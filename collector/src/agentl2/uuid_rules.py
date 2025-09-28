from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Mapping, Optional

from dateutil import parser as date_parser  # type: ignore


def _ensure_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if value in (None, "", "00000000"):
        raise ValueError("날짜 값이 필요합니다.")
    if isinstance(value, (int, float)):
        value = str(int(value))
    if isinstance(value, str):
        cleaned = re.sub(r"[^0-9]", "", value)
        if len(cleaned) >= 8:
            return datetime.strptime(cleaned[:8], "%Y%m%d").date()
        return date_parser.parse(value).date()
    raise ValueError(f"지원하지 않는 날짜 형식: {value!r}")


def _zfill_digits(value: Optional[str], length: int) -> str:
    if value is None:
        return "0" * length
    digits = re.sub(r"[^0-9]", "", value)
    return digits.zfill(length) if digits else "0" * length


def _clean_code(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^0-9A-Za-z]", "", value.upper())


def law_uuid(dto: Mapping[str, Any]) -> str:
    kind_code = _clean_code(
        dto.get("법령종류코드")
        or dto.get("lawTypeCode")
        or dto.get("law_kind_code")
    )
    if not kind_code:
        raise ValueError("법령종류코드가 필요합니다.")

    law_number = (
        dto.get("법령번호")
        or dto.get("lawNo")
        or dto.get("law_number")
    )
    if not law_number:
        raise ValueError("법령번호가 필요합니다.")

    promulgation_raw = (
        dto.get("공포일자")
        or dto.get("promulgationDate")
        or dto.get("promulgation_date")
    )
    promulgation_date = _ensure_date(promulgation_raw)

    revision_raw = (
        dto.get("개정차수")
        or dto.get("revisionNo")
        or dto.get("revision_no")
    )

    return f"{kind_code}-{_zfill_digits(str(law_number), 6)}-{promulgation_date.strftime('%Y%m%d')}-{_zfill_digits(str(revision_raw) if revision_raw is not None else None, 3)}"


def prec_uuid(dto: Mapping[str, Any]) -> str:
    court_code = _clean_code(
        dto.get("법원코드")
        or dto.get("courtCode")
        or dto.get("court_code")
    )
    if not court_code:
        raise ValueError("법원코드가 필요합니다.")

    case_number = (
        dto.get("사건번호")
        or dto.get("caseNumber")
        or dto.get("case_number")
    )
    if not case_number:
        raise ValueError("사건번호가 필요합니다.")
    case_number_str = str(case_number).strip()

    judgment_raw = (
        dto.get("선고일자")
        or dto.get("judgmentDate")
        or dto.get("judgment_date")
    )
    judgment_date = _ensure_date(judgment_raw)

    return f"{court_code}-{case_number_str}-{judgment_date.strftime('%Y%m%d')}"
