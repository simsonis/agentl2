"""
Facilitator Agent - Handles initial user query processing and intent extraction.
"""

from __future__ import annotations

from typing import List
from loguru import logger

from .base_agent import BaseAgent, AgentResponse, AgentAction, ConversationContext


class FacilitatorAgent(BaseAgent):
    """
    Facilitator Agent that handles user query processing and intent extraction.
    Acts as a 20-year experienced legal consultant from a major law firm.
    """

    def __init__(self, **kwargs):
        super().__init__(name="Facilitator", **kwargs)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the facilitator agent."""
        return """너는 법률 LLM 시스템의 맨 처음 레이어에 해당하는 사용자 질의 전달자 에이전트야.

너는 20년차 대형로펌의 법률 상담가야.

사용자의 질의를 받으면 너와 사용자의 대화 내용을 바탕으로
1. 사용자의 의도가 무엇인지,
2. 사용자의 의도에 맞는 답을 찾기 위해 추출 혹은 생성할 수 있는 판례, 법령 DB 검색용 키워드는 무엇인지
깊게 생각하고 말해줘.

**중요** 법률 전문가의 관점에서 사용자의 질문이 의도와 키워드를 파악하기에 충분치 않다고 판단하면 충분한 의도를 파악하기 위한 너의 질문을 3번(option) 답변으로 생성해서 사용자로 하여금 추가 설명을 하도록 유도해.

너의 답변 포맷은 다음과 같아:
1. intent = {사용자의 구체적인 법률 상담 의도}
2. search keywords = {키워드1, 키워드2, 키워드3, ...}
3(option). = {추가 질문 1}
3(option). = {추가 질문 2}
3(option). = {추가 질문 3}

답변 가이드라인:
- intent는 구체적이고 명확하게 표현해야 함 (예: "개인정보 수집 동의 절차 문의", "금융상품 불완전판매 피해 구제 방법 문의")
- search keywords는 법령명, 법조문, 판례 검색에 효과적인 핵심 용어들로 구성
- 추가 질문은 사용자의 구체적인 상황, 적용 법령, 시급성 등을 파악하기 위한 실무적 질문
- 질문이 충분히 구체적이면 3(option) 없이 1, 2번만 답변

예시:
사용자: "개인정보 처리 관련해서 궁금한 게 있어요"
→ 너무 모호하므로 추가 질문 필요

사용자: "우리 회사에서 고객 개인정보를 가명처리해서 마케팅에 활용하려고 하는데 개인정보보호법상 문제가 없는지 확인하고 싶습니다"
→ 충분히 구체적이므로 바로 intent와 keywords 제공"""

    async def process(
        self,
        user_input: str,
        context: ConversationContext
    ) -> AgentResponse:
        """Process user input and extract intent/keywords or request clarification."""

        logger.info(f"Facilitator processing: {user_input[:50]}...")

        try:
            # Build conversation history
            messages = self._build_conversation_history(context)
            messages.append({"role": "user", "content": user_input})

            # Get LLM response
            llm_response = await self._call_llm(messages, max_tokens=800)

            # Parse structured response
            parsed = self._parse_structured_response(llm_response)

            # Determine action based on parsed response
            if parsed["clarification_options"]:
                # Need clarification
                action = AgentAction.REQUEST_CLARIFICATION
                message = self._format_clarification_message(parsed["clarification_options"])

            elif parsed["intent"] and parsed["keywords"]:
                # Ready to search
                action = AgentAction.FORWARD_TO_SEARCH
                message = f"의도를 파악했습니다. 관련 정보를 검색하겠습니다."

            else:
                # Continue conversation for more info
                action = AgentAction.CONTINUE_CONVERSATION
                message = "조금 더 구체적인 상황을 알려주시면 더 정확한 도움을 드릴 수 있습니다."

            return AgentResponse(
                action=action,
                message=message,
                intent=parsed["intent"],
                keywords=parsed["keywords"],
                clarification_options=parsed["clarification_options"],
                confidence=parsed["confidence"],
                metadata={
                    "llm_response": llm_response,
                    "conversation_turns": len(context.user_messages) + 1
                }
            )

        except Exception as e:
            logger.error(f"Error in facilitator agent: {e}")
            return AgentResponse(
                action=AgentAction.CONTINUE_CONVERSATION,
                message="죄송합니다. 질문을 처리하는 중 오류가 발생했습니다. 다시 한 번 말씀해 주시겠어요?",
                confidence=0.0
            )

    def _format_clarification_message(self, options: List[str]) -> str:
        """Format clarification options into a user-friendly message."""
        if not options:
            return "조금 더 자세히 말씀해 주시겠어요?"

        message = "더 정확한 답변을 위해 추가 정보가 필요합니다:\n\n"

        for i, option in enumerate(options, 1):
            message += f"{i}. {option.strip()}\n"

        message += "\n위 질문들에 대해 답변해 주시면 더 구체적인 법률 조언을 제공할 수 있습니다."

        return message

    async def validate_completeness(
        self,
        intent: str,
        keywords: List[str],
        context: ConversationContext
    ) -> bool:
        """Validate if intent and keywords are sufficient for search."""

        # Basic validation rules
        if not intent or len(intent.strip()) < 10:
            return False

        if not keywords or len(keywords) < 2:
            return False

        # Check for legal specificity
        legal_indicators = [
            "법", "조문", "판례", "규정", "시행령", "시행규칙",
            "개인정보", "금융", "소비자", "계약", "손해배상",
            "민법", "상법", "형법", "행정법"
        ]

        combined_text = intent + " " + " ".join(keywords)
        has_legal_context = any(indicator in combined_text for indicator in legal_indicators)

        return has_legal_context

    def extract_conversation_summary(self, context: ConversationContext) -> str:
        """Extract a summary of the conversation for handoff to other agents."""

        if not context.user_messages:
            return "새로운 대화 시작"

        summary_parts = []

        # Add conversation flow
        summary_parts.append(f"대화 턴 수: {len(context.user_messages)}")

        # Add latest intent if available
        if context.extracted_intent:
            summary_parts.append(f"파악된 의도: {context.extracted_intent}")

        # Add keywords if available
        if context.extracted_keywords:
            summary_parts.append(f"추출된 키워드: {', '.join(context.extracted_keywords[:5])}")

        # Add key conversation points
        if len(context.user_messages) > 1:
            summary_parts.append("주요 대화 내용:")
            for i, msg in enumerate(context.user_messages[-3:], 1):  # Last 3 messages
                summary_parts.append(f"  {i}. {msg[:100]}...")

        return "\n".join(summary_parts)