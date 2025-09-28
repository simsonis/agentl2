"""
Response Agent - Generates final legal responses based on search results.
"""

from __future__ import annotations

from typing import List, Dict, Any
from loguru import logger

from .base_agent import BaseAgent, AgentResponse, AgentAction, ConversationContext
from ..models import SearchResults, SearchResult, LegalResponse, SearchSource
from ..response.fact_checker import FactChecker
from ..response.source_validator import SourceValidator


class ResponseAgent(BaseAgent):
    """
    Response Agent that generates comprehensive legal responses.
    Acts as a senior legal advisor providing detailed and accurate advice.
    """

    def __init__(self, **kwargs):
        super().__init__(name="ResponseAgent", **kwargs)
        self.fact_checker = FactChecker()
        self.source_validator = SourceValidator()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the focused response agent."""
        return """너는 법률 답변 내용 생성 전문가야.
너는 20년차 시니어 파트너 변호사로서, 분석된 법적 정보를 바탕으로 사용자가 이해하기 쉬운 법률 답변을 작성하는 것이 너의 전문 분야야.

너의 집중 임무:
1. **핵심 답변 작성**: 사용자 질문에 대한 직접적이고 명확한 답변
2. **법적 근거 설명**: 해당 답변의 법적 근거와 논리 구조
3. **실무 가이드**: 실제 적용 시 절차와 주의사항
4. **예외 상황**: 일반 원칙의 예외나 특수 상황

답변 구조:
## 핵심 답변
[질문에 대한 직접적 답변]

## 법적 근거
[관련 법령과 해석]

## 실무 적용
[실제 절차와 방법]

## 주의사항
[예외상황과 위험요소]

중요 원칙:
- 근거가 되는 법령이나 판례는 [REF-001] 형태로 참조 번호만 표시
- 구체적인 조문 내용이나 판례 요지는 언급하지 말고 참조만 표시
- 출처의 정확성은 다른 Agent가 담당하므로 내용에만 집중
- 법적 결론을 명확히 하되, 불확실한 부분은 "추가 검토 필요" 표시

예시:
"가명정보 처리는 개인정보보호법 제28조의2 [REF-001]에 따라 특정 조건하에서 가능하며, 금융회사의 경우 신용정보법 [REF-002]의 추가 제약이 적용됩니다."

답변의 품질과 사용자 이해도에만 집중하고, 인용의 정확성은 별도 검증 과정에서 처리됩니다."""

    async def process(
        self,
        user_input: str,
        context: ConversationContext
    ) -> AgentResponse:
        """Generate final legal response based on search results."""

        logger.info("Response agent generating final answer")

        try:
            # Extract search results from context
            search_results = self._extract_search_results(context)

            if not search_results or search_results.total_count == 0:
                return await self._generate_no_results_response(context)

            # Verify and validate search results
            verified_results = await self.fact_checker.verify(search_results)
            validated_sources = await self.source_validator.validate_sources(verified_results)

            # Generate comprehensive response
            response_content = await self._generate_comprehensive_response(
                user_query=self._get_original_query(context),
                intent=context.extracted_intent,
                keywords=context.extracted_keywords,
                search_results=verified_results,
                conversation_context=context
            )

            # Generate follow-up questions
            follow_ups = await self._generate_follow_up_questions(
                context.extracted_intent,
                context.extracted_keywords,
                verified_results
            )

            return AgentResponse(
                action=AgentAction.COMPLETE,
                message=response_content,
                intent=context.extracted_intent,
                keywords=context.extracted_keywords,
                confidence=self._calculate_confidence(verified_results, validated_sources),
                metadata={
                    "sources": validated_sources,
                    "follow_up_questions": follow_ups,
                    "verified_results_count": len(verified_results),
                    "search_duration": getattr(search_results, 'search_duration', 0.0)
                }
            )

        except Exception as e:
            logger.error(f"Error in response agent: {e}")
            return await self._generate_error_response(str(e))

    async def _generate_comprehensive_response(
        self,
        user_query: str,
        intent: str,
        keywords: List[str],
        search_results: List[SearchResult],
        conversation_context: ConversationContext
    ) -> str:
        """Generate comprehensive legal response using LLM."""

        # Prepare search results context
        results_context = self._prepare_search_context(search_results)

        # Build conversation summary
        conversation_summary = self._build_conversation_summary(conversation_context)

        prompt = f"""법률 질문에 대한 전문적인 답변을 생성해줘.

