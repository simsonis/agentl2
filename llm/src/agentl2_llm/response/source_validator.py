"""
Source validation and citation management.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Set
from urllib.parse import urlparse

from ..models import SearchResult, SearchSource, SourceType


class SourceValidator:
    """Validates and manages source citations."""

    def __init__(self):
        # Authoritative legal sources
        self.authoritative_sources = {
            "law.go.kr": {
                "name": "국가법령정보센터",
                "authority_level": "official",
                "reliability": 0.95
            },
            "scourt.go.kr": {
                "name": "대법원",
                "authority_level": "official",
                "reliability": 0.95
            },
            "court.go.kr": {
                "name": "법원",
                "authority_level": "official",
                "reliability": 0.9
            },
            "casenote.kr": {
                "name": "케이스노트",
                "authority_level": "secondary",
                "reliability": 0.75
            }
        }

    async def validate_sources(self, results: List[SearchResult]) -> List[SearchSource]:
        """Validate and rank sources by reliability."""
        validated_sources = []

        for result in results:
            source = result.source
            validation_score = await self._validate_single_source(source)

            if validation_score >= 0.5:  # Minimum threshold
                # Update source confidence with validation score
                source.confidence = min(source.confidence * validation_score, 1.0)
                validated_sources.append(source)

        # Sort by confidence (descending)
        validated_sources.sort(key=lambda s: s.confidence, reverse=True)

        return validated_sources

    async def _validate_single_source(self, source: SearchSource) -> float:
        """Validate a single source."""
        score = 0.0

        # Domain authority check
        domain_score = self._check_domain_authority(source.url)
        score += domain_score * 0.5

        # URL structure check
        url_score = self._check_url_structure(source.url)
        score += url_score * 0.2

        # Content type appropriateness
        content_score = self._check_content_type(source)
        score += content_score * 0.2

        # Recency check
        recency_score = self._check_recency(source.date)
        score += recency_score * 0.1

        return min(score, 1.0)

    def _check_domain_authority(self, url: str) -> float:
        """Check domain authority and reliability."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            for auth_domain, info in self.authoritative_sources.items():
                if auth_domain in domain:
                    return info["reliability"]

            # Check for government domains
            if domain.endswith('.go.kr'):
                return 0.9
            elif domain.endswith('.kr'):
                return 0.6
            else:
                return 0.4

        except:
            return 0.2

    def _check_url_structure(self, url: str) -> float:
        """Check URL structure for legitimacy."""
        try:
            parsed = urlparse(url)

            score = 0.5  # Base score

            # HTTPS bonus
            if parsed.scheme == 'https':
                score += 0.3

            # Reasonable path length
            if len(parsed.path) > 0 and len(parsed.path) < 200:
                score += 0.2

            # No suspicious parameters
            if not any(suspicious in url.lower() for suspicious in ['redirect', 'click', 'ad']):
                score += 0.1

            return min(score, 1.0)

        except:
            return 0.1

    def _check_content_type(self, source: SearchSource) -> float:
        """Check if content type matches source type."""
        score = 0.5  # Base score

        # Check title for legal content indicators
        legal_indicators = {
            SourceType.EXTERNAL_LAW: ["법령", "법률", "조문", "규정", "시행령"],
            SourceType.EXTERNAL_PRECEDENT: ["판례", "판결", "대법원", "결정", "명령"],
        }

        if source.source_type in legal_indicators:
            indicators = legal_indicators[source.source_type]
            title_lower = source.title.lower()

            matches = sum(1 for indicator in indicators if indicator in title_lower)
            score += min(matches * 0.1, 0.4)

        return min(score, 1.0)

    def _check_recency(self, date: datetime | None) -> float:
        """Check how recent the source is."""
        if not date:
            return 0.5  # Neutral for unknown dates

        now = datetime.now()
        age_days = (now - date).days

        if age_days <= 30:
            return 1.0
        elif age_days <= 365:
            return 0.8
        elif age_days <= 365 * 2:
            return 0.6
        else:
            return 0.4


class CitationManager:
    """Manages citation formatting and source attribution."""

    def __init__(self):
        pass

    def format_citations(self, sources: List[SearchSource]) -> List[str]:
        """Format sources into proper citations."""
        citations = []

        for i, source in enumerate(sources, 1):
            citation = self._format_single_citation(source, i)
            citations.append(citation)

        return citations

    def _format_single_citation(self, source: SearchSource, index: int) -> str:
        """Format a single source citation."""
        # Determine source type
        domain = self._extract_domain(source.url)
        authority_info = self._get_authority_info(domain)

        # Basic citation format
        citation = f"[{index}] {source.title}"

        # Add source authority
        if authority_info:
            citation += f" - {authority_info['name']}"

        # Add date if available
        if source.date:
            date_str = source.date.strftime("%Y.%m.%d")
            citation += f" ({date_str})"

        # Add URL
        citation += f" <{source.url}>"

        return citation

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except:
            return ""

    def _get_authority_info(self, domain: str) -> Dict | None:
        """Get authority information for domain."""
        validator = SourceValidator()
        for auth_domain, info in validator.authoritative_sources.items():
            if auth_domain in domain:
                return info
        return None

    def generate_source_summary(self, sources: List[SearchSource]) -> str:
        """Generate a summary of sources used."""
        if not sources:
            return "출처 정보가 없습니다."

        summary_parts = []

        # Count by authority level
        official_count = 0
        secondary_count = 0

        for source in sources:
            domain = self._extract_domain(source.url)
            authority_info = self._get_authority_info(domain)

            if authority_info and authority_info['authority_level'] == 'official':
                official_count += 1
            else:
                secondary_count += 1

        # Build summary
        if official_count > 0:
            summary_parts.append(f"공식 출처 {official_count}건")

        if secondary_count > 0:
            summary_parts.append(f"참고 출처 {secondary_count}건")

        summary = "참조: " + ", ".join(summary_parts)

        # Add reliability note
        avg_confidence = sum(s.confidence for s in sources) / len(sources)
        if avg_confidence >= 0.8:
            reliability = "높음"
        elif avg_confidence >= 0.6:
            reliability = "보통"
        else:
            reliability = "낮음"

        summary += f" (신뢰도: {reliability})"

        return summary