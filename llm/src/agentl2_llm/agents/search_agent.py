"""
Search Agent - Handles search execution based on extracted intent and keywords.
"""

from __future__ import annotations

from typing import List, Dict, Any
from loguru import logger

from .base_agent import BaseAgent, AgentResponse, AgentAction, ConversationContext
from ..search.search_coordinator import SearchCoordinator
from ..models import SearchResults, QueryIntent


class SearchAgent(BaseAgent):
    """
    Search Agent that performs search based on user intent and keywords.
    Coordinates between internal and external search sources.
    """

    def __init__(self, search_coordinator: SearchCoordinator, **kwargs):
        super().__init__(name="SearchAgent", **kwargs)
        self.search_coordinator = search_coordinator

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the search agent."""
        return """너는 법률 검색 전문 에이전트야.

사용자의 의도와 키워드를 받아서 관련 법령과 판례를 효과적으로 검색하는 것이 너의 역할이야.

검색 과정에서 다음을 수행해:
1. 키워드 최적화: 법률 검색에 더 효과적인 키워드로 보완하거나 확장
2. 검색 전략 수립: 법령 검색과 판례 검색의 우선순위 결정
3. 검색 결과 평가: 검색된 결과의 관련성과 신뢰성 평가

검색 결과가 부족하거나 관련성이 낮으면 키워드를 조정해서 재검색을 시도해.

너의 목표는 사용자의 법률 질의에 가장 적합한 정보를 찾는 것이야."""

    async def process(
        self,
        user_input: str,
        context: ConversationContext
    ) -> AgentResponse:
        """Process search based on extracted intent and keywords."""

        logger.info(f"Search agent processing with intent: {context.extracted_intent}")

        try:
            # Get intent and keywords from context
            intent = context.extracted_intent or "general_inquiry"
            keywords = context.extracted_keywords or []

            if not keywords:
                # Try to extract keywords from user input
                keywords = await self._extract_emergency_keywords(user_input)

            # Convert intent to QueryIntent enum
            query_intent = self._map_intent_to_enum(intent)

            # Enhance keywords using LLM
            enhanced_keywords = await self._enhance_keywords(intent, keywords, user_input)

            # Perform search
            search_results = await self.search_coordinator.search(
                keywords=enhanced_keywords,
                intent=query_intent,
                include_internal=True,
                include_external=True,
                limit=20
            )

            # Evaluate search results
            evaluation = await self._evaluate_search_results(
                search_results, intent, enhanced_keywords
            )

            # Decide next action based on results
            if evaluation["should_retry"]:
                # Retry with different keywords
                retry_keywords = evaluation["suggested_keywords"]
                logger.info(f"Retrying search with keywords: {retry_keywords}")

                search_results = await self.search_coordinator.search(
                    keywords=retry_keywords,
                    intent=query_intent,
                    include_internal=True,
                    include_external=True,
                    limit=15
                )

            return AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message=f"{search_results.total_count}건의 관련 정보를 찾았습니다.",
                intent=intent,
                keywords=enhanced_keywords,
                confidence=evaluation["confidence"],
                metadata={
                    "search_results": search_results,
                    "evaluation": evaluation,
                    "search_duration": search_results.search_duration
                }
            )

        except Exception as e:
            logger.error(f"Error in search agent: {e}")
            return AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message="검색 중 오류가 발생했지만 가능한 정보로 답변을 생성하겠습니다.",
                confidence=0.3,
                metadata={"error": str(e)}
            )

    async def _enhance_keywords(
        self,
        intent: str,
        keywords: List[str],
        user_input: str
    ) -> List[str]:
        """Enhance keywords using LLM for better search results."""

        prompt = f"""법률 검색을 위한 키워드 최적화를 해줘.

사용자 의도: {intent}
기존 키워드: {', '.join(keywords)}
사용자 질문: {user_input}

다음을 고려해서 검색 키워드를 최적화해줘:
1. 법령명과 조문번호 추가
2. 관련 판례 검색을 위한 법률 용어
3. 동의어와 유사 개념
4. 제외해야 할 불필요한 키워드