질문: {user_query}
파악된 의도: {intent}
핵심 키워드: {', '.join(keywords)}

대화 맥락:
{conversation_summary}

검색된 법률 정보:
{results_context}

위 정보를 바탕으로 다음 구조로 전문적인 법률 답변을 생성해줘:

## 핵심 답변
질문에 대한 직접적이고 명확한 답변

## 관련 법령
적용되는 법령과 조문의 구체적 내용

## 판례 참조 (해당시)
관련 판례의 핵심 법리와 적용 기준

## 실무 가이드
실제 적용 시 절차나 주의사항

## 추가 고려사항
예외상황이나 변경 가능성, 개별 사안별 검토 필요사항

## 법률 조언의 한계
이 답변의 한계와 전문가 상담 권유

답변은 정확하고 실용적이며, 법률 전문가 수준의 품질로 작성해줘."""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=1500)
            return response

        except Exception as e:
            logger.error(f"LLM response generation failed: {e}")
            return self._generate_fallback_response(user_query, search_results)

    def _prepare_search_context(self, results: List[SearchResult]) -> str:
        """Prepare search results context for LLM."""

        if not results:
            return "관련 정보를 찾을 수 없습니다."

        context_parts = []

        for i, result in enumerate(results[:8], 1):  # Limit to top 8 results
            context_part = f"""
{i}. {result.title}
출처: {result.source.url}
유형: {result.source.source_type.value}
관련도: {result.relevance_score:.2f}
내용: {result.content[:400]}{'...' if len(result.content) > 400 else ''}
"""
            context_parts.append(context_part)

        return "\n".join(context_parts)

    def _build_conversation_summary(self, context: ConversationContext) -> str:
        """Build conversation summary for context."""

        if not context.user_messages:
            return "첫 질문입니다."

        summary_parts = [
            f"대화 턴: {len(context.user_messages)}회"
        ]

        if len(context.user_messages) > 1:
            summary_parts.append("이전 대화:")
            for i, msg in enumerate(context.user_messages[:-1], 1):
                summary_parts.append(f"  {i}. {msg[:100]}...")

        return "\n".join(summary_parts)

    async def _generate_follow_up_questions(
        self,
        intent: str,
        keywords: List[str],
        results: List[SearchResult]
    ) -> List[str]:
        """Generate relevant follow-up questions."""

        follow_ups = []

        # Intent-based follow-ups
        if "법령" in intent or "법률" in intent:
            follow_ups.extend([
                "이 법령의 시행령이나 시행규칙도 확인하고 싶으신가요?",
                "관련 판례도 함께 검토하시겠습니까?",
                "특정 조문의 적용 기준에 대해 더 자세히 알고 싶으신가요?"
            ])

        elif "판례" in intent:
            follow_ups.extend([
                "비슷한 사안의 다른 판례도 검토하시겠습니까?",
                "이 판례의 변경 가능성에 대해 알고 싶으신가요?",
                "실무 적용 시 주의사항이 궁금하신가요?"
            ])

        elif "절차" in intent:
            follow_ups.extend([
                "구체적인 서류나 양식이 필요하신가요?",
                "예상 소요 기간이나 비용에 대해 궁금하신가요?",
                "절차상 주의사항이나 함정이 있는지 알고 싶으신가요?"
            ])

        # Keyword-based follow-ups
        if any(keyword in " ".join(keywords) for keyword in ["개인정보", "정보보호"]):
            follow_ups.append("개인정보 처리 관련 구체적인 가이드라인이 필요하신가요?")

        if any(keyword in " ".join(keywords) for keyword in ["금융", "소비자"]):
            follow_ups.append("금융소비자 피해 구제 절차에 대해서도 알고 싶으신가요?")

        # Result-based follow-ups
        if results:
            has_precedent = any("판례" in r.title or "판결" in r.title for r in results)
            if has_precedent:
                follow_ups.append("관련 판례의 최신 동향이 궁금하신가요?")

        return follow_ups[:4]  # Limit to 4 follow-ups

    def _extract_search_results(self, context: ConversationContext) -> SearchResults:
        """Extract search results from conversation context."""

        if not context.agent_responses:
            return SearchResults()

        # Find the latest search agent response
        for response in reversed(context.agent_responses):
            if response.metadata and "search_results" in response.metadata:
                return response.metadata["search_results"]

        return SearchResults()

    def _get_original_query(self, context: ConversationContext) -> str:
        """Get the original user query."""
        return context.user_messages[0] if context.user_messages else "질문을 찾을 수 없습니다."

    def _calculate_confidence(
        self,
        results: List[SearchResult],
        sources: List[SearchSource]
    ) -> float:
        """Calculate overall confidence score."""

        if not results:
            return 0.0

        # Average source confidence
        avg_source_confidence = sum(s.confidence for s in sources) / len(sources) if sources else 0.0

        # Average relevance
        avg_relevance = sum(r.relevance_score for r in results) / len(results)

        # Result count factor
        count_factor = min(len(results) / 5.0, 1.0)

        # Weighted confidence
        confidence = (
            avg_source_confidence * 0.4 +
            avg_relevance * 0.4 +
            count_factor * 0.2
        )

        return min(confidence, 1.0)

    def _generate_fallback_response(
        self,
        user_query: str,
        results: List[SearchResult]
    ) -> str:
        """Generate fallback response when LLM fails."""

        if not results:
            return f"""죄송합니다. '{user_query}'에 대한 관련 정보를 찾을 수 없습니다.

