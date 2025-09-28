"""
Response generation using LLM.
"""

from __future__ import annotations

import json
import time
from typing import List, Optional

import openai
from loguru import logger

from ..models import LegalQuery, SearchResult, LegalResponse, SearchSource
from .fact_checker import FactChecker, ConsistencyChecker
from .source_validator import SourceValidator, CitationManager


class ResponseGenerator:
    """Generates responses to legal queries using LLM."""

    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = openai.AsyncOpenAI(api_key=api_key)
        self.model = model
        self.fact_checker = FactChecker()
        self.consistency_checker = ConsistencyChecker()
        self.source_validator = SourceValidator()
        self.citation_manager = CitationManager()

        # Response generation prompts
        self.system_prompt = """당신은 대한민국의 법률 전문가입니다. 사용자의 법률 질문에 대해 정확하고 신뢰할 수 있는 답변을 제공해야 합니다.

다음 원칙을 따르세요:
1. 제공된 검색 결과만을 바탕으로 답변하세요
2. 법률 용어를 정확히 사용하세요
3. 출처를 명확히 밝히세요
4. 불확실한 정보는 명시하세요
5. 실용적인 조언을 포함하세요

답변 형식:
- 간결하고 명확한 설명
- 관련 법령이나 판례 인용
- 실무상 주의사항
- 추가 확인이 필요한 사항"""

    async def generate(
        self,
        query: LegalQuery,
        search_results: List[SearchResult],
        max_tokens: int = 1000
    ) -> LegalResponse:
        """Generate a comprehensive legal response."""
        start_time = time.time()

        try:
            # Verify and validate information
            # Convert search_results to SearchResults if it's a list
            if isinstance(search_results, list):
                from ..models import SearchResults
                search_results_obj = SearchResults()
                search_results_obj.external_results = search_results
                search_results_obj.total_count = len(search_results)
                verified_results = await self.fact_checker.verify(search_results_obj)
            else:
                verified_results = await self.fact_checker.verify(search_results)
            validated_sources = await self.source_validator.validate_sources(verified_results)

            # Check consistency
            consistency_check = await self.consistency_checker.check_consistency(verified_results)

            # Generate response using LLM
            response_text = await self._generate_llm_response(
                query, verified_results, consistency_check, max_tokens
            )

            # Generate follow-up questions
            follow_ups = await self._generate_follow_up_questions(query, verified_results)

            # Create response
            response = LegalResponse(
                answer=response_text,
                sources=validated_sources,
                confidence=self._calculate_overall_confidence(verified_results, consistency_check),
                related_keywords=self._extract_related_keywords(verified_results),
                follow_up_questions=follow_ups,
                processing_time=time.time() - start_time,
                query=query
            )

            logger.info(f"Generated response for query: {query.original_text[:50]}...")
            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._generate_fallback_response(query, search_results)

    async def _generate_llm_response(
        self,
        query: LegalQuery,
        results: List[SearchResult],
        consistency_check: dict,
        max_tokens: int
    ) -> str:
        """Generate response using LLM."""

        # Prepare context from search results
        context = self._prepare_context(results)

        # Build user prompt
        user_prompt = f"""질문: {query.original_text}

질문 분석:
- 의도: {query.intent.value}
- 주요 키워드: {', '.join(query.keywords)}
- 법률 관련 용어: {', '.join(query.legal_entities)}

검색 결과:
{context}

일관성 검증:
- 정보 일관성: {'일치함' if consistency_check['consistent'] else '일부 불일치'}
- 신뢰도: {consistency_check['confidence']:.2f}
{f"- 충돌 사항: {consistency_check['conflicts']}" if consistency_check['conflicts'] else ""}

위 정보를 바탕으로 질문에 대한 정확하고 유용한 답변을 제공해 주세요."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.3,  # Lower temperature for more consistent legal advice
                presence_penalty=0.1,
                frequency_penalty=0.1
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"LLM API error: {e}")
            return self._generate_template_response(query, results)

    def _prepare_context(self, results: List[SearchResult]) -> str:
        """Prepare context from search results for LLM."""
        if not results:
            return "관련 정보를 찾을 수 없습니다."

        context_parts = []

        for i, result in enumerate(results[:5], 1):  # Limit to top 5 results
            context_part = f"""
{i}. {result.title}
출처: {result.source.url}
내용: {result.content[:300]}{'...' if len(result.content) > 300 else ''}
관련도: {result.relevance_score:.2f}
"""
            context_parts.append(context_part)

        return "\n".join(context_parts)

    async def _generate_follow_up_questions(
        self,
        query: LegalQuery,
        results: List[SearchResult]
    ) -> List[str]:
        """Generate relevant follow-up questions."""
        follow_ups = []

        # Intent-based follow-ups
        if query.intent.value == "law_search":
            follow_ups.extend([
                "이 법령의 시행령이나 시행규칙도 확인하고 싶으신가요?",
                "관련 판례도 함께 찾아보시겠습니까?",
                "특정 조문의 해석에 대해 더 자세히 알고 싶으신가요?"
            ])
        elif query.intent.value == "precedent_search":
            follow_ups.extend([
                "비슷한 사안의 다른 판례도 확인하시겠습니까?",
                "이 판례의 법리가 적용되는 다른 사례가 궁금하신가요?",
                "관련 법령 조문도 함께 확인하시겠습니까?"
            ])
        elif query.intent.value == "legal_interpretation":
            follow_ups.extend([
                "구체적인 적용 사례가 궁금하신가요?",
                "예외 상황이나 특별한 경우도 알고 싶으신가요?",
                "실무상 주의사항이 궁금하신가요?"
            ])

        # Keyword-based follow-ups
        if "개인정보" in query.keywords:
            follow_ups.append("개인정보 처리 관련 절차나 의무사항도 확인하시겠습니까?")

        if "금융" in " ".join(query.keywords):
            follow_ups.append("금융소비자 보호 관련 구제절차도 알고 싶으신가요?")

        return follow_ups[:3]  # Limit to 3 follow-ups

    def _calculate_overall_confidence(
        self,
        results: List[SearchResult],
        consistency_check: dict
    ) -> float:
        """Calculate overall confidence score."""
        if not results:
            return 0.0

        # Average source confidence
        avg_source_confidence = sum(r.source.confidence for r in results) / len(results)

        # Average relevance score
        avg_relevance = sum(r.relevance_score for r in results) / len(results)

        # Consistency score
        consistency_score = consistency_check.get('confidence', 0.0)

        # Result count factor
        count_factor = min(len(results) / 5.0, 1.0)  # Normalized to 5 results

        # Weighted average
        confidence = (
            avg_source_confidence * 0.4 +
            avg_relevance * 0.3 +
            consistency_score * 0.2 +
            count_factor * 0.1
        )

        return min(confidence, 1.0)

    def _extract_related_keywords(self, results: List[SearchResult]) -> List[str]:
        """Extract related keywords from search results."""
        all_keywords = []

        for result in results:
            all_keywords.extend(result.keywords_matched)

        # Count and sort by frequency
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        # Return top keywords
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, count in sorted_keywords[:10]]

    def _generate_template_response(self, query: LegalQuery, results: List[SearchResult]) -> str:
        """Generate a template response when LLM is unavailable."""
        if not results:
            return f"""죄송합니다. '{query.original_text}'에 대한 관련 정보를 찾을 수 없습니다.

