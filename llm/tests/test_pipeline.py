"""Tests for Enhanced Agent Pipeline."""

import pytest
from unittest.mock import MagicMock, patch
import sys

# AsyncMock compatibility for Python 3.7
if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock
else:
    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super(AsyncMock, self).__call__(*args, **kwargs)

from agentl2_llm.pipeline.enhanced_agent_pipeline import EnhancedAgentPipeline
from agentl2_llm.models import LegalResponse, SearchSource, SourceType
from agentl2_llm.agents.base_agent import AgentAction


class TestEnhancedAgentPipeline:
    """Test suite for EnhancedAgentPipeline."""

    @pytest.fixture
    def pipeline(self, mock_openai_client):
        """Create pipeline instance with mocked OpenAI client."""
        with patch('agentl2_llm.pipeline.enhanced_agent_pipeline.openai.AsyncOpenAI', return_value=mock_openai_client):
            pipeline = EnhancedAgentPipeline(
                openai_api_key="test-key",
                openai_model="gpt-4",
                temperature=0.3
            )
            return pipeline

    @pytest.mark.asyncio
    async def test_pipeline_initialization(self, pipeline):
        """Test pipeline initialization."""
        assert pipeline is not None
        assert pipeline.facilitator is not None
        assert pipeline.search_agent is not None
        assert pipeline.analyst is not None
        assert pipeline.response_agent is not None
        assert pipeline.citation_agent is not None
        assert pipeline.validator is not None
        assert pipeline.max_conversation_turns == 5

    @pytest.mark.asyncio
    async def test_process_message_new_conversation(self, pipeline):
        """Test processing a message in new conversation."""
        # Mock all agent responses
        with patch.object(pipeline.facilitator, 'process') as mock_facilitator, \
             patch.object(pipeline.search_agent, 'process') as mock_search, \
             patch.object(pipeline.analyst, 'process') as mock_analyst, \
             patch.object(pipeline.response_agent, 'process') as mock_response, \
             patch.object(pipeline.citation_agent, 'process') as mock_citation, \
             patch.object(pipeline.validator, 'process') as mock_validator:

            # Setup mock responses
            from agentl2_llm.agents.base_agent import AgentResponse

            mock_facilitator.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_SEARCH,
                intent="개인정보 문의",
                keywords=["개인정보보호법", "동의"],
                confidence=0.9
            )

            mock_search.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                confidence=0.85,
                metadata={"search_results": MagicMock(total_count=5)}
            )

            mock_analyst.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                confidence=0.9
            )

            mock_response.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message="개인정보 수집 시 동의가 필요합니다.",
                confidence=0.9
            )

            mock_citation.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                confidence=0.85
            )

            mock_validator.return_value = AgentResponse(
                action=AgentAction.COMPLETE,
                message="개인정보보호법 제15조에 따라 개인정보 수집 시 명시적 동의가 필요합니다.",
                confidence=0.9
            )

            # Process message
            response = await pipeline.process_message(
                "개인정보 수집 시 동의가 필요한가요?"
            )

            # Verify response
            assert isinstance(response, LegalResponse)
            assert response.answer is not None
            assert response.confidence > 0.0
            assert response.processing_time > 0.0

            # Verify all agents were called
            mock_facilitator.assert_called_once()
            mock_search.assert_called_once()
            mock_analyst.assert_called_once()
            mock_response.assert_called_once()
            mock_citation.assert_called_once()
            mock_validator.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_needs_clarification(self, pipeline):
        """Test processing message that needs clarification."""
        with patch.object(pipeline.facilitator, 'process') as mock_facilitator:
            from agentl2_llm.agents.base_agent import AgentResponse

            # Facilitator requests clarification
            mock_facilitator.return_value = AgentResponse(
                action=AgentAction.REQUEST_CLARIFICATION,
                message="추가 정보가 필요합니다",
                clarification_options=[
                    "어떤 종류의 개인정보인가요?",
                    "수집 목적은 무엇인가요?"
                ],
                confidence=0.5
            )

            response = await pipeline.process_message(
                "개인정보에 대해 궁금합니다"
            )

            assert isinstance(response, LegalResponse)
            assert "추가 정보" in response.answer or "필요" in response.answer
            assert len(response.follow_up_questions) > 0

    @pytest.mark.asyncio
    async def test_process_message_with_conversation_id(self, pipeline):
        """Test processing with existing conversation ID."""
        conversation_id = "test-conv-123"

        with patch.object(pipeline.facilitator, 'process') as mock_facilitator, \
             patch.object(pipeline.search_agent, 'process') as mock_search, \
             patch.object(pipeline.analyst, 'process') as mock_analyst, \
             patch.object(pipeline.response_agent, 'process') as mock_response, \
             patch.object(pipeline.citation_agent, 'process') as mock_citation, \
             patch.object(pipeline.validator, 'process') as mock_validator:

            from agentl2_llm.agents.base_agent import AgentResponse

            # Setup mocks
            mock_facilitator.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_SEARCH,
                intent="법령 검색",
                keywords=["개인정보보호법"],
                confidence=0.9
            )

            mock_search.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                confidence=0.85,
                metadata={"search_results": MagicMock(total_count=3)}
            )

            mock_analyst.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                confidence=0.9
            )

            mock_response.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                message="답변입니다",
                confidence=0.9
            )

            mock_citation.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                confidence=0.85
            )

            mock_validator.return_value = AgentResponse(
                action=AgentAction.COMPLETE,
                message="최종 답변입니다",
                confidence=0.9
            )

            # First message
            response1 = await pipeline.process_message(
                "개인정보보호법이 뭔가요?",
                conversation_id=conversation_id
            )

            assert isinstance(response1, LegalResponse)

            # Second message in same conversation
            response2 = await pipeline.process_message(
                "더 자세히 알려주세요",
                conversation_id=conversation_id
            )

            assert isinstance(response2, LegalResponse)

            # Verify conversation context was maintained
            assert conversation_id in pipeline.conversations
            context = pipeline.conversations[conversation_id]
            assert len(context.user_messages) == 2

    @pytest.mark.asyncio
    async def test_conversation_turn_limit(self, pipeline):
        """Test conversation turn limit enforcement."""
        conversation_id = "test-limit-conv"

        with patch.object(pipeline.facilitator, 'process') as mock_facilitator, \
             patch.object(pipeline.search_agent, 'process'), \
             patch.object(pipeline.analyst, 'process'), \
             patch.object(pipeline.response_agent, 'process'), \
             patch.object(pipeline.citation_agent, 'process'), \
             patch.object(pipeline.validator, 'process') as mock_validator:

            from agentl2_llm.agents.base_agent import AgentResponse

            mock_facilitator.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_SEARCH,
                confidence=0.9
            )

            mock_validator.return_value = AgentResponse(
                action=AgentAction.COMPLETE,
                message="답변",
                confidence=0.9
            )

            # Send max_conversation_turns + 1 messages
            for i in range(pipeline.max_conversation_turns + 1):
                response = await pipeline.process_message(
                    f"질문 {i}",
                    conversation_id=conversation_id
                )

                if i >= pipeline.max_conversation_turns:
                    # Should get limit exceeded response
                    assert "대화 횟수" in response.answer or "최대" in response.answer

    @pytest.mark.asyncio
    async def test_event_handler_called(self, pipeline):
        """Test event handler is called for each agent step."""
        events_received = []

        async def event_handler(agent: str, payload: dict):
            events_received.append({"agent": agent, "payload": payload})

        with patch.object(pipeline.facilitator, 'process') as mock_facilitator, \
             patch.object(pipeline.search_agent, 'process') as mock_search, \
             patch.object(pipeline.analyst, 'process'), \
             patch.object(pipeline.response_agent, 'process'), \
             patch.object(pipeline.citation_agent, 'process'), \
             patch.object(pipeline.validator, 'process') as mock_validator:

            from agentl2_llm.agents.base_agent import AgentResponse

            mock_facilitator.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_SEARCH,
                confidence=0.9
            )

            mock_search.return_value = AgentResponse(
                action=AgentAction.FORWARD_TO_RESPONSE,
                confidence=0.85,
                metadata={"search_results": MagicMock(total_count=1)}
            )

            mock_validator.return_value = AgentResponse(
                action=AgentAction.COMPLETE,
                message="최종 답변",
                confidence=0.9
            )

            await pipeline.process_message(
                "테스트 질문",
                event_handler=event_handler
            )

            # Should have received events from all agents
            assert len(events_received) > 0
            agent_names = [event["agent"] for event in events_received]
            assert "facilitator" in agent_names

    @pytest.mark.asyncio
    async def test_priority_memory_updates_multi_turn(self, pipeline):
        """Latest intent/keywords should be prioritised across turns."""
        from agentl2_llm.agents.base_agent import AgentResponse

        with patch.object(pipeline.facilitator, 'process') as mock_facilitator, \
             patch.object(pipeline.search_agent, 'process') as mock_search, \
             patch.object(pipeline.analyst, 'process') as mock_analyst, \
             patch.object(pipeline.response_agent, 'process') as mock_response, \
             patch.object(pipeline.citation_agent, 'process') as mock_citation, \
             patch.object(pipeline.validator, 'process') as mock_validator:

            mock_facilitator.side_effect = [
                AgentResponse(
                    action=AgentAction.FORWARD_TO_SEARCH,
                    intent="첫 번째 의도",
                    keywords=["기존 키워드", "금융거래"],
                    confidence=0.9
                ),
                AgentResponse(
                    action=AgentAction.FORWARD_TO_SEARCH,
                    intent="두 번째 의도",
                    keywords=["새 키워드"],
                    confidence=0.92
                )
            ]

            mock_search.side_effect = [
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.85),
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.86)
            ]
            mock_analyst.side_effect = [
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.87),
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.88)
            ]
            mock_response.side_effect = [
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.9),
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.9)
            ]
            mock_citation.side_effect = [
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.85),
                AgentResponse(action=AgentAction.FORWARD_TO_RESPONSE, confidence=0.85)
            ]
            mock_validator.side_effect = [
                AgentResponse(action=AgentAction.COMPLETE, message="답변 1", confidence=0.9),
                AgentResponse(action=AgentAction.COMPLETE, message="답변 2", confidence=0.91)
            ]

            conversation_id = "priority-conv"

            await pipeline.process_message("첫 질문", conversation_id=conversation_id)
            context = pipeline.conversations[conversation_id]
            memory = context.session_metadata.get("priority_memory", {})
            assert memory.get("intents")
            assert memory["intents"][0] == "첫 번째 의도"
            assert memory["keywords"][0] == "기존 키워드"

            await pipeline.process_message("두 번째 질문", conversation_id=conversation_id)
            context = pipeline.conversations[conversation_id]
            memory = context.session_metadata.get("priority_memory", {})

            assert memory["intents"][0] == "두 번째 의도"
            assert "첫 번째 의도" in memory["intents"][1:]
            assert memory["keywords"][0] == "새 키워드"
            assert "금융거래" in memory["keywords"][1:]
            assert context.extracted_intent == "두 번째 의도"
            assert context.extracted_keywords[0] == "새 키워드"

