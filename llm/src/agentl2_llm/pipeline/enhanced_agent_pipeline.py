"""
Enhanced Agent-based pipeline with comprehensive legal analysis.
"""

from __future__ import annotations

import time
import uuid
import inspect
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable, List

import openai
from pydantic import BaseModel
from loguru import logger

from ..agents.base_agent import ConversationContext, AgentAction, AgentResponse
from ..agents.facilitator_agent import FacilitatorAgent
from ..agents.search_agent import SearchAgent
from ..agents.analyst_agent import AnalystAgent
from ..agents.response_agent import ResponseAgent
from ..agents.citation_agent import CitationAgent
from ..agents.validator_agent import ValidatorAgent
from ..search.search_coordinator import SearchCoordinator
from ..models import LegalResponse, SearchSource, SearchResults, SourceType


class EnhancedAgentPipeline:
    """
    ???????????????- 6??�?????????
    ??????검????분석가 ????????????검증자
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

        # 기존 ??????
        self.facilitator = FacilitatorAgent(**agent_kwargs)
        self.search_agent = SearchAgent(
            search_coordinator=self.search_coordinator,
            **agent_kwargs
        )
        self.response_agent = ResponseAgent(**agent_kwargs)

        # ?�????????
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
        conversation_id: Optional[str] = None,
        event_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
    ) -> LegalResponse:
        """
        Process a user message through the enhanced 6-agent pipeline.

        Flow: ????��???�분?��?????????증자
        """

        start_time = time.time()

        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        context = self._get_or_create_context(conversation_id)

        logger.info(f"Processing message through enhanced pipeline: {user_message[:50]}...")

        try:
            context.user_messages.append(user_message)

            if len(context.user_messages) > self.max_conversation_turns:
                limit_response = self._generate_limit_exceeded_response(conversation_id)
                await self._emit_event(
                    event_handler,
                    "pipeline",
                    {
                        "stage": "limit_exceeded",
                        "response": self._serialize_legal_response(limit_response),
                        "context": self._summarize_context(context)
                    }
                )
                return limit_response

            final_response = await self._execute_enhanced_pipeline(
                user_message,
                context,
                event_handler=event_handler
            )

            self.conversations[conversation_id] = context

            final_response.processing_time = time.time() - start_time

            await self._emit_event(
                event_handler,
                "pipeline",
                {
                    "stage": "completed",
                    "response": self._serialize_legal_response(final_response),
                    "context": self._summarize_context(context)
                }
            )

            logger.info(f"Enhanced pipeline completed in {final_response.processing_time:.2f}s")
            return final_response

        except Exception as e:
            logger.error(f"Error in enhanced pipeline: {e}")
            error_response = self._generate_error_response(user_message, str(e))
            await self._emit_event(
                event_handler,
                "pipeline",
                {
                    "stage": "error",
                    "error": str(e),
                    "response": self._serialize_legal_response(error_response),
                    "context": self._summarize_context(context)
                }
            )
            return error_response

    async def _execute_enhanced_pipeline(
        self,
        user_message: str,
        context: ConversationContext,
        event_handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
    ) -> LegalResponse:
        """Execute the complete 6-agent pipeline."""

        # Step 1: ????Agent - ???????????추출
        logger.info("Step 1: Facilitator Agent processing")
        facilitator_input = self._build_agent_input(user_message, context)
        facilitator_response = await self.facilitator.process(user_message, context)
        context.agent_responses.append(facilitator_response)

        if facilitator_response.intent:
            context.extracted_intent = facilitator_response.intent
        if facilitator_response.keywords:
            context.extracted_keywords.extend(facilitator_response.keywords)
            context.extracted_keywords = self._deduplicate_sequence(context.extracted_keywords)

        await self._emit_event(
            event_handler,
            "facilitator",
            {
                "input": facilitator_input,
                "output": self._summarize_agent_response(facilitator_response),
                "context": self._summarize_context(context)
            }
        )

        if facilitator_response.action == AgentAction.REQUEST_CLARIFICATION:
            clarification_response = LegalResponse(
                answer=facilitator_response.message,
                sources=[],
                confidence=facilitator_response.confidence,
                related_keywords=facilitator_response.keywords,
                follow_up_questions=facilitator_response.clarification_options,
                query=None
            )
            await self._emit_event(
                event_handler,
                "pipeline",
                {
                    "stage": "clarification_needed",
                    "response": self._serialize_legal_response(clarification_response),
                    "context": self._summarize_context(context)
                }
            )
            return clarification_response

        if facilitator_response.action == AgentAction.CONTINUE_CONVERSATION:
            continuation_response = LegalResponse(
                answer=facilitator_response.message,
                sources=[],
                confidence=facilitator_response.confidence,
                related_keywords=facilitator_response.keywords,
                follow_up_questions=[
                    "조금 ??구체?????????�주?�겠???",
                    "????�??????문제가 발생????"
                ],
                query=None
            )
            await self._emit_event(
                event_handler,
                "pipeline",
                {
                    "stage": "additional_context_required",
                    "response": self._serialize_legal_response(continuation_response),
                    "context": self._summarize_context(context)
                }
            )
            return continuation_response

        # Step 2: 검??Agent - 중간 검???보완 검??
        logger.info("Step 2: Search Agent processing")
        search_input = self._build_agent_input(user_message, context)
        search_response = await self.search_agent.process(user_message, context)
        context.agent_responses.append(search_response)

        await self._emit_event(
            event_handler,
            "search",
            {
                "input": search_input,
                "output": self._summarize_agent_response(search_response),
                "context": self._summarize_context(context)
            }
        )

        # Step 3: 분석가 Agent - 법적 분석
        logger.info("Step 3: Analyst Agent processing")
        analysis_input = self._build_agent_input(user_message, context)
        analysis_response = await self.analyst.process(user_message, context)
        context.agent_responses.append(analysis_response)

        await self._emit_event(
            event_handler,
            "analyst",
            {
                "input": analysis_input,
                "output": self._summarize_agent_response(analysis_response),
                "context": self._summarize_context(context)
            }
        )

        # Step 4: ???Agent - ?? ???
        logger.info("Step 4: Response Agent processing")
        response_input = self._build_agent_input(user_message, context)
        response_agent_response = await self.response_agent.process(user_message, context)
        context.agent_responses.append(response_agent_response)

        await self._emit_event(
            event_handler,
            "response",
            {
                "input": response_input,
                "output": self._summarize_agent_response(response_agent_response),
                "context": self._summarize_context(context)
            }
        )

        # Step 5: ???Agent - 참조 ?�?
        logger.info("Step 5: Citation Agent processing")
        citation_input = self._build_agent_input(user_message, context)
        citation_response = await self.citation_agent.process(user_message, context)
        context.agent_responses.append(citation_response)

        await self._emit_event(
            event_handler,
            "citation",
            {
                "input": citation_input,
                "output": self._summarize_agent_response(citation_response),
                "context": self._summarize_context(context)
            }
        )

        # Step 6: 검증자 Agent - 종합 검?
        logger.info("Step 6: Validator Agent processing")
        validator_input = self._build_agent_input(user_message, context)
        validation_response = await self.validator.process(user_message, context)
        context.agent_responses.append(validation_response)

        await self._emit_event(
            event_handler,
            "validator",
            {
                "input": validator_input,
                "output": self._summarize_agent_response(validation_response),
                "context": self._summarize_context(context)
            }
        )

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

    async def _emit_event(
        self,
        handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]],
        agent: str,
        payload: Dict[str, Any]
    ) -> None:
        if not handler:
            return

        event_payload = dict(payload) if isinstance(payload, dict) else {"value": payload}
        event_payload.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")

        try:
            result = handler(agent, event_payload)
            if inspect.isawaitable(result):
                await result
        except Exception as exc:
            logger.warning(f"Event handler error for {agent}: {exc}")

    def _build_agent_input(self, user_message: str, context: ConversationContext) -> Dict[str, Any]:
        return {
            "user_message": user_message,
            "intent": context.extracted_intent,
            "keywords": context.extracted_keywords[-10:],
            "context": self._summarize_context(context)
        }

    def _summarize_context(self, context: ConversationContext) -> Dict[str, Any]:
        return {
            "conversation_id": context.conversation_id,
            "turn_count": len(context.user_messages),
            "recent_user_messages": context.user_messages[-3:],
            "recent_agent_actions": [
                response.action.value for response in context.agent_responses[-3:]
            ],
            "extracted_intent": context.extracted_intent,
            "extracted_keywords": context.extracted_keywords[-10:]
        }

    def _summarize_agent_response(self, response: AgentResponse) -> Dict[str, Any]:
        summary = {
            "action": response.action.value,
            "message": response.message,
            "intent": response.intent,
            "keywords": response.keywords,
            "confidence": response.confidence,
        }
        if response.clarification_options:
            summary["clarification_options"] = response.clarification_options
        if response.metadata:
            summary["metadata"] = self._summarize_metadata(response.metadata)
        return summary

    def _summarize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        return {key: self._serialize_value(value) for key, value in metadata.items()}

    def _serialize_value(self, value: Any):
        if isinstance(value, SearchResults):
            return self._serialize_search_results(value)
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if is_dataclass(value):
            return asdict(value)
        if isinstance(value, dict):
            return {key: self._serialize_value(val) for key, val in list(value.items())[:10]}
        if isinstance(value, (list, tuple)):
            return [self._serialize_value(item) for item in list(value)[:5]]
        if hasattr(value, "__dict__"):
            return {key: self._serialize_value(val) for key, val in list(vars(value).items())[:10]}
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    def _serialize_search_results(self, results: SearchResults) -> Dict[str, Any]:
        return {
            "total_count": results.total_count,
            "internal_count": len(results.internal_results),
            "external_count": len(results.external_results),
            "search_duration": results.search_duration,
            "top_results": [
                {
                    "title": item.title,
                    "url": item.source.url,
                    "source_type": item.source.source_type.value
                    if hasattr(item.source.source_type, "value")
                    else str(item.source.source_type),
                    "relevance_score": item.relevance_score,
                }
                for item in results.get_all_results()[:3]
            ],
        }

    def _serialize_legal_response(self, response: LegalResponse) -> Dict[str, Any]:
        return {
            "answer": response.answer,
            "sources": [
                {
                    "title": source.title,
                    "url": source.url,
                    "source_type": source.source_type.value
                    if hasattr(source.source_type, "value")
                    else str(source.source_type),
                    "confidence": source.confidence,
                    "excerpt": source.excerpt,
                    "date": source.date.isoformat() if source.date else None,
                }
                for source in response.sources[:5]
            ],
            "confidence": response.confidence,
            "related_keywords": response.related_keywords,
            "follow_up_questions": response.follow_up_questions,
            "processing_time": response.processing_time,
        }

    @staticmethod
    def _deduplicate_sequence(items: List[str]) -> List[str]:
        seen: set[str] = set()
        deduplicated: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                deduplicated.append(item)
        return deduplicated


    def _map_citation_type_to_source_type(self, citation_type: str) -> SourceType:
        mapping = {
            "statute": SourceType.EXTERNAL_LAW,
            "precedent": SourceType.EXTERNAL_PRECEDENT,
            "administrative": SourceType.EXTERNAL_GENERAL,
        }
        return mapping.get(citation_type, SourceType.EXTERNAL_GENERAL)

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
                            source_type=self._map_citation_type_to_source_type(citation.citation_type),
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
                    "??법령??????????�규�?????�???????",
                    "관???????�?찾아보시겠습?�?"
                ])
            elif "??" in intent:
                follow_ups.extend([
                    "비슷???????�?????????�겠??�?",
                    "최신 법령 개정?????�?검???�???"
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
                "facilitator": {"status": "operational", "role": "?????????"},
                "search": {"status": "operational", "role": "?????????"},
                "analyst": {"status": "operational", "role": "법적분석/?????"},
                "response": {"status": "operational", "role": "???????"},
                "citation": {"status": "operational", "role": "???출처관?"},
                "validator": {"status": "operational", "role": "종합검??질???"}
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
            answer=f"""??????�? ????{self.max_conversation_turns})?????????

?�??질문?????�?????? ????주세??

????????충분???�??? 못하???
- ??구체???질문?�?????? ??????
- 관??법령명이??조문???????질문??보세??
- ?????문�?? 직접 ?????바랍???"",
            sources=[],
            confidence=0.0,
            related_keywords=[],
            follow_up_questions=[],
            query=None
        )

    def _generate_error_response(self, user_message: str, error: str) -> LegalResponse:
        """Generate error response."""
        return LegalResponse(
            answer=f"""Sorry, an error occurred in the enhanced legal analysis process.

Error: {error}

Please try again:
- Rephrase your question
- Use simpler language
- Try different keywords

Contact administrator if problem persists.""",
            sources=[],
            confidence=0.0,
            related_keywords=[],
            follow_up_questions=[
                "Would you like to try a different approach?",
                "Can you rephrase your question?"
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