다음 사항을 확인해 보세요:
- 검색어를 다르게 표현해 보세요
- 더 구체적인 키워드를 사용해 보세요
- 관련 법령명이나 조문 번호를 포함해 보세요

정확한 법률 조언이 필요하시면 전문가와 상담하시기 바랍니다."""

        # Simple response with search results
        response_parts = [
            f"'{user_query}'에 대한 검색 결과입니다.",
            "",
            "## 관련 정보"
        ]

        for i, result in enumerate(results[:3], 1):
            response_parts.extend([
                f"### {i}. {result.title}",
                f"{result.content[:300]}...",
                f"출처: {result.source.url}",
                ""
            ])

        response_parts.extend([
            "## 주의사항",
            "- 위 정보는 참고용이며 구체적인 상황에 따라 달라질 수 있습니다",
            "- 정확한 법률 조언은 전문가와 상담하시기 바랍니다",
            "- 최신 법령 개정사항을 확인하시기 바랍니다"
        ])

        return "\n".join(response_parts)

    async def _generate_no_results_response(self, context: ConversationContext) -> AgentResponse:
        """Generate response when no search results are available."""

        original_query = self._get_original_query(context)

        message = f"""죄송합니다. '{original_query}'에 대한 관련 법률 정보를 찾을 수 없습니다.

이런 경우를 시도해 보세요:

1. **키워드 변경**: 더 일반적이거나 구체적인 용어 사용
2. **법령명 직접 명시**: 관련 법률이나 규정명을 포함
3. **질문 재구성**: 다른 방식으로 질문을 표현

## 일반적인 법률 정보 검색 팁
- 개인정보보호법, 금융소비자보호법 등 정확한 법령명 사용
- "제00조", "시행령" 등 구체적인 조문 정보 포함
- "판례", "대법원" 등 판례 검색 시 명시

정확한 법률 상담이 필요하시면 해당 분야 전문 변호사와 상담하시기 바랍니다."""

        return AgentResponse(
            action=AgentAction.COMPLETE,
            message=message,
            confidence=0.2,
            metadata={"no_results": True}
        )

    async def _generate_error_response(self, error_message: str) -> AgentResponse:
        """Generate error response."""

        message = f"""답변 생성 중 오류가 발생했습니다.

오류 내용: {error_message}

다음을 시도해 보세요:
- 질문을 다시 입력해 보세요
- 더 간단한 형태로 질문해 보세요
- 잠시 후 다시 시도해 보세요

지속적인 문제가 발생하면 관리자에게 문의하시기 바랍니다."""

        return AgentResponse(
            action=AgentAction.COMPLETE,
            message=message,
            confidence=0.0,
            metadata={"error": error_message}
        )