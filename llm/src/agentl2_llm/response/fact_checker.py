"""
Fact checking and information verification.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import List, Dict, Set

from loguru import logger

from ..models import SearchResult, SearchResults, VerificationResult, SourceType


class FactChecker:
    """Verifies the accuracy and reliability of search results."""

    def __init__(self):
        # Source reliability scores
        self.source_reliability = {
            SourceType.INTERNAL_LAW: 0.95,
            SourceType.INTERNAL_PRECEDENT: 0.95,
            SourceType.EXTERNAL_LAW: 0.75,
            SourceType.EXTERNAL_PRECEDENT: 0.75,
            SourceType.EXTERNAL_GENERAL: 0.60,
        }

        # Trusted external domains
        self.trusted_domains = {
            "casenote.kr": 0.8,
            "law.go.kr": 0.95,
            "scourt.go.kr": 0.9,
            "court.go.kr": 0.9,
        }

    async def verify(self, search_results: SearchResults) -> List[SearchResult]:
        """Verify and filter search results based on reliability."""
        verified_results = []

        all_results = search_results.get_all_results()
        logger.info(f"Verifying {len(all_results)} search results")

        for result in all_results:
            verification = await self._verify_single_result(result)

            if verification.is_verified:
                verified_results.append(result)
                logger.debug(f"Verified result: {result.title[:50]}...")
            else:
                logger.warning(f"Failed verification: {result.title[:50]}... - {verification.issues}")

        logger.info(f"Verification completed: {len(verified_results)}/{len(all_results)} results passed")
        return verified_results

    async def _verify_single_result(self, result: SearchResult) -> VerificationResult:
        """Verify a single search result."""
        issues = []
        score = 0.0

        # Source type reliability
        base_score = self.source_reliability.get(result.source.source_type, 0.5)
        score += base_score * 0.4

        # Domain trust score
        domain_score = self._get_domain_trust_score(result.source.url)
        score += domain_score * 0.3

        # Content quality score
        content_score = self._assess_content_quality(result)
        score += content_score * 0.2

        # Recency score
        recency_score = self._assess_recency(result.source.date)
        score += recency_score * 0.1

        # Check for potential issues
        issues.extend(self._check_content_issues(result))

        # Final verification decision
        is_verified = score >= 0.6 and len(issues) == 0

        return VerificationResult(
            is_verified=is_verified,
            confidence=min(score, 1.0),
            issues=issues,
            recommendations=self._generate_recommendations(result, score, issues)
        )

    def _get_domain_trust_score(self, url: str) -> float:
        """Get trust score for the domain."""
        try:
            domain = url.split("//")[1].split("/")[0].lower()
            for trusted_domain, score in self.trusted_domains.items():
                if trusted_domain in domain:
                    return score
            return 0.5  # Default for unknown domains
        except:
            return 0.3  # Low score for malformed URLs

    def _assess_content_quality(self, result: SearchResult) -> float:
        """Assess the quality of the content."""
        score = 0.0

        # Length check
        content_length = len(result.content)
        if content_length > 50:
            score += 0.3
        if content_length > 200:
            score += 0.2

        # Legal terminology check
        legal_terms = [
            "법령", "법률", "조문", "판례", "판결", "대법원", "고등법원",
            "민법", "상법", "형법", "개인정보보호법", "금융소비자보호법"
        ]

        legal_term_count = sum(1 for term in legal_terms if term in result.content)
        score += min(legal_term_count * 0.1, 0.3)

        # Title-content relevance
        title_words = set(result.title.split())
        content_words = set(result.content.split())
        overlap = len(title_words & content_words) / max(len(title_words), 1)
        score += overlap * 0.2

        return min(score, 1.0)

    def _assess_recency(self, date: datetime | None) -> float:
        """Assess how recent the information is."""
        if not date:
            return 0.5  # Neutral score for unknown dates

        now = datetime.now()
        age_days = (now - date).days

        if age_days <= 30:
            return 1.0
        elif age_days <= 365:
            return 0.8
        elif age_days <= 365 * 3:
            return 0.6
        else:
            return 0.4

    def _check_content_issues(self, result: SearchResult) -> List[str]:
        """Check for potential content issues."""
        issues = []

        # Check for extremely short content
        if len(result.content.strip()) < 20:
            issues.append("Content too short")

        # Check for repetitive content
        words = result.content.split()
        if len(set(words)) < len(words) * 0.3:
            issues.append("Highly repetitive content")

        # Check for suspicious patterns
        suspicious_patterns = [
            r"click here",
            r"광고",
            r"스팸",
            r"로그인.*필요",
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, result.content, re.IGNORECASE):
                issues.append(f"Suspicious content pattern: {pattern}")

        # Check for broken formatting
        if result.content.count('\n\n') > 10:
            issues.append("Excessive line breaks")

        return issues

    def _generate_recommendations(
        self,
        result: SearchResult,
        score: float,
        issues: List[str]
    ) -> List[str]:
        """Generate recommendations for improving result reliability."""
        recommendations = []

        if score < 0.7:
            recommendations.append("Consider cross-referencing with official legal sources")

        if result.source.source_type in [SourceType.EXTERNAL_LAW, SourceType.EXTERNAL_PRECEDENT]:
            recommendations.append("Verify information with primary legal sources")

        if issues:
            recommendations.append("Review content quality issues before using")

        if not result.source.date:
            recommendations.append("Check the publication or update date")

        return recommendations


class ConsistencyChecker:
    """Checks for consistency across multiple search results."""

    def __init__(self):
        pass

    async def check_consistency(self, results: List[SearchResult]) -> Dict[str, any]:
        """Check for consistency across search results."""
        if len(results) < 2:
            return {"consistent": True, "confidence": 1.0, "conflicts": []}

        conflicts = []
        key_facts = self._extract_key_facts(results)

        # Check for contradictions in key facts
        for fact_type, facts in key_facts.items():
            if len(set(facts)) > 1:
                conflicts.append({
                    "type": fact_type,
                    "conflicting_values": list(set(facts)),
                    "sources": [r.source.url for r in results]
                })

        consistency_score = max(0.0, 1.0 - (len(conflicts) * 0.2))

        return {
            "consistent": len(conflicts) == 0,
            "confidence": consistency_score,
            "conflicts": conflicts,
            "total_results_checked": len(results)
        }

    def _extract_key_facts(self, results: List[SearchResult]) -> Dict[str, List[str]]:
        """Extract key facts from search results for consistency checking."""
        key_facts = {
            "dates": [],
            "legal_references": [],
            "monetary_amounts": [],
            "case_numbers": []
        }

        for result in results:
            content = result.title + " " + result.content

            # Extract dates
            date_patterns = [
                r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',
                r'\d{4}\.\d{1,2}\.\d{1,2}',
                r'\d{4}-\d{1,2}-\d{1,2}'
            ]
            for pattern in date_patterns:
                dates = re.findall(pattern, content)
                key_facts["dates"].extend(dates)

            # Extract legal references
            legal_refs = re.findall(r'[가-힣\s]+법(?:률)?', content)
            key_facts["legal_references"].extend(legal_refs)

            # Extract monetary amounts
            money_patterns = [r'\d+억\s*원', r'\d+만\s*원', r'\d+원']
            for pattern in money_patterns:
                amounts = re.findall(pattern, content)
                key_facts["monetary_amounts"].extend(amounts)

            # Extract case numbers
            case_numbers = re.findall(r'\d{4}[가-힣]\d+', content)
            key_facts["case_numbers"].extend(case_numbers)

        return key_facts