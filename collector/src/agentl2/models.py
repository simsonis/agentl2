from __future__ import annotations

from datetime import datetime, date
from typing import Optional

from sqlalchemy import JSON, Date, DateTime, Integer, String, Text, UniqueConstraint, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class RawLawData(Base):
    __tablename__ = "raw_law_data"
    __table_args__ = (UniqueConstraint("law_id", "enforce_date", name="uq_law_version"),)

    law_serial_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    law_id: Mapped[Optional[str]] = mapped_column(String(20))
    law_name_ko: Mapped[str] = mapped_column(Text, nullable=False)
    law_name_zh: Mapped[Optional[str]] = mapped_column(String(255))
    law_abbreviation: Mapped[Optional[str]] = mapped_column(String(255))
    promulgation_no: Mapped[Optional[int]] = mapped_column(Integer)
    promulgation_date: Mapped[Optional[date]] = mapped_column(Date)
    enforce_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[Optional[str]] = mapped_column(String(1))
    law_category_name: Mapped[Optional[str]] = mapped_column(String(50))
    ministry_code: Mapped[Optional[str]] = mapped_column(String(10))
    ministry_name: Mapped[Optional[str]] = mapped_column(String(100))
    ministry_contact: Mapped[Optional[str]] = mapped_column(String(100))
    revision_type_name: Mapped[Optional[str]] = mapped_column(String(50))
    is_sub_statute: Mapped[Optional[str]] = mapped_column(String(1))
    basic_info_xml: Mapped[Optional[str]] = mapped_column(Text)
    article_xml: Mapped[Optional[str]] = mapped_column(Text)
    supplement_xml: Mapped[Optional[str]] = mapped_column(Text)
    revision_reason_xml: Mapped[Optional[str]] = mapped_column(Text)
    history_xml: Mapped[Optional[str]] = mapped_column(Text)
    collection_id: Mapped[str] = mapped_column(String(50), nullable=False)
    api_request_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response_json: Mapped[Optional[dict]] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @classmethod
    def exists_by_version(cls, session: Session, law_id: str, enforce_date: date) -> bool:
        stmt = select(func.count()).where(cls.law_id == law_id, cls.enforce_date == enforce_date)
        return session.scalar(stmt) > 0

    @classmethod
    def exists_by_serial(cls, session: Session, law_serial_no: int) -> bool:
        stmt = select(func.count()).where(cls.law_serial_no == law_serial_no)
        return session.scalar(stmt) > 0


class RawPrecedentData(Base):
    __tablename__ = "raw_precedent_data"
    __table_args__ = (UniqueConstraint("case_number", "judgment_date", "court_code", name="uq_case_info"),)

    prec_serial_no: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_name: Mapped[Optional[str]] = mapped_column(Text)
    case_number: Mapped[str] = mapped_column(String(100), nullable=False)
    judgment_date: Mapped[Optional[date]] = mapped_column(Date)
    court_name: Mapped[Optional[str]] = mapped_column(String(100))
    court_code: Mapped[Optional[str]] = mapped_column(String(10))
    case_type_code: Mapped[Optional[str]] = mapped_column(String(10))
    case_type_name: Mapped[Optional[str]] = mapped_column(String(50))
    judgment_type_code: Mapped[Optional[str]] = mapped_column(String(10))
    judgment_type_name: Mapped[Optional[str]] = mapped_column(String(50))
    judgment_result: Mapped[Optional[str]] = mapped_column(Text)
    referenced_statutes: Mapped[Optional[str]] = mapped_column(Text)
    referenced_precedents: Mapped[Optional[str]] = mapped_column(Text)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    conclusion: Mapped[Optional[str]] = mapped_column(Text)
    reasoning: Mapped[Optional[str]] = mapped_column(Text)
    full_text: Mapped[Optional[str]] = mapped_column(Text)
    collection_id: Mapped[str] = mapped_column(String(50), nullable=False)
    api_request_url: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response_json: Mapped[Optional[dict]] = mapped_column(JSON)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    @classmethod
    def exists_by_case(cls, session: Session, case_number: str, judgment_date: Optional[date], court_code: Optional[str]) -> bool:
        stmt = select(func.count()).where(
            cls.case_number == case_number,
            cls.judgment_date == judgment_date,
            cls.court_code == court_code,
        )
        return session.scalar(stmt) > 0

    @classmethod
    def exists_by_serial(cls, session: Session, prec_serial_no: int) -> bool:
        stmt = select(func.count()).where(cls.prec_serial_no == prec_serial_no)
        return session.scalar(stmt) > 0