최적화된 키워드를 콤마로 구분해서 10개 이내로 제공해줘."""

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=300)

            # Extract keywords from response
            enhanced_keywords = []
            for line in response.split('\n'):
                if ',' in line:
                    keywords_in_line = [k.strip() for k in line.split(',')]
                    enhanced_keywords.extend(keywords_in_line)

            # Clean and deduplicate
            cleaned_keywords = []
            for keyword in enhanced_keywords:
                keyword = keyword.strip('- *•').strip()
                if keyword and len(keyword) > 1 and keyword not in cleaned_keywords:
                    cleaned_keywords.append(keyword)

            # Combine with original keywords
            final_keywords = list(set(keywords + cleaned_keywords))

            logger.info(f"Enhanced keywords: {final_keywords[:10]}")
            return final_keywords[:10]  # Limit to 10 keywords

        except Exception as e:
            logger.warning(f"Keyword enhancement failed: {e}")
            return keywords  # Return original keywords if enhancement fails

    async def _evaluate_search_results(
        self,
        search_results: SearchResults,
        intent: str,
        keywords: List[str]
    ) -> Dict[str, Any]:
        """Evaluate search results and suggest improvements."""

        evaluation = {
            "confidence": 0.0,
            "should_retry": False,
            "suggested_keywords": [],
            "issues": []
        }

        # Check result count
        if search_results.total_count == 0:
            evaluation["confidence"] = 0.0
            evaluation["should_retry"] = True
            evaluation["issues"].append("검색 결과 없음")
            evaluation["suggested_keywords"] = await self._generate_alternative_keywords(keywords)

        elif search_results.total_count < 3:
            evaluation["confidence"] = 0.4
            evaluation["should_retry"] = True
            evaluation["issues"].append("검색 결과 부족")
            evaluation["suggested_keywords"] = await self._generate_alternative_keywords(keywords)

        else:
            # Evaluate relevance of results
            all_results = search_results.get_all_results()
            avg_relevance = sum(r.relevance_score for r in all_results) / len(all_results)

            if avg_relevance < 0.3:
                evaluation["confidence"] = 0.3
                evaluation["should_retry"] = True
                evaluation["issues"].append("관련성 낮음")

            elif avg_relevance < 0.6:
                evaluation["confidence"] = 0.6
                evaluation["should_retry"] = False

            else:
                evaluation["confidence"] = 0.9
                evaluation["should_retry"] = False

        return evaluation

    async def _generate_alternative_keywords(self, original_keywords: List[str]) -> List[str]:
        """Generate alternative keywords for retry search."""

        prompt = f"""다음 키워드로 법률 검색했지만 결과가 부족해서 다른 키워드가 필요해:

원래 키워드: {', '.join(original_keywords)}

대안 키워드를 제안해줘:
1. 더 일반적인 용어
2. 관련 법령의 다른 이름
3. 유사한 법적 개념
4. 상위 또는 하위 개념

5개 이내의 대안 키워드를 콤마로 구분해서 제공해줘."""

        try:
            messages = [
                {"role": "user", "content": prompt}
            ]

            response = await self._call_llm(messages, max_tokens=200)

            # Extract alternative keywords
            alt_keywords = []
            for part in response.split(','):
                keyword = part.strip().strip('- *•').strip()
                if keyword and len(keyword) > 1:
                    alt_keywords.append(keyword)

            return alt_keywords[:5]

        except Exception as e:
            logger.warning(f"Alternative keyword generation failed: {e}")
            return original_keywords

    async def _extract_emergency_keywords(self, user_input: str) -> List[str]:
        """Extract keywords directly from user input when none provided."""

        prompt = f"""다음 법률 질문에서 검색용 키워드를 추출해줘:

질문: {user_input}

법령명, 법률 용어, 핵심 개념을 중심으로 5개 이내의 키워드를 콤마로 구분해서 제공해줘."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self._call_llm(messages, max_tokens=150)

            keywords = []
            for part in response.split(','):
                keyword = part.strip().strip('- *•').strip()
                if keyword and len(keyword) > 1:
                    keywords.append(keyword)

            return keywords[:5]

        except Exception as e:
            logger.warning(f"Emergency keyword extraction failed: {e}")
            return ["법률", "법령"]  # Fallback keywords

    def _map_intent_to_enum(self, intent: str) -> QueryIntent:
        """Map intent string to QueryIntent enum."""

        intent_lower = intent.lower()

        if any(word in intent_lower for word in ["법령", "법률", "조문", "규정"]):
            return QueryIntent.LAW_SEARCH
        elif any(word in intent_lower for word in ["판례", "판결", "법원"]):
            return QueryIntent.PRECEDENT_SEARCH
        elif any(word in intent_lower for word in ["해석", "의미", "적용"]):
            return QueryIntent.LEGAL_INTERPRETATION
        elif any(word in intent_lower for word in ["절차", "방법", "신청"]):
            return QueryIntent.PROCEDURAL_GUIDANCE
        elif any(word in intent_lower for word in ["비교", "차이", "구별"]):
            return QueryIntent.COMPARATIVE_ANALYSIS
        else:
            return QueryIntent.GENERAL_INQUIRY