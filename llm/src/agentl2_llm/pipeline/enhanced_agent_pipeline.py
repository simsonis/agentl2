"""
Enhanced Agent-based pipeline with comprehensive legal analysis.
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
from ..agents.analyst_agent import AnalystAgent
from ..agents.response_agent import ResponseAgent
from ..agents.citation_agent import CitationAgent
from ..agents.validator_agent import ValidatorAgent
from ..search.search_coordinator import SearchCoordinator
from ..models import LegalResponse, SearchSource


class EnhancedAgentPipeline:
    """
    확장된 에이전트 파이프라인 - 6개 전문 에이전트 협업
    전달자 → 검색 → 분석가 → 응답 → 인용 → 검증자
    """

    def __init__(
        self,
        openai_api_key: str,
        openai_model: str = "gpt-4",
        temperature: float = 0.3,
        max_conversation_turns: int = 5
    ):
        """Initialize the enhanced agent pipeline."""

        self.openai_client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.search_coordinator = SearchCoordinator()
        self.max_conversation_turns = max_conversation_turns

        # Initialize agents
        agent_kwargs = {
            "openai_client": self.openai_client,
            "model": openai_model,
            "temperature": temperature
        }

        # 기존 에이전트들
        self.facilitator = FacilitatorAgent(**agent_kwargs)
        self.search_agent = SearchAgent(
            search_coordinator=self.search_coordinator,
            **agent_kwargs
        )
        self.response_agent = ResponseAgent(**agent_kwargs)

        # 새로운 에이전트들
        self.analyst = AnalystAgent(**agent_kwargs)
        self.citation_agent = CitationAgent(**agent_kwargs)
        self.validator = ValidatorAgent(**agent_kwargs)

        # Active conversations
        self.conversations: Dict[str, ConversationContext] = {}

        logger.info("Enhanced agent pipeline initialized with 6 specialized agents")

    async def close(self):
        """Close all connections and cleanup resources."""
        await self.search_coordinator.close()
        await self.openai_client.close()
        logger.info("Enhanced agent pipeline closed")

    async def process_message(
        self,
        user_message: str,
        conversation_id: Optional[str] = None
    ) -> LegalResponse:
        """
        Process a user message through the enhanced 6-agent pipeline.

        Flow: 전달자 → 검색 → 분석가 → 응답 → 인용 → 검증자
        """

        start_time = time.time()

        # Get or create conversation context
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        context = self._get_or_create_context(conversation_id)

        logger.info(f"Processing message through enhanced pipeline: {user_message[:50]}...")

        try:
            # Add user message to context
            context.user_messages.append(user_message)

            # Check conversation limits
            if len(context.user_messages) > self.max_conversation_turns:
                return self._generate_limit_exceeded_response(conversation_id)

            # Execute enhanced agent pipeline
            final_response = await self._execute_enhanced_pipeline(
                user_message, context
            )

            # Store conversation
            self.conversations[conversation_id] = context

            # Set processing time
            final_response.processing_time = time.time() - start_time

            logger.info(f"Enhanced pipeline completed in {final_response.processing_time:.2f}s")
            return final_response

        except Exception as e:
            logger.error(f"Error in enhanced pipeline: {e}")
            return self._generate_error_response(user_message, str(e))

    async def _execute_enhanced_pipeline(
        self,
        user_message: str,
        context: ConversationContext
    ) -> LegalResponse:
        """Execute the complete 6-agent pipeline."""

        # Step 1: 전달자 Agent - 의도 파악 및 키워드 추출
        logger.info("Step 1: Facilitator Agent processing")
        facilitator_response = await self.facilitator.process(user_message, context)
        context.agent_responses.append(facilitator_response)

        # Update context with extracted information
        if facilitator_response.intent:
            context.extracted_intent = facilitator_response.intent
        if facilitator_response.keywords:
            context.extracted_keywords.extend(facilitator_response.keywords)

        # Early exit if clarification needed
        if facilitator_response.action == AgentAction.REQUEST_CLARIFICATION:
            return LegalResponse(
                answer=facilitator_response.message,
                sources=[],
                confidence=facilitator_response.confidence,
                related_keywords=facilitator_response.keywords,
                follow_up_questions=facilitator_response.clarification_options,
                query=None
            )

        # Early exit if conversation continues
        if facilitator_response.action == AgentAction.CONTINUE_CONVERSATION:
            return LegalResponse(
                answer=facilitator_response.message,
                sources=[],
                confidence=facilitator_response.confidence,
                related_keywords=facilitator_response.keywords,
                follow_up_questions=[
                    "더 구체적으로 설명해 주시겠어요?",
                    "어떤 상황에서 이런 문제가 발생했나요?"
                ],
                query=None
            )

        # Step 2: 검색 Agent - 다중 라운드 검색
        logger.info("Step 2: Search Agent processing")
        search_response = await self.search_agent.process(user_message, context)
        context.agent_responses.append(search_response)

        # Step 3: 분석가 Agent - 법적 분석
        logger.info("Step 3: Analyst Agent processing")
        analysis_response = await self.analyst.process(user_message, context)
        context.agent_responses.append(analysis_response)

        # Step 4: 응답 Agent - 답변 내용 생성
        logger.info("Step 4: Response Agent processing")
        response_agent_response = await self.response_agent.process(user_message, context)
        context.agent_responses.append(response_agent_response)

        # Step 5: 인용 Agent - 참조를 실제 인용으로 변환
        logger.info("Step 5: Citation Agent processing")
        citation_response = await self.citation_agent.process(user_message, context)
        context.agent_responses.append(citation_response)

        # Step 6: 검증자 Agent - 종합 검증 및 최종 답변 구성
        logger.info("Step 6: Validator Agent processing")
        validation_response = await self.validator.process(user_message, context)
        context.agent_responses.append(validation_response)

        # Extract final response information
        final_answer = validation_response.message
        sources = self._extract_sources(context)
        confidence = validation_response.confidence
        related_keywords = self._extract_related_keywords(context)
        follow_ups = self._extract_follow_up_questions(context)

        return LegalResponse(
            answer=final_answer,
            sources=sources,
            confidence=confidence,
            related_keywords=related_keywords,
            follow_up_questions=follow_ups,
            query=None
        )

    def _extract_sources(self, context: ConversationContext) -> list[SearchSource]:
        """Extract sources from context."""
        sources = []

        for response in context.agent_responses:
            if response.metadata:
                # Citation agent sources
                if "citation_package" in response.metadata:
                    citation_package = response.metadata["citation_package"]
                    for citation in citation_package.citations:
                        source = SearchSource(
                            url=citation.source_url,
                            title=citation.title,
                            source_type=citation.citation_type,
                            confidence=0.8,
                            excerpt=citation.content[:150]
                        )
                        sources.append(source)

                # Search results sources
                elif "search_results" in response.metadata:
                    search_results = response.metadata["search_results"]
                    for result in search_results.get_all_results()[:5]:  # Top 5
                        sources.append(result.source)

        return sources[:10]  # Limit to 10 sources

    def _extract_related_keywords(self, context: ConversationContext) -> list[str]:
        """Extract related keywords from context."""
        all_keywords = []

        for response in context.agent_responses:
            if response.keywords:
                all_keywords.extend(response.keywords)

        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in all_keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)

        return unique_keywords[:10]  # Limit to 10

    def _extract_follow_up_questions(self, context: ConversationContext) -> list[str]:
        """Extract follow-up questions from context."""
        follow_ups = []

        # Look for follow-up questions in agent responses
        for response in context.agent_responses:
            if response.clarification_options:
                follow_ups.extend(response.clarification_options)

        # Default follow-ups based on intent
        if context.extracted_intent:
            intent = context.extracted_intent.lower()
            if "법령" in intent:
                follow_ups.extend([
                    "이 법령의 시행령이나 시행규칙도 확인하고 싶으신가요?",
                    "관련 판례도 함께 찾아보시겠습니까?"
                ])
            elif "판례" in intent:
                follow_ups.extend([
                    "비슷한 사안의 다른 판례도 확인하시겠습니까?",
                    "최신 법령 개정사항도 함께 검토하시겠습니까?"
                ])

        return follow_ups[:4]  # Limit to 4

    def _get_or_create_context(self, conversation_id: str) -> ConversationContext:
        """Get existing conversation context or create new one."""
        if conversation_id in self.conversations:
            return self.conversations[conversation_id]
        return ConversationContext(conversation_id=conversation_id)

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get overall enhanced pipeline status."""
        search_status = await self.search_coordinator.get_search_status()

        return {
            "pipeline": {
                "type": "enhanced_6_agent_pipeline",
                "status": "operational",
                "active_conversations": len(self.conversations),
                "max_conversation_turns": self.max_conversation_turns
            },
            "agents": {
                "facilitator": {"status": "operational", "role": "의도파악/키워드추출"},
                "search": {"status": "operational", "role": "다중라운드검색"},
                "analyst": {"status": "operational", "role": "법적분석/쟁점식별"},
                "response": {"status": "operational", "role": "답변내용생성"},
                "citation": {"status": "operational", "role": "인용/출처관리"},
                "validator": {"status": "operational", "role": "종합검증/품질관리"}
            },
            "search": search_status
        }

    def get_conversation_status(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a conversation."""
        if conversation_id not in self.conversations:
            return None

        context = self.conversations[conversation_id]

        # Pipeline stage tracking
        stages_completed = []
        for response in context.agent_responses:
            agent_name = getattr(response, 'agent_name', 'Unknown')
            stages_completed.append(agent_name)

        return {
            "conversation_id": conversation_id,
            "turn_count": len(context.user_messages),
            "extracted_intent": context.extracted_intent,
            "extracted_keywords": context.extracted_keywords,
            "pipeline_stages_completed": stages_completed,
            "last_agent_action": context.agent_responses[-1].action.value if context.agent_responses else None,
            "final_confidence": context.agent_responses[-1].confidence if context.agent_responses else 0.0
        }

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation context."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False

    def _generate_limit_exceeded_response(self, conversation_id: str) -> LegalResponse:
        """Generate response when conversation limit is exceeded."""
        return LegalResponse(
            answer=f"""이 대화는 최대 턴 수({self.max_conversation_turns})에 도달했습니다.

새로운 질문이 있으시면 새 대화를 시작해 주세요.

이전 대화에서 충분한 정보를 얻지 못하셨다면:
- 더 구체적인 질문으로 새 대화를 시작하세요
- 관련 법령명이나 조문을 포함해서 질문해 보세요
- 필요시 전문가와 직접 상담하시기 바랍니다""",
            sources=[],
            confidence=0.0,
            related_keywords=[],
            follow_up_questions=[],
            query=None
        )

    def _generate_error_response(self, user_message: str, error: str) -> LegalResponse:
        """Generate error response."""
        return LegalResponse(
            answer=f"""죄송합니다. 고도화된 법률 분석 과정에서 오류가 발생했습니다.

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


# Convenience wrapper for conversation management
class EnhancedConversationManager:
    """Enhanced conversation manager for the 6-agent pipeline."""

    def __init__(self, pipeline: EnhancedAgentPipeline):
        self.pipeline = pipeline

    async def start_conversation(self, initial_message: str) -> tuple[str, LegalResponse]:
        """Start a new conversation with enhanced analysis."""
        conversation_id = str(uuid.uuid4())
        response = await self.pipeline.process_message(initial_message, conversation_id)
        return conversation_id, response

    async def continue_conversation(
        self,
        conversation_id: str,
        message: str
    ) -> LegalResponse:
        """Continue an existing conversation with enhanced analysis."""
        return await self.pipeline.process_message(message, conversation_id)

    def get_conversation_analysis(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed conversation analysis."""
        status = self.pipeline.get_conversation_status(conversation_id)
        if not status:
            return None

        if conversation_id not in self.pipeline.conversations:
            return None

        context = self.pipeline.conversations[conversation_id]

        # Extract analysis results from agent responses
        analysis_data = {
            "legal_analysis": None,
            "search_quality": None,
            "citation_quality": None,
            "validation_results": None
        }

        for response in context.agent_responses:
            metadata = response.metadata or {}

            if "analysis_result" in metadata:
                analysis_data["legal_analysis"] = metadata["analysis_result"]

            if "search_results" in metadata:
                search_results = metadata["search_results"]
                analysis_data["search_quality"] = {
                    "total_results": search_results.total_count,
                    "search_duration": search_results.search_duration
                }

            if "citation_package" in metadata:
                citation_package = metadata["citation_package"]
                analysis_data["citation_quality"] = {
                    "citations_count": len(citation_package.citations),
                    "quality_score": citation_package.quality_score
                }

            if "validation_result" in metadata:
                analysis_data["validation_results"] = metadata["validation_result"]

        return {
            **status,
            "detailed_analysis": analysis_data,
            "pipeline_performance": {
                "total_agents": 6,
                "agents_executed": len(status.get("pipeline_stages_completed", [])),
                "completion_rate": len(status.get("pipeline_stages_completed", [])) / 6
            }
        }