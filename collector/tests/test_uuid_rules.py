from datetime import date

import pytest

from agentl2.uuid_rules import law_uuid, prec_uuid


def test_law_uuid_happy_path() -> None:
    dto = {
        "법령종류코드": "LAW",
        "법령번호": "9682",
        "공포일자": "2020-03-05",
        "개정차수": "1",
    }
    assert law_uuid(dto) == "LAW-009682-20200305-001"


def test_law_uuid_missing_fields() -> None:
    dto = {"법령번호": "123"}
    with pytest.raises(ValueError):
        law_uuid(dto)


def test_law_uuid_revision_default_zero() -> None:
    dto = {
        "lawTypeCode": "DEC",
        "lawNo": "15",
        "promulgationDate": "20190101",
    }
    assert law_uuid(dto) == "DEC-000015-20190101-000"


def test_prec_uuid_happy_path() -> None:
    dto = {
        "courtCode": "SUP",
        "caseNumber": "2020도123",
        "judgmentDate": "2020.12.15",
    }
    assert prec_uuid(dto) == "SUP-2020도123-20201215"


def test_prec_uuid_requires_fields() -> None:
    with pytest.raises(ValueError):
        prec_uuid({"caseNumber": "2020도123", "judgmentDate": "20200101"})