@pytest.mark.asyncio
    async def test_error_handling(self, pipeline):
        """Test error handling in pipeline."""
        with patch.object(pipeline.facilitator, 'process') as mock_facilitator:
            # Facilitator raises error
            mock_facilitator.side_effect = Exception("Test error")

            response = await pipeline.process_message("테스트 질문")

            # Should return error response
            assert isinstance(response, LegalResponse)
            assert response.confidence == 0.0

    @pytest.mark.asyncio
    async def test_get_pipeline_status(self, pipeline):
        """Test getting pipeline status."""
        with patch.object(pipeline.search_coordinator, 'get_search_status') as mock_search_status:
            mock_search_status.return_value = {"status": "operational"}

            status = await pipeline.get_pipeline_status()

            assert "pipeline" in status
            assert "agents" in status
            assert status["pipeline"]["type"] == "enhanced_6_agent_pipeline"
            assert len(status["agents"]) == 6

    def test_get_conversation_status(self, pipeline):
        """Test getting conversation status."""
        from agentl2_llm.agents.base_agent import ConversationContext, AgentResponse

        conversation_id = "test-conv-456"

        # Create conversation context
        context = ConversationContext(
            conversation_id=conversation_id,
            user_messages=["질문 1"],
            extracted_intent="법령 검색",
            extracted_keywords=["개인정보보호법"]
        )

        context.agent_responses.append(
            AgentResponse(
                action=AgentAction.FORWARD_TO_SEARCH,
                confidence=0.9
            )
        )

        pipeline.conversations[conversation_id] = context

        status = pipeline.get_conversation_status(conversation_id)

        assert status is not None
        assert status["conversation_id"] == conversation_id
        assert status["turn_count"] == 1
        assert status["extracted_intent"] == "법령 검색"

    def test_get_conversation_status_not_found(self, pipeline):
        """Test getting status for non-existent conversation."""
        status = pipeline.get_conversation_status("non-existent-id")
        assert status is None

    def test_clear_conversation(self, pipeline):
        """Test clearing conversation context."""
        from agentl2_llm.agents.base_agent import ConversationContext

        conversation_id = "test-clear-conv"

        # Create conversation
        pipeline.conversations[conversation_id] = ConversationContext(
            conversation_id=conversation_id
        )

        # Clear conversation
        result = pipeline.clear_conversation(conversation_id)

        assert result is True
        assert conversation_id not in pipeline.conversations

    def test_clear_conversation_not_found(self, pipeline):
        """Test clearing non-existent conversation."""
        result = pipeline.clear_conversation("non-existent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_close(self, pipeline):
        """Test pipeline cleanup."""
        with patch.object(pipeline.search_coordinator, 'close') as mock_search_close, \
             patch.object(pipeline.openai_client, 'close') as mock_openai_close:

            await pipeline.close()

            mock_search_close.assert_called_once()
            mock_openai_close.assert_called_once()
