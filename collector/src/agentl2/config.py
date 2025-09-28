from __future__ import annotations

from functools import lru_cache
from typing import Dict, Optional

from pydantic import Field, HttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_key_value_pairs(raw: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for item in raw.split(","):
        key, sep, value = item.partition("=")
        if not key or not sep:
            continue
        result[key.strip()] = value.strip()
    return result


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = Field(alias="DATABASE_URL")
    db_pool_size: int = Field(5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(10, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(30, alias="DB_POOL_TIMEOUT")

    log_level: str = Field("INFO", alias="COLLECTOR_LOG_LEVEL")
    log_format: str = Field("json", alias="COLLECTOR_LOG_FORMAT")
    metrics_port: int = Field(8000, alias="COLLECTOR_METRICS_PORT")

    max_retries: int = Field(5, alias="COLLECTOR_MAX_RETRIES")
    backoff_seconds: float = Field(1.0, alias="COLLECTOR_BACKOFF_SECONDS")

    law_api_base_url: HttpUrl = Field("https://www.law.go.kr/DRF/", alias="LAW_API_BASE_URL")
    law_api_search_endpoint: str = Field("lawSearch.do", alias="LAW_API_SEARCH_ENDPOINT")
    law_api_detail_endpoint: str = Field("lawService.do", alias="LAW_API_DETAIL_ENDPOINT")
    law_api_detail_id_param: str = Field("ID", alias="LAW_API_DETAIL_ID_PARAM")
    law_api_sort_param: str = Field("sort", alias="LAW_API_SORT_PARAM")
    law_api_default_sort: Optional[str] = Field(None, alias="LAW_API_DEFAULT_SORT")
    law_api_oc: str = Field(..., alias="LAW_API_OC")
    law_api_target: str = Field("law", alias="LAW_API_TARGET")
    law_api_detail_target: str = Field("law", alias="LAW_API_DETAIL_TARGET")
    law_api_query_param: str = Field("query", alias="LAW_API_QUERY_PARAM")
    law_api_page_param: str = Field("page", alias="LAW_API_PAGE_PARAM")
    law_api_page_size_param: str = Field("display", alias="LAW_API_DISPLAY_PARAM")
    law_api_static_params: Dict[str, str] = Field(default_factory=dict, alias="LAW_API_STATIC_PARAMS")
    law_api_default_type: str = Field("JSON", alias="LAW_API_DEFAULT_TYPE")
    law_api_default_page_size: int = Field(100, alias="LAW_API_DEFAULT_PAGE_SIZE")
    law_api_user_agent: str = Field("agentl2-collector/0.1", alias="LAW_API_USER_AGENT")
    law_api_request_timeout: float = Field(15.0, alias="LAW_API_REQUEST_TIMEOUT")
    law_api_rate_limit_rps: float = Field(3.0, alias="LAW_API_RATE_LIMIT_RPS")

    prec_api_base_url: Optional[HttpUrl] = Field(None, alias="PREC_API_BASE_URL")
    prec_api_search_endpoint: str = Field("precSearch.do", alias="PREC_API_SEARCH_ENDPOINT")
    prec_api_detail_endpoint: Optional[str] = Field(None, alias="PREC_API_DETAIL_ENDPOINT")
    prec_api_oc: Optional[str] = Field(None, alias="PREC_API_OC")
    prec_api_target: str = Field("prec", alias="PREC_API_TARGET")
    prec_api_query_param: str = Field("search", alias="PREC_API_KEYWORD_PARAM")
    prec_api_start_date_param: str = Field("startDate", alias="PREC_API_START_DATE_PARAM")
    prec_api_end_date_param: str = Field("endDate", alias="PREC_API_END_DATE_PARAM")
    prec_api_page_param: str = Field("page", alias="PREC_API_PAGE_PARAM")
    prec_api_page_size_param: str = Field("display", alias="PREC_API_DISPLAY_PARAM")
    prec_api_static_params: Dict[str, str] = Field(default_factory=dict, alias="PREC_API_STATIC_PARAMS")
    prec_api_default_type: str = Field("JSON", alias="PREC_API_DEFAULT_TYPE")
    prec_api_default_page_size: int = Field(100, alias="PREC_API_DEFAULT_PAGE_SIZE")
    prec_api_user_agent: str = Field("agentl2-collector/0.1", alias="PREC_API_USER_AGENT")
    prec_api_request_timeout: float = Field(15.0, alias="PREC_API_REQUEST_TIMEOUT")
    prec_api_rate_limit_rps: float = Field(3.0, alias="PREC_API_RATE_LIMIT_RPS")

    @model_validator(mode="before")
    @classmethod
    def _parse_static_params(cls, values: Dict[str, str]) -> Dict[str, str]:
        for key in ("LAW_API_STATIC_PARAMS", "PREC_API_STATIC_PARAMS"):
            raw_value = values.get(key)
            if isinstance(raw_value, str):
                values[key] = _parse_key_value_pairs(raw_value)
        return values

    @model_validator(mode="after")
    def _apply_prec_defaults(self) -> "Settings":
        if self.prec_api_base_url is None:
            self.prec_api_base_url = self.law_api_base_url
        if self.prec_api_oc in (None, ""):
            self.prec_api_oc = self.law_api_oc
        return self

    def llm_config(self) -> Dict[str, Optional[str]]:
        return {
            "provider": None,
            "endpoint": None,
            "profile": None,
            "api_key_env": None,
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
