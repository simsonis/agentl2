"""
Intent classification for legal queries.
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

from ..models import QueryIntent, LegalQuery


class IntentClassifier:
    """Classifies the intent of legal queries."""

    def __init__(self):
        # Intent classification patterns
        self.intent_patterns = {
            QueryIntent.LAW_SEARCH: [
                r"법령|법률|조문|시행령|시행규칙|규정",
                r"어떤 법|무슨 법|관련 법령",
                r"법조문|법률 조항",
            ],
            QueryIntent.PRECEDENT_SEARCH: [
                r"판례|판결|결정|명령",
                r"대법원|고등법원|지방법원",
                r"사건번호|판결문",
            ],
            QueryIntent.LEGAL_INTERPRETATION: [
                r"해석|의미|뜻|어떻게 이해",
                r"적용.*방법|적용.*기준",
                r"법적.*의미|법률적.*의미",
            ],
            QueryIntent.PROCEDURAL_GUIDANCE: [
                r"절차|순서|방법|과정",
                r"어떻게.*해야|어떻게.*진행",
                r"신청.*방법|접수.*방법",
            ],
            QueryIntent.COMPARATIVE_ANALYSIS: [
                r"차이|비교|다른점|구별",
                r"vs|대비|대조",
                r"어떤.*다른|무엇.*다른",
            ],
        }

        # Legal entity patterns
        self.legal_entity_patterns = [
            r"개인정보보호법",
            r"정보통신망.*이용촉진.*정보보호.*법",
            r"신용정보.*이용.*보호.*법",
            r"금융소비자보호법",
            r"가명정보|익명정보|개인정보",
            r"민법|상법|형법|행정법",
        ]

    async def classify(self, query_text: str) -> LegalQuery:
        """Classify the intent of a legal query."""
        # Clean and normalize text
        normalized_text = self._normalize_text(query_text)

        # Extract legal entities
        legal_entities = self._extract_legal_entities(normalized_text)

        # Classify intent
        intent, confidence = self._classify_intent(normalized_text)

        # Extract keywords
        keywords = self._extract_keywords(normalized_text)

        return LegalQuery(
            original_text=query_text,
            intent=intent,
            keywords=keywords,
            legal_entities=legal_entities,
            confidence=confidence,
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for processing."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def _classify_intent(self, text: str) -> Tuple[QueryIntent, float]:
        """Classify the intent with confidence score."""
        intent_scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches * 0.3  # Weight each match
            intent_scores[intent] = min(score, 1.0)

        if not intent_scores or max(intent_scores.values()) < 0.2:
            return QueryIntent.GENERAL_INQUIRY, 0.5

        best_intent = max(intent_scores, key=intent_scores.get)
        confidence = intent_scores[best_intent]

        return best_intent, confidence

    def _extract_legal_entities(self, text: str) -> List[str]:
        """Extract legal entities from text."""
        entities = []
        for pattern in self.legal_entity_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)

        return list(set(entities))  # Remove duplicates

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract relevant keywords from text."""
        # Remove common stopwords
        stopwords = {
            '이', '가', '을', '를', '의', '에', '는', '은', '와', '과',
            '하다', '있다', '되다', '이다', '그', '저', '이것', '저것',
            '무엇', '어떤', '어떻게', '왜', '언제', '어디서'
        }

        # Split into words and filter
        words = re.findall(r'[가-힣]+', text)
        keywords = [word for word in words if len(word) > 1 and word not in stopwords]

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        return unique_keywords[:10]  # Limit to top 10 keywords