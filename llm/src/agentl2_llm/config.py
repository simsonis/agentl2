"""
Configuration settings for the LLM module.
"""

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings


class LLMSettings(BaseSettings):
    """Configuration settings for the LLM chatbot."""

    # OpenAI API settings
    openai_api_key: str
    openai_model: str = "gpt-4"
    openai_max_tokens: int = 1000
    openai_temperature: float = 0.3

    # Search settings
    search_limit: int = 20
    enable_internal_search: bool = True
    enable_external_search: bool = True

    # External search settings
    casenote_timeout: int = 30
    casenote_max_results: int = 10

    # Response generation settings
    max_response_length: int = 2000
    confidence_threshold: float = 0.6
    max_sources: int = 5

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "json"

    class Config:
        env_prefix = "LLM_"
        env_file = ".env"


def get_llm_settings() -> LLMSettings:
    """Get LLM configuration settings."""
    return LLMSettings()