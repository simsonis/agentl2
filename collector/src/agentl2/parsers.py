from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Mapping, Optional

from dateutil import parser as date_parser  # type: ignore

from .uuid_rules import law_uuid, prec_uuid


def ensure_date(value: Any) -> Optional[date]:
    if value in (None, "", "00000000"):
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        value = str(int(value))
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        digits = re.sub(r"[^0-9]", "", stripped)
        if len(digits) >= 8:
            try:
                return datetime.strptime(digits[:8], "%Y%m%d").date()
            except ValueError:
                pass
        try:
            return date_parser.parse(stripped).date()
        except (ValueError, TypeError):
            pass
    raise ValueError(f"날짜 값을 파싱할 수 없습니다: {value!r}")


def ensure_int(value: Any) -> Optional[int]:
    if value in (None, "", [], "N/A"):
        return None
    try:
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def ensure_str(value: Any) -> Optional[str]:
    if value in (None, "", []):
        return None
    result = str(value).strip()
    return result or None


def _to_plain_dict(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if isinstance(payload, dict):
        return dict(payload)
    return json.loads(json.dumps(payload, ensure_ascii=False))


def _merge_payload(list_payload: Mapping[str, Any], detail_payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    merged = _to_plain_dict(list_payload)
    if detail_payload:
        merged.update(_to_plain_dict(detail_payload))
    return merged


@dataclass
class LawRecord:
    law_serial_no: int
    law_id: Optional[str]
    law_name_ko: str
    law_name_zh: Optional[str]
    law_abbreviation: Optional[str]
    promulgation_no: Optional[int]
    promulgation_date: Optional[date]
    enforce_date: date
    is_current: Optional[str]
    law_category_name: Optional[str]
    ministry_code: Optional[str]
    ministry_name: Optional[str]
    ministry_contact: Optional[str]
    revision_type_name: Optional[str]
    is_sub_statute: Optional[str]
    basic_info_xml: Optional[str]
    article_xml: Optional[str]
    supplement_xml: Optional[str]
    revision_reason_xml: Optional[str]
    history_xml: Optional[str]
    uuid: Optional[str]
    raw_payload: Dict[str, Any]

    def as_row(self, collection_id: str, request_url: str) -> Dict[str, Any]:
        return {
            "law_serial_no": self.law_serial_no,
            "law_id": self.law_id,
            "law_name_ko": self.law_name_ko,
            "law_name_zh": self.law_name_zh,
            "law_abbreviation": self.law_abbreviation,
            "promulgation_no": self.promulgation_no,
            "promulgation_date": self.promulgation_date,
            "enforce_date": self.enforce_date,
            "is_current": self.is_current,
            "law_category_name": self.law_category_name,
            "ministry_code": self.ministry_code,
            "ministry_name": self.ministry_name,
            "ministry_contact": self.ministry_contact,
            "revision_type_name": self.revision_type_name,
            "is_sub_statute": self.is_sub_statute,
            "basic_info_xml": self.basic_info_xml,
            "article_xml": self.article_xml,
            "supplement_xml": self.supplement_xml,
            "revision_reason_xml": self.revision_reason_xml,
            "history_xml": self.history_xml,
            "collection_id": collection_id,
            "api_request_url": request_url,
            "raw_response_json": self.raw_payload,
        }


@dataclass
class PrecedentRecord:
    prec_serial_no: int
    case_name: Optional[str]
    case_number: str
    judgment_date: Optional[date]
    court_name: Optional[str]
    court_code: Optional[str]
    case_type_code: Optional[str]
    case_type_name: Optional[str]
    judgment_type_code: Optional[str]
    judgment_type_name: Optional[str]
    judgment_result: Optional[str]
    referenced_statutes: Optional[str]
    referenced_precedents: Optional[str]
    summary: Optional[str]
    conclusion: Optional[str]
    reasoning: Optional[str]
    full_text: Optional[str]
    uuid: Optional[str]
    raw_payload: Dict[str, Any]

    def as_row(self, collection_id: str, request_url: str) -> Dict[str, Any]:
        return {
            "prec_serial_no": self.prec_serial_no,
            "case_name": self.case_name,
            "case_number": self.case_number,
            "judgment_date": self.judgment_date,
            "court_name": self.court_name,
            "court_code": self.court_code,
            "case_type_code": self.case_type_code,
            "case_type_name": self.case_type_name,
            "judgment_type_code": self.judgment_type_code,
            "judgment_type_name": self.judgment_type_name,
            "judgment_result": self.judgment_result,
            "referenced_statutes": self.referenced_statutes,
            "referenced_precedents": self.referenced_precedents,
            "summary": self.summary,
            "conclusion": self.conclusion,
            "reasoning": self.reasoning,
            "full_text": self.full_text,
            "collection_id": collection_id,
            "api_request_url": request_url,
            "raw_response_json": self.raw_payload,
        }


def normalize_law_payload(list_payload: Mapping[str, Any], detail_payload: Optional[Mapping[str, Any]] = None) -> LawRecord:
    merged = _merge_payload(list_payload, detail_payload)

    law_serial_no = ensure_int(
        merged.get("법령일련번호") or merged.get("lawSerialNo") or merged.get("law_serial_no")
    )
    if law_serial_no is None:
        raise ValueError("법령일련번호를 찾을 수 없습니다.")

    law_id = ensure_str(merged.get("법령ID") or merged.get("lawId") or merged.get("law_id"))
    law_name_ko = ensure_str(merged.get("법령명한글") or merged.get("lawName") or merged.get("law_name_ko"))
    if not law_name_ko:
        raise ValueError("법령명(한글)이 필요합니다.")

    enforce_date = ensure_date(merged.get("시행일자") or merged.get("enforceDate") or merged.get("enforce_date"))
    if enforce_date is None:
        raise ValueError("시행일자를 파싱할 수 없습니다.")

    promulgation_date = ensure_date(merged.get("공포일자") or merged.get("promulgationDate") or merged.get("promulgation_date"))
    promulgation_no = ensure_int(merged.get("공포번호") or merged.get("promulgationNo") or merged.get("promulgation_no"))

    uuid_value: Optional[str] = None
    try:
        uuid_value = law_uuid(merged)
    except ValueError:
        uuid_value = None

    return LawRecord(
        law_serial_no=law_serial_no,
        law_id=law_id,
        law_name_ko=law_name_ko,
        law_name_zh=ensure_str(merged.get("법령명한자") or merged.get("lawNameZh")),
        law_abbreviation=ensure_str(merged.get("법령약칭명") or merged.get("lawAbbreviation")),
        promulgation_no=promulgation_no,
        promulgation_date=promulgation_date,
        enforce_date=enforce_date,
        is_current=ensure_str(merged.get("현행연혁구분코드") or merged.get("isCurrent")),
        law_category_name=ensure_str(merged.get("법령구분명") or merged.get("lawCategoryName")),
        ministry_code=ensure_str(merged.get("소관부처코드") or merged.get("ministryCode")),
        ministry_name=ensure_str(merged.get("소관부처명") or merged.get("ministryName")),
        ministry_contact=ensure_str(merged.get("소관부처연락처") or merged.get("ministryContact")),
        revision_type_name=ensure_str(merged.get("제개정구분명") or merged.get("revisionTypeName")),
        is_sub_statute=ensure_str(merged.get("자법타법구분") or merged.get("isSubStatute")),
        basic_info_xml=ensure_str(merged.get("기본정보") or merged.get("basicInfo")),
        article_xml=ensure_str(merged.get("조문") or merged.get("article")),
        supplement_xml=ensure_str(merged.get("부칙") or merged.get("supplement")),
        revision_reason_xml=ensure_str(merged.get("제개정이유") or merged.get("revisionReason")),
        history_xml=ensure_str(merged.get("연혁") or merged.get("history")),
        uuid=uuid_value,
        raw_payload=merged,
    )


def normalize_precedent_payload(list_payload: Mapping[str, Any], detail_payload: Optional[Mapping[str, Any]] = None) -> PrecedentRecord:
    merged = _merge_payload(list_payload, detail_payload)

    prec_serial_no = ensure_int(
        merged.get("판례일련번호")
        or merged.get("precSerialNo")
        or merged.get("prec_serial_no")
    )
    if prec_serial_no is None:
        raise ValueError("판례일련번호를 찾을 수 없습니다.")

    case_number = ensure_str(merged.get("사건번호") or merged.get("caseNumber") or merged.get("case_number"))
    if not case_number:
        raise ValueError("사건번호가 필요합니다.")
    case_number = case_number.strip()

    judgment_date = ensure_date(merged.get("선고일자") or merged.get("judgmentDate") or merged.get("judgment_date"))
    court_code = ensure_str(merged.get("법원코드") or merged.get("courtCode") or merged.get("court_code"))

    uuid_value: Optional[str] = None
    try:
        uuid_value = prec_uuid(merged)
    except ValueError:
        uuid_value = None

    return PrecedentRecord(
        prec_serial_no=prec_serial_no,
        case_name=ensure_str(merged.get("사건명") or merged.get("caseName")),
        case_number=case_number,
        judgment_date=judgment_date,
        court_name=ensure_str(merged.get("법원명") or merged.get("courtName")),
        court_code=court_code,
        case_type_code=ensure_str(merged.get("사건종류코드") or merged.get("caseTypeCode")),
        case_type_name=ensure_str(merged.get("사건종류명") or merged.get("caseTypeName")),
        judgment_type_code=ensure_str(merged.get("판결유형코드") or merged.get("judgmentTypeCode")),
        judgment_type_name=ensure_str(merged.get("판결유형명") or merged.get("judgmentTypeName")),
        judgment_result=ensure_str(merged.get("판결결과") or merged.get("judgmentResult")),
        referenced_statutes=ensure_str(merged.get("참조법령") or merged.get("referencedStatutes")),
        referenced_precedents=ensure_str(merged.get("참조판례") or merged.get("referencedPrecedents")),
        summary=ensure_str(merged.get("판시사항") or merged.get("summary")),
        conclusion=ensure_str(merged.get("판결요지") or merged.get("conclusion")),
        reasoning=ensure_str(merged.get("판례내용") or merged.get("reasoning")),
        full_text=ensure_str(merged.get("전체판례") or merged.get("fullText")),
        uuid=uuid_value,
        raw_payload=merged,
    )
