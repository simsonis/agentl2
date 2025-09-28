from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Tuple

import click
from sqlalchemy import insert, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .api_client import APIClient, APIResponse
from .config import Settings, get_settings
from .db import healthcheck, init_engine, session_scope
from .logging import configure_logging, get_logger
from .metrics import MetricsServer
from .models import RawPrecedentData
from .parsers import PrecedentRecord, normalize_precedent_payload

logger = get_logger("agentl2.collect_prec")


@dataclass
class RunStats:
    collected: int = 0
    duplicates: int = 0
    failures: int = 0


def _parse_date_range(raw: Optional[str]) -> Optional[Tuple[str, str]]:
    if raw in (None, ""):
        return None
    parts = raw.split("~")
    if len(parts) != 2:
        raise click.BadParameter("date-range must be formatted as YYYYMMDD~YYYYMMDD")
    start = parts[0].strip()
    end = parts[1].strip()
    if start and len(start) != 8:
        raise click.BadParameter("start date must be YYYYMMDD")
    if end and len(end) != 8:
        raise click.BadParameter("end date must be YYYYMMDD")
    return start or "", end or ""


class PrecedentCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        base_defaults = {
            **settings.prec_api_static_params,
            "OC": settings.prec_api_oc,
            "type": settings.prec_api_default_type,
        }
        self.client = APIClient(
            base_url=str(settings.prec_api_base_url),
            default_params={**base_defaults, "target": settings.prec_api_target},
            user_agent=settings.prec_api_user_agent,
            timeout=settings.prec_api_request_timeout,
            rate_limit_rps=settings.prec_api_rate_limit_rps,
            max_retries=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )

    def close(self) -> None:
        self.client.close()

    def run(
        self,
        *,
        keywords: Optional[str],
        date_range: Optional[Tuple[str, str]],
        start_page: int,
        total_pages: int,
        collection_id: str,
        page_size: Optional[int],
    ) -> RunStats:
        stats = RunStats()
        with session_scope() as session:
            for page in range(start_page, start_page + max(total_pages, 1)):
                try:
                    response = self._fetch_page(
                        keywords=keywords,
                        date_range=date_range,
                        page=page,
                        page_size=page_size,
                    )
                except Exception:
                    logger.exception("failed to fetch precedent list", page=page)
                    stats.failures += 1
                    continue

                items = self._extract_items(response.json)
                if not items:
                    logger.warning("no precedents returned", page=page)
                    continue

                for item in items:
                    try:
                        record = normalize_precedent_payload(item)
                        inserted = self._store_record(
                            session=session,
                            record=record,
                            collection_id=collection_id,
                            response=response,
                        )
                        if inserted:
                            stats.collected += 1
                        else:
                            stats.duplicates += 1
                    except Exception:
                        logger.exception("precedent item processing failed")
                        stats.failures += 1
        return stats

    def _fetch_page(
        self,
        *,
        keywords: Optional[str],
        date_range: Optional[Tuple[str, str]],
        page: int,
        page_size: Optional[int],
    ) -> APIResponse:
        params: Dict[str, Any] = {
            self.settings.prec_api_page_param: page,
            self.settings.prec_api_page_size_param: page_size or self.settings.prec_api_default_page_size,
        }
        if keywords:
            params[self.settings.prec_api_query_param] = keywords
        if date_range:
            start, end = date_range
            if start:
                params[self.settings.prec_api_start_date_param] = start
            if end:
                params[self.settings.prec_api_end_date_param] = end
        logger.info(
            "requesting precedent list",
            page=page,
            keywords=keywords,
            date_range=date_range,
            page_size=params[self.settings.prec_api_page_size_param],
        )
        return self.client.request_json(self.settings.prec_api_search_endpoint, params=params)

    @staticmethod
    def _extract_items(payload: Any) -> List[Mapping[str, Any]]:
        items: List[Mapping[str, Any]] = []
        if isinstance(payload, list):
            items.extend(item for item in payload if isinstance(item, Mapping))
            return items
        if isinstance(payload, Mapping):
            for key in ("precedents", "precList", "list", "items", "result"):
                value = payload.get(key)
                if isinstance(value, list):
                    items.extend(item for item in value if isinstance(item, Mapping))
                elif isinstance(value, Mapping):
                    items.append(value)
        return items

    def _store_record(
        self,
        session: Session,
        record: PrecedentRecord,
        collection_id: str,
        response: APIResponse,
    ) -> bool:
        row = record.as_row(collection_id=collection_id, request_url=response.url)
        row["collected_at"] = datetime.now(timezone.utc)
        if response.json is not None:
            row["raw_response_json"] = response.json

        insert_stmt = (
            insert(RawPrecedentData)
            .values(**row)
            .on_conflict_do_nothing(index_elements=["prec_serial_no"])
        )
        result = session.execute(insert_stmt)
        if result.rowcount and result.rowcount > 0:
            logger.info("inserted precedent record", prec_serial_no=record.prec_serial_no, uuid=record.uuid)
            return True

        update_stmt = (
            update(RawPrecedentData)
            .where(RawPrecedentData.prec_serial_no == record.prec_serial_no)
            .values(**row)
        )
        try:
            session.execute(update_stmt)
            logger.info("updated precedent record", prec_serial_no=record.prec_serial_no, uuid=record.uuid)
        except SQLAlchemyError:
            logger.exception("failed to upsert precedent record", prec_serial_no=record.prec_serial_no)
            raise
        return False


@click.command()
@click.option("--keywords", default=None, help="판례 검색 키워드")
@click.option("--date-range", default=None, help="검색 기간 (YYYYMMDD~YYYYMMDD)")
@click.option("--page", default=1, show_default=True, type=int, help="조회 시작 페이지")
@click.option("--pages", default=1, show_default=True, type=int, help="조회할 페이지 수")
@click.option("--page-size", default=None, type=int, help="페이지 당 결과 수 (미지정 시 기본값 사용)")
@click.option("--collection-id", required=True, help="수집 실행 식별자 (예: poc-20250926)")
def main(
    keywords: Optional[str],
    date_range: Optional[str],
    page: int,
    pages: int,
    page_size: Optional[int],
    collection_id: str,
) -> None:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format)
    engine = init_engine(settings)
    healthcheck(engine)

    metrics_server = MetricsServer(settings.metrics_port)
    metrics_server.start()
    metrics_server.record_run_start("precedents")

    collector = PrecedentCollector(settings)
    started = time.monotonic()
    try:
        stats = collector.run(
            keywords=keywords,
            date_range=_parse_date_range(date_range),
            start_page=page,
            total_pages=pages,
            collection_id=collection_id,
            page_size=page_size,
        )
    finally:
        collector.close()
    duration = time.monotonic() - started
    logger.info(
        "precedent collection summary",
        keywords=keywords,
        date_range=date_range,
        start_page=page,
        pages=pages,
        page_size=page_size or settings.prec_api_default_page_size,
        collected=stats.collected,
        duplicates=stats.duplicates,
        failures=stats.failures,
        duration_seconds=round(duration, 3),
    )
    metrics_server.record_run_end("precedents", stats.collected, stats.duplicates, stats.failures)


if __name__ == "__main__":
    main()
