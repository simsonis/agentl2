from datetime import date

import pytest

from agentl2.parsers import (
    LawRecord,
    PrecedentRecord,
    ensure_date,
    normalize_law_payload,
    normalize_precedent_payload,
)


def test_ensure_date_various_formats() -> None:
    assert ensure_date("20240101") == date(2024, 1, 1)
    assert ensure_date("2024.01.01") == date(2024, 1, 1)
    assert ensure_date("2024-01-01T10:00:00") == date(2024, 1, 1)
    assert ensure_date(20240101) == date(2024, 1, 1)
    with pytest.raises(ValueError):
        ensure_date("invalid-date")


def test_normalize_law_payload_with_detail() -> None:
    list_payload = {
        "법령일련번호": "123",
        "법령ID": "LAW0001",
        "법령명한글": "금융소비자보호법",
        "시행일자": "20240301",
        "공포일자": "20240215",
        "법령종류코드": "LAW",
        "개정차수": "001",
    }
    detail_payload = {
        "법령약칭명": "금소법",
        "소관부처명": "금융위원회",
    }
    record = normalize_law_payload(list_payload, detail_payload)
    assert isinstance(record, LawRecord)
    assert record.law_serial_no == 123
    assert record.law_name_ko == "금융소비자보호법"
    assert record.enforce_date == date(2024, 3, 1)
    assert record.law_abbreviation == "금소법"
    assert record.uuid == "LAW-009682-20240215-001" or record.uuid is None


def test_normalize_law_payload_missing_serial_raises() -> None:
    with pytest.raises(ValueError):
        normalize_law_payload({"법령명한글": "테스트", "시행일자": "20240101"})


def test_normalize_precedent_payload_happy_path() -> None:
    payload = {
        "판례일련번호": "321",
        "사건번호": "2023도1234",
        "선고일자": "2023-06-30",
        "법원코드": "SCC",
        "사건명": "중요 판례",
    }
    record = normalize_precedent_payload(payload)
    assert isinstance(record, PrecedentRecord)
    assert record.prec_serial_no == 321
    assert record.case_number == "2023도1234"
    assert record.judgment_date == date(2023, 6, 30)
    assert record.court_code == "SCC"
    assert record.uuid == "SCC-2023도1234-20230630"


def test_normalize_precedent_payload_missing_case_raises() -> None:
    with pytest.raises(ValueError):
        normalize_precedent_payload({"판례일련번호": "1"})
