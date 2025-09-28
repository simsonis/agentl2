from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

import click
from sqlalchemy import insert, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .api_client import APIClient, APIResponse
from .config import Settings, get_settings
from .db import healthcheck, init_engine, session_scope
from .logging import configure_logging, get_logger
from .metrics import MetricsServer
from .models import RawLawData
from .parsers import LawRecord, normalize_law_payload

logger = get_logger("agentl2.collect_laws")


@dataclass
class RunStats:
    collected: int = 0
    duplicates: int = 0
    failures: int = 0


class LawCollector:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        base_defaults = {
            **settings.law_api_static_params,
            "OC": settings.law_api_oc,
            "type": settings.law_api_default_type,
        }
        self.list_client = APIClient(
            base_url=str(settings.law_api_base_url),
            default_params={**base_defaults, "target": settings.law_api_target},
            user_agent=settings.law_api_user_agent,
            timeout=settings.law_api_request_timeout,
            rate_limit_rps=settings.law_api_rate_limit_rps,
            max_retries=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )
        self.detail_client = APIClient(
            base_url=str(settings.law_api_base_url),
            default_params={**base_defaults, "target": settings.law_api_detail_target},
            user_agent=settings.law_api_user_agent,
            timeout=settings.law_api_request_timeout,
            rate_limit_rps=settings.law_api_rate_limit_rps,
            max_retries=settings.max_retries,
            backoff_seconds=settings.backoff_seconds,
        )

    def close(self) -> None:
        self.list_client.close()
        self.detail_client.close()

    def run(
        self,
        *,
        query: Optional[str],
        start_page: int,
        total_pages: int,
        collection_id: str,
        page_size: Optional[int],
    ) -> RunStats:
        stats = RunStats()
        with session_scope() as session:
            for page in range(start_page, start_page + max(total_pages, 1)):
                try:
                    list_response = self._fetch_list_page(query=query, page=page, page_size=page_size)
                except Exception:
                    logger.exception("failed to fetch law list", page=page, query=query)
                    stats.failures += 1
                    continue

                items = self._extract_items(list_response.json)
                if not items:
                    logger.warning("no laws returned", page=page, query=query)
                    continue

                for item in items:
                    try:
                        detail_response = self._fetch_detail(item)
                        record = normalize_law_payload(item, detail_response.json if detail_response else None)
                        inserted = self._store_record(
                            session=session,
                            record=record,
                            collection_id=collection_id,
                            list_response=list_response,
                            detail_response=detail_response,
                        )
                        if inserted:
                            stats.collected += 1
                        else:
                            stats.duplicates += 1
                    except Exception:
                        logger.exception("law item processing failed")
                        stats.failures += 1
        return stats

    def _fetch_list_page(self, *, query: Optional[str], page: int, page_size: Optional[int]) -> APIResponse:
        params: Dict[str, Any] = {
            self.settings.law_api_page_param: page,
            self.settings.law_api_page_size_param: page_size or self.settings.law_api_default_page_size,
        }
        if query:
            params[self.settings.law_api_query_param] = query
        if self.settings.law_api_default_sort:
            params[self.settings.law_api_sort_param] = self.settings.law_api_default_sort
        logger.info(
            "requesting law list",
            page=page,
            query=query,
            page_size=params[self.settings.law_api_page_size_param],
        )
        return self.list_client.request_json(self.settings.law_api_search_endpoint, params=params)

    def _fetch_detail(self, list_item: Mapping[str, Any]) -> Optional[APIResponse]:
        law_id = (
            list_item.get("법령ID")
            or list_item.get("lawId")
            or list_item.get("law_id")
        )
        params: Dict[str, Any]
        if law_id:
            params = {self.settings.law_api_detail_id_param: law_id}
        else:
            serial_no = (
                list_item.get("법령일련번호")
                or list_item.get("lawSerialNo")
                or list_item.get("law_serial_no")
            )
            if not serial_no:
                logger.warning("missing identifier for law detail fetch")
                return None
            params = {self.settings.law_api_detail_id_param: serial_no}
        logger.debug("requesting law detail", params=params)
        return self.detail_client.request_json(self.settings.law_api_detail_endpoint, params=params)

    @staticmethod
    def _extract_items(payload: Any) -> List[Mapping[str, Any]]:
        items: List[Mapping[str, Any]] = []
        if isinstance(payload, list):
            items.extend(item for item in payload if isinstance(item, Mapping))
            return items
        if isinstance(payload, Mapping):
            for key in ("law", "laws", "lawList", "list", "items", "result"):
                value = payload.get(key)
                if isinstance(value, list):
                    items.extend(item for item in value if isinstance(item, Mapping))
                elif isinstance(value, Mapping):
                    items.append(value)
        return items

    def _store_record(
        self,
        session: Session,
        record: LawRecord,
        collection_id: str,
        list_response: APIResponse,
        detail_response: Optional[APIResponse],
    ) -> bool:
        request_url = detail_response.url if detail_response else list_response.url
        row = record.as_row(collection_id=collection_id, request_url=request_url)
        if detail_response and detail_response.json is not None:
            row["raw_response_json"] = detail_response.json
        row["collected_at"] = datetime.now(timezone.utc)

        insert_stmt = (
            insert(RawLawData)
            .values(**row)
            .on_conflict_do_nothing(index_elements=["law_serial_no"])
        )
        result = session.execute(insert_stmt)
        if result.rowcount and result.rowcount > 0:
            logger.info("inserted law record", law_serial_no=record.law_serial_no, uuid=record.uuid)
            return True

        update_stmt = (
            update(RawLawData)
            .where(RawLawData.law_serial_no == record.law_serial_no)
            .values(**row)
        )
        try:
            session.execute(update_stmt)
            logger.info("updated law record", law_serial_no=record.law_serial_no, uuid=record.uuid)
        except SQLAlchemyError:
            logger.exception("failed to upsert law record", law_serial_no=record.law_serial_no)
            raise
        return False


@click.command()
@click.option("--query", default=None, help="법령 검색어")
@click.option("--page", default=1, show_default=True, type=int, help="조회 시작 페이지")
@click.option("--pages", default=1, show_default=True, type=int, help="조회할 페이지 수")
@click.option("--page-size", default=None, type=int, help="페이지 당 결과 수 (미지정 시 기본값 사용)")
@click.option("--collection-id", required=True, help="수집 실행 식별자 (예: poc-20250926)")
def main(
    query: Optional[str],
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
    metrics_server.record_run_start("laws")

    collector = LawCollector(settings)
    started = time.monotonic()
    try:
        stats = collector.run(
            query=query,
            start_page=page,
            total_pages=pages,
            collection_id=collection_id,
            page_size=page_size,
        )
    finally:
        collector.close()
    duration = time.monotonic() - started
    logger.info(
        "law collection summary",
        query=query,
        start_page=page,
        pages=pages,
        page_size=page_size or settings.law_api_default_page_size,
        collected=stats.collected,
        duplicates=stats.duplicates,
        failures=stats.failures,
        duration_seconds=round(duration, 3),
    )
    metrics_server.record_run_end("laws", stats.collected, stats.duplicates, stats.failures)


if __name__ == "__main__":
    main()
