"""
Keyword extraction for legal queries.
"""

from __future__ import annotations

import re
from typing import List, Set, Dict
from collections import Counter


class KeywordExtractor:
    """Extracts relevant keywords from legal queries."""

    def __init__(self):
        # Legal domain-specific keywords
        self.legal_keywords = {
            # 개인정보보호 관련
            "개인정보", "가명정보", "익명정보", "개인정보보호법", "정보보호",
            "개인식별", "동의", "수집", "이용", "제공", "처리", "파기",

            # 금융 관련
            "금융소비자보호법", "신용정보", "금융상품", "불완전판매", "설명의무",
            "은행", "보험", "증권", "투자", "대출",

            # 일반 법률 용어
            "법령", "법률", "시행령", "시행규칙", "조문", "항", "호",
            "판례", "판결", "대법원", "고등법원", "지방법원",
            "권리", "의무", "책임", "손해배상", "위법", "합법",

            # 절차 관련
            "신청", "접수", "승인", "허가", "등록", "신고", "보고",
            "심사", "검토", "결정", "통지", "공고", "공시"
        }

        # Stopwords to exclude
        self.stopwords = {
            '이', '가', '을', '를', '의', '에', '는', '은', '와', '과', '도', '만',
            '하다', '있다', '되다', '이다', '아니다', '같다', '다르다',
            '그', '저', '이것', '저것', '여기', '거기', '이곳', '저곳',
            '무엇', '어떤', '어떻게', '왜', '언제', '어디서', '누가', '누구',
            '할', '한', '할수', '있는', '없는', '되는', '안되는',
            '때문', '위해', '통해', '대해', '관해', '따라', '의해'
        }

    async def extract(self, text: str) -> List[str]:
        """Extract keywords from text."""
        # Normalize text
        normalized_text = self._normalize_text(text)

        # Extract candidate words
        candidates = self._extract_candidates(normalized_text)

        # Score and rank keywords
        scored_keywords = self._score_keywords(candidates, normalized_text)

        # Return top keywords
        return [keyword for keyword, score in scored_keywords[:15]]

    def _normalize_text(self, text: str) -> str:
        """Normalize text for keyword extraction."""
        # Remove special characters except Korean, numbers, and spaces
        text = re.sub(r'[^\w\s가-힣]', ' ', text)

        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())

        return text

    def _extract_candidates(self, text: str) -> List[str]:
        """Extract candidate keywords."""
        candidates = []

        # Extract single words (2+ characters)
        words = re.findall(r'[가-힣]{2,}', text)
        candidates.extend(words)

        # Extract compound terms (legal phrases)
        compound_patterns = [
            r'[가-힣]+법',          # Laws ending with '법'
            r'[가-힣]+령',          # Decrees ending with '령'
            r'[가-힣]+규칙',        # Rules ending with '규칙'
            r'[가-힣]+정보',        # Information terms
            r'[가-힣]+보호',        # Protection terms
            r'[가-힣]+의무',        # Obligation terms
            r'[가-힣]+권리',        # Rights terms
        ]

        for pattern in compound_patterns:
            matches = re.findall(pattern, text)
            candidates.extend(matches)

        # Filter out stopwords
        candidates = [word for word in candidates if word not in self.stopwords]

        return candidates

    def _score_keywords(self, candidates: List[str], text: str) -> List[tuple]:
        """Score and rank keywords by relevance."""
        keyword_scores = {}
        word_counts = Counter(candidates)

        for word, frequency in word_counts.items():
            score = 0.0

            # Frequency score (normalized)
            score += min(frequency / len(candidates), 0.5)

            # Legal domain relevance
            if word in self.legal_keywords:
                score += 0.5

            # Length bonus (prefer longer, more specific terms)
            if len(word) >= 3:
                score += 0.1
            if len(word) >= 5:
                score += 0.1

            # Position bonus (words at the beginning are often more important)
            first_occurrence = text.find(word)
            if first_occurrence < len(text) * 0.3:  # First 30% of text
                score += 0.2

            keyword_scores[word] = score

        # Sort by score descending
        return sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)

    def extract_legal_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract specific legal entities categorized by type."""
        entities = {
            'laws': [],
            'courts': [],
            'case_numbers': [],
            'dates': [],
            'monetary_amounts': []
        }

        # Law patterns
        law_patterns = [
            r'[가-힣\s]*법(?:률)?',
            r'[가-힣\s]*령',
            r'[가-힣\s]*규칙',
            r'[가-힣\s]*규정'
        ]

        for pattern in law_patterns:
            matches = re.findall(pattern, text)
            entities['laws'].extend([match.strip() for match in matches if len(match.strip()) > 2])

        # Court patterns
        court_patterns = [
            r'대법원',
            r'[가-힣]*고등법원',
            r'[가-힣]*지방법원',
            r'[가-힣]*법원'
        ]

        for pattern in court_patterns:
            matches = re.findall(pattern, text)
            entities['courts'].extend(matches)

        # Case number patterns
        case_number_pattern = r'\d{4}[가-힣]\d+'
        entities['case_numbers'] = re.findall(case_number_pattern, text)

        # Date patterns
        date_patterns = [
            r'\d{4}년\s*\d{1,2}월\s*\d{1,2}일',
            r'\d{4}\.\d{1,2}\.\d{1,2}',
            r'\d{4}-\d{1,2}-\d{1,2}'
        ]

        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            entities['dates'].extend(matches)

        # Monetary amount patterns
        money_patterns = [
            r'\d+억\s*원',
            r'\d+만\s*원',
            r'\d+원'
        ]

        for pattern in money_patterns:
            matches = re.findall(pattern, text)
            entities['monetary_amounts'].extend(matches)

        return entities