다음 사항을 확인해 보세요:
- 검색어를 다르게 표현해 보세요
- 더 구체적인 키워드를 사용해 보세요
- 관련 법령명이나 조문 번호를 포함해 보세요

추가 도움이 필요하시면 전문가와 상담하시기 바랍니다."""

        # Simple template response
        response_parts = [
            f"'{query.original_text}'에 대한 검색 결과를 찾았습니다.",
            "",
            "주요 정보:",
        ]

        for i, result in enumerate(results[:3], 1):
            response_parts.append(f"{i}. {result.title}")
            response_parts.append(f"   {result.content[:200]}...")
            response_parts.append("")

        response_parts.extend([
            "⚠️ 주의사항:",
            "- 위 정보는 참고용이며 구체적인 상황에 따라 달라질 수 있습니다",
            "- 정확한 법률 조언은 전문가와 상담하시기 바랍니다",
            "- 최신 법령 개정사항을 확인하시기 바랍니다"
        ])

        return "\n".join(response_parts)

    def _generate_fallback_response(self, query: LegalQuery, results: List[SearchResult]) -> LegalResponse:
        """Generate a fallback response when main generation fails."""
        return LegalResponse(
            answer=self._generate_template_response(query, results),
            sources=[result.source for result in results[:5]],
            confidence=0.5,
            related_keywords=query.keywords,
            follow_up_questions=[
                "더 구체적인 질문으로 다시 검색해 보시겠습니까?",
                "관련 법령이나 조문을 직접 확인하시겠습니까?"
            ],
            processing_time=1.0,
            query=query
        )