"""
Data models for the legal chatbot system.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class QueryIntent(str, Enum):
    """Legal query intent categories."""
    LAW_SEARCH = "law_search"
    PRECEDENT_SEARCH = "precedent_search"
    LEGAL_INTERPRETATION = "legal_interpretation"
    PROCEDURAL_GUIDANCE = "procedural_guidance"
    COMPARATIVE_ANALYSIS = "comparative_analysis"
    GENERAL_INQUIRY = "general_inquiry"


class SourceType(str, Enum):
    """Types of information sources."""
    INTERNAL_LAW = "internal_law"
    INTERNAL_PRECEDENT = "internal_precedent"
    EXTERNAL_LAW = "external_law"
    EXTERNAL_PRECEDENT = "external_precedent"
    EXTERNAL_GENERAL = "external_general"


class SearchSource(BaseModel):
    """Information about a search result source."""
    url: str
    title: str
    source_type: SourceType
    confidence: float = Field(ge=0.0, le=1.0)
    date: Optional[datetime] = None
    excerpt: Optional[str] = None


class SearchResult(BaseModel):
    """Individual search result."""
    title: str
    content: str
    source: SearchSource
    relevance_score: float = Field(ge=0.0, le=1.0)
    keywords_matched: List[str] = Field(default_factory=list)


class SearchResults(BaseModel):
    """Collection of search results."""
    internal_results: List[SearchResult] = Field(default_factory=list)
    external_results: List[SearchResult] = Field(default_factory=list)
    total_count: int = 0
    search_duration: float = 0.0

    def add_internal(self, results: List[SearchResult]) -> None:
        """Add internal search results."""
        self.internal_results.extend(results)
        self.total_count += len(results)

    def add_external(self, results: List[SearchResult]) -> None:
        """Add external search results."""
        self.external_results.extend(results)
        self.total_count += len(results)

    def get_all_results(self) -> List[SearchResult]:
        """Get all search results combined."""
        return self.internal_results + self.external_results


class LegalQuery(BaseModel):
    """Processed legal query."""
    original_text: str
    intent: QueryIntent
    keywords: List[str]
    legal_entities: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class LegalResponse(BaseModel):
    """Final response to legal query."""
    answer: str
    sources: List[SearchSource]
    confidence: float = Field(ge=0.0, le=1.0)
    related_keywords: List[str] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    processing_time: float = 0.0
    query: Optional[LegalQuery] = None


class VerificationResult(BaseModel):
    """Result of information verification."""
    is_verified: bool
    confidence: float = Field(ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)