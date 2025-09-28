"""
Agent-based pipeline for legal chatbot.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional, Dict, Any

import openai
from loguru import logger

from ..agents.base_agent import ConversationContext, AgentAction
from ..agents.facilitator_agent import FacilitatorAgent
from ..agents.search_agent import SearchAgent
from ..agents.response_agent import ResponseAgent
from ..search.search_coordinator import SearchCoordinator
from ..models import LegalResponse, SearchSource, SourceType


class AgentPipeline:
    """
    Agent-based pipeline that orchestrates conversation flow through multiple agents.
    """

    def __init__(
        self,
        openai_api_key: str,
        openai_model: str = "gpt-4",
        temperature: float = 0.3,
        max_conversation_turns: int = 5
    ):
        """Initialize the agent pipeline."""

        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.search_coordinator = SearchCoordinator()
        self.max_conversation_turns = max_conversation_turns

        # Initialize agents
        agent_kwargs = {
            "openai_client": self.openai_client,
            "model": openai_model,
            "temperature": temperature
        }

        self.facilitator = FacilitatorAgent(**agent_kwargs)
        self.search_agent = SearchAgent(
            search_coordinator=self.search_coordinator,
            **agent_kwargs
        )
        self.response_agent = ResponseAgent(**agent_kwargs)

        # Active conversations
        self.conversations: Dict[str, ConversationContext] = {}

        logger.info("Agent pipeline initialized")

    async def close(self):
        """Close all connections and cleanup resources."""
        await self.search_coordinator.close()
        await self.openai_client.close()
        logger.info("Agent pipeline closed")

    async def process_message(
        self,
        user_message: str,
        conversation_id: Optional[str] = None
    ) -> LegalResponse:
        """
        Process a user message through the agent pipeline.

        Args:
            user_message: The user's message
            conversation_id: Optional conversation ID for context

        Returns:
            LegalResponse with the final answer
        """

        start_time = time.time()

        # Get or create conversation context
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        context = self._get_or_create_context(conversation_id)

        logger.info(f"Processing message in conversation {conversation_id}: {user_message[:50]}...")

        try:
            # Add user message to context
            context.user_messages.append(user_message)

            # Check conversation limits
            if len(context.user_messages) > self.max_conversation_turns:
                return self._generate_limit_exceeded_response(conversation_id)

            # Start with facilitator agent
            current_agent = self.facilitator
            agent_response = await current_agent.process(user_message, context)

            # Add response to context
            context.agent_responses.append(agent_response)

            # Process agent pipeline
            final_response = await self._process_agent_pipeline(
                agent_response, context, user_message
            )

            # Update conversation context
            if agent_response.intent:
                context.extracted_intent = agent_response.intent
            if agent_response.keywords:
                context.extracted_keywords.extend(agent_response.keywords)
                # Remove duplicates while preserving order
                seen = set()
                context.extracted_keywords = [
                    x for x in context.extracted_keywords
                    if not (x in seen or seen.add(x))
                ]

            # Store conversation
            self.conversations[conversation_id] = context

            # Set processing time
            final_response.processing_time = time.time() - start_time

            logger.info(f"Message processed in {final_response.processing_time:.2f}s")
            return final_response

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._generate_error_response(user_message, str(e))

    async def _process_agent_pipeline(
        self,
        initial_response,
        context: ConversationContext,
        user_message: str
    ) -> LegalResponse:
        """Process the message through the agent pipeline."""

        current_response = initial_response

        # Handle facilitator response
        if current_response.action == AgentAction.REQUEST_CLARIFICATION:
            # Return clarification request to user
            return LegalResponse(
                answer=current_response.message,
                sources=[],
                confidence=current_response.confidence,
                related_keywords=current_response.keywords,
                follow_up_questions=current_response.clarification_options,
                query=None
            )

        elif current_response.action == AgentAction.CONTINUE_CONVERSATION:
            # Continue conversation with facilitator
            return LegalResponse(
                answer=current_response.message,
                sources=[],
                confidence=current_response.confidence,
                related_keywords=current_response.keywords,
                follow_up_questions=[
                    "더 구체적으로 설명해 주시겠어요?",
                    "어떤 상황에서 이런 문제가 발생했나요?",
                    "관련된 법령이나 규정이 있다면 알려주세요."
                ],
                query=None
            )

        elif current_response.action == AgentAction.FORWARD_TO_SEARCH:
            # Move to search agent
            logger.info("Forwarding to search agent")
            search_response = await self.search_agent.process(user_message, context)
            context.agent_responses.append(search_response)

            if search_response.action == AgentAction.FORWARD_TO_RESPONSE:
                # Move to response agent
                logger.info("Forwarding to response agent")
                response_agent_response = await self.response_agent.process(user_message, context)
                context.agent_responses.append(response_agent_response)

                return self._convert_to_legal_response(response_agent_response, context)

            else:
                # Search failed, return search agent message
                return LegalResponse(
                    answer=search_response.message,
                    sources=[],
                    confidence=search_response.confidence,
                    related_keywords=search_response.keywords,
                    follow_up_questions=[
                        "다른 키워드로 다시 검색해 보시겠습니까?",
                        "더 구체적인 법령명이나 조문을 알고 계신가요?"
                    ],
                    query=None
                )

        else:
            # Unknown action, return generic response
            return LegalResponse(
                answer="죄송합니다. 질문을 처리하는 중 예상치 못한 상황이 발생했습니다. 다시 시도해 주세요.",
                sources=[],
                confidence=0.0,
                related_keywords=[],
                follow_up_questions=[],
                query=None
            )

    def _convert_to_legal_response(
        self,
        agent_response,
        context: ConversationContext
    ) -> LegalResponse:
        """Convert agent response to LegalResponse."""

        # Extract sources from metadata
        sources = agent_response.metadata.get("sources", [])

        # Extract follow-up questions
        follow_ups = agent_response.metadata.get("follow_up_questions", [])

        return LegalResponse(
            answer=agent_response.message,
            sources=sources,
            confidence=agent_response.confidence,
            related_keywords=agent_response.keywords,
            follow_up_questions=follow_ups,
            query=None  # TODO: Create LegalQuery object if needed
        )

    def _get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Get existing conversation context or create new one."""

        if conversation_id in self.conversations:
            return self.conversations[conversation_id]

        return ConversationContext(conversation_id=conversation_id)

    def get_conversation_status(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a conversation."""

        if conversation_id not in self.conversations:
            return None

        context = self.conversations[conversation_id]

        return {
            "conversation_id": conversation_id,
            "turn_count": len(context.user_messages),
            "extracted_intent": context.extracted_intent,
            "extracted_keywords": context.extracted_keywords,
            "last_agent_action": context.agent_responses[-1].action.value if context.agent_responses else None,
            "confidence": context.agent_responses[-1].confidence if context.agent_responses else 0.0
        }

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation context."""

        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get overall pipeline status."""

        search_status = await self.search_coordinator.get_search_status()

        return {
            "pipeline": {
                "status": "operational",
                "active_conversations": len(self.conversations),
                "max_conversation_turns": self.max_conversation_turns
            },
            "agents": {
                "facilitator": {"status": "operational"},
                "search": {"status": "operational"},
                "response": {"status": "operational"}
            },
            "search": search_status
        }

    def _generate_limit_exceeded_response(self, conversation_id: str) -> LegalResponse:
        """Generate response when conversation limit is exceeded."""

        return LegalResponse(
            answer=f"""이 대화는 최대 턴 수({self.max_conversation_turns})에 도달했습니다.

새로운 질문이 있으시면 새 대화를 시작해 주세요.

이전 대화에서 충분한 정보를 얻지 못하셨다면:
- 더 구체적인 질문으로 새 대화를 시작하세요
- 관련 법령명이나 조문을 포함해서 질문해 보세요
- 필요시 전문가와 직접 상담하시기 바랍니다

대화 ID: {conversation_id}""",
            sources=[],
            confidence=0.0,
            related_keywords=[],
            follow_up_questions=[],
            query=None
        )

    def _generate_error_response(self, user_message: str, error: str) -> LegalResponse:
        """Generate error response."""

        return LegalResponse(
            answer=f"""죄송합니다. 메시지 처리 중 오류가 발생했습니다.

오류 내용: {error}

다음을 시도해 보세요:
- 질문을 다시 입력해 보세요
- 더 간단한 형태로 질문해 보세요
- 잠시 후 다시 시도해 보세요

지속적인 문제가 발생하면 관리자에게 문의하시기 바랍니다.""",
            sources=[],
            confidence=0.0,
            related_keywords=[],
            follow_up_questions=[
                "다시 시도해 보시겠습니까?",
                "다른 방식으로 질문해 보시겠습니까?"
            ],
            query=None
        )


class ConversationManager:
    """Manages multiple conversations and provides conversation utilities."""

    def __init__(self, pipeline: AgentPipeline):
        self.pipeline = pipeline

    async def start_conversation(self, initial_message: str) -> tuple[str, LegalResponse]:
        """Start a new conversation."""

        conversation_id = str(uuid.uuid4())
        response = await self.pipeline.process_message(initial_message, conversation_id)

        return conversation_id, response

    async def continue_conversation(
        self,
        conversation_id: str,
        message: str
    ) -> LegalResponse:
        """Continue an existing conversation."""

        return await self.pipeline.process_message(message, conversation_id)

    def get_conversation_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of the conversation."""

        status = self.pipeline.get_conversation_status(conversation_id)
        if not status:
            return None

        if conversation_id not in self.pipeline.conversations:
            return None

        context = self.pipeline.conversations[conversation_id]

        return {
            **status,
            "messages": [
                {"role": "user", "content": msg}
                for msg in context.user_messages
            ],
            "agent_responses": [
                {
                    "action": resp.action.value,
                    "message": resp.message,
                    "confidence": resp.confidence
                }
                for resp in context.agent_responses
            ]
        }