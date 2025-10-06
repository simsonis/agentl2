"""Tests for Facilitator Agent."""

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

from agentl2_llm.agents.facilitator_agent import FacilitatorAgent
from agentl2_llm.agents.base_agent import (
    ConversationContext,
    AgentResponse,
    AgentAction
)


class TestFacilitatorAgent:
    """Test suite for FacilitatorAgent."""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_openai_client):
        """Test agent initialization."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        assert agent.name == "Facilitator"
        assert agent.model == "gpt-4"
        assert agent.temperature == 0.3
        assert agent.client == mock_openai_client
        assert len(agent.system_prompt) > 0

    @pytest.mark.asyncio
    async def test_process_clear_intent(self, mock_openai_client, sample_context):
        """Test processing user input with clear intent."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        # Mock LLM response with clear intent
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content="1. intent = {개인정보 수집 동의 절차 확인 문의}\n2. search keywords = {개인정보보호법, 동의, 명시적 동의, 개인정보 수집}"
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await agent.process(
            "우리 회사에서 고객 개인정보를 수집할 때 동의 절차가 필요한가요?",
            sample_context
        )

        assert isinstance(response, AgentResponse)
        assert response.action == AgentAction.FORWARD_TO_SEARCH
        assert response.intent is not None
        assert len(response.keywords) > 0
        assert "개인정보보호법" in response.keywords or "개인정보" in response.keywords
        assert response.confidence > 0.5

    @pytest.mark.asyncio
    async def test_process_needs_clarification(self, mock_openai_client, sample_context):
        """Test processing vague user input that needs clarification."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        # Mock LLM response that needs clarification
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content="""1. intent = {개인정보 관련 문의}
2. search keywords = {개인정보}
3(option). = {어떤 종류의 개인정보를 수집하시나요?}
3(option). = {개인정보를 어떤 목적으로 활용하실 계획인가요?}
3(option). = {개인정보 주체에게 동의를 받으셨나요?}"""
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await agent.process(
            "개인정보 처리에 대해 궁금합니다",
            sample_context
        )

        assert isinstance(response, AgentResponse)
        assert response.action == AgentAction.REQUEST_CLARIFICATION
        assert len(response.clarification_options) > 0
        assert "어떤" in response.message or "추가" in response.message

    @pytest.mark.asyncio
    async def test_process_direct_question_skips_clarification(
        self,
        mock_openai_client,
        sample_context,
        mock_llm_response_needs_clarification
    ):
        """Direct questions should not trigger clarification loops."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content=mock_llm_response_needs_clarification
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await agent.process(
            "금융회사의 익명처리가 필요한 경우에 대해 설명해주세요",
            sample_context
        )

        assert response.action == AgentAction.FORWARD_TO_SEARCH
        assert response.clarification_options == []

    @pytest.mark.asyncio
    async def test_process_avoids_repeated_clarification(
        self,
        mock_openai_client,
        sample_context_with_history,
        mock_llm_response_needs_clarification
    ):
        """Once clarification was requested, avoid repeating it after user reply."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content=mock_llm_response_needs_clarification
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await agent.process(
            "추가 활용 목적이 포함되었습니다. 관련 법령으로 처리하세요",
            sample_context_with_history
        )

        assert response.action == AgentAction.FORWARD_TO_SEARCH
        assert response.clarification_options == []

    async def test_process_with_conversation_history(
        self,
        mock_openai_client,
        sample_context_with_history
    ):
        """Test processing with conversation history."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        # Mock LLM response
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content="1. intent = {개인정보 가명처리 마케팅 활용 적법성 확인}\n2. search keywords = {개인정보보호법, 가명처리, 마케팅, 활용}"
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await agent.process(
            "가명처리해서 마케팅에 활용하려고 합니다",
            sample_context_with_history
        )

        assert isinstance(response, AgentResponse)
        assert response.intent is not None
        assert len(response.keywords) > 0

        # Verify conversation history was used
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args.kwargs['messages']
        assert len(messages) >= 3  # system + previous user + previous assistant + new user

    def test_build_conversation_history_includes_priority_context(
        self,
        mock_openai_client
    ):
        """Priority memory summary should be injected into conversation history."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        context = ConversationContext(
            conversation_id="ctx-priority",
            user_messages=["첫 번째 질문이 무엇인지 말해줘"],
            agent_responses=[]
        )
        context.session_metadata["priority_memory"] = {
            "intents": ["금융거래 익명처리 범위 파악"],
            "keywords": ["금융회사", "익명처리", "개인정보"]
        }

        messages = agent._build_conversation_history(context)
        system_messages = [msg["content"] for msg in messages if msg["role"] == "system"]

        assert any("최근 대화 맥락" in content for content in system_messages)
        assert any("핵심 키워드" in content for content in system_messages)


    @pytest.mark.asyncio
    async def test_error_handling(self, mock_openai_client, sample_context):
        """Test error handling when LLM call fails."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        # Mock LLM to raise an error
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("OpenAI API Error")
        )

        response = await agent.process(
            "개인정보 처리 문의",
            sample_context
        )

        assert isinstance(response, AgentResponse)
        assert response.action == AgentAction.CONTINUE_CONVERSATION
        assert response.confidence == 0.0
        assert "오류" in response.message or "죄송" in response.message

    @pytest.mark.asyncio
    async def test_validate_completeness_sufficient(
        self,
        mock_openai_client,
        sample_context
    ):
        """Test intent/keyword validation with sufficient information."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        intent = "개인정보 수집 동의 절차 확인 문의"
        keywords = ["개인정보보호법", "동의", "수집"]

        is_complete = await agent.validate_completeness(intent, keywords, sample_context)

        assert is_complete is True

    @pytest.mark.asyncio
    async def test_validate_completeness_insufficient(
        self,
        mock_openai_client,
        sample_context
    ):
        """Test intent/keyword validation with insufficient information."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        # Too short intent
        intent = "문의"
        keywords = ["개인정보"]

        is_complete = await agent.validate_completeness(intent, keywords, sample_context)

        assert is_complete is False

    @pytest.mark.asyncio
    async def test_validate_completeness_no_legal_context(
        self,
        mock_openai_client,
        sample_context
    ):
        """Test validation fails when no legal context."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        intent = "일반적인 질문입니다"
        keywords = ["질문", "도움"]

        is_complete = await agent.validate_completeness(intent, keywords, sample_context)

        assert is_complete is False

    def test_format_clarification_message(self, mock_openai_client):
        """Test clarification message formatting."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        options = [
            "어떤 종류의 개인정보를 수집하시나요?",
            "수집 목적은 무엇인가요?",
            "동의를 받으셨나요?"
        ]

        message = agent._format_clarification_message(options)

        assert "추가 정보" in message or "필요" in message
        assert all(opt in message for opt in options)
        assert "1." in message
        assert "2." in message
        assert "3." in message

    def test_format_clarification_message_empty(self, mock_openai_client):
        """Test clarification message with empty options."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        message = agent._format_clarification_message([])

        assert len(message) > 0
        assert "자세히" in message or "말씀" in message

    def test_extract_conversation_summary_empty(
        self,
        mock_openai_client,
        sample_context
    ):
        """Test conversation summary extraction with empty context."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        summary = agent.extract_conversation_summary(sample_context)

        assert "새로운 대화" in summary or "시작" in summary

    def test_extract_conversation_summary_with_history(
        self,
        mock_openai_client,
        sample_context_with_history
    ):
        """Test conversation summary extraction with history."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        summary = agent.extract_conversation_summary(sample_context_with_history)

        assert "대화 턴" in summary
        assert "의도" in summary or "키워드" in summary

    def test_parse_structured_response(self, mock_openai_client):
        """Test parsing of structured LLM response."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        llm_response = """1. intent = {개인정보 수집 동의 절차 확인}
2. search keywords = {개인정보보호법, 동의, 수집, 명시적 동의}
3(option). = {수집하려는 개인정보 항목은 무엇인가요?}"""

        parsed = agent._parse_structured_response(llm_response)

        assert parsed["intent"] == "개인정보 수집 동의 절차 확인"
        assert "개인정보보호법" in parsed["keywords"]
        assert "동의" in parsed["keywords"]
        assert len(parsed["clarification_options"]) >= 1
        assert parsed["confidence"] > 0.0

    def test_parse_structured_response_no_clarification(self, mock_openai_client):
        """Test parsing response without clarification options."""
        agent = FacilitatorAgent(
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.3
        )

        llm_response = """1. intent = {금융소비자 보호 법령 확인}
2. search keywords = {금융소비자보호법, 불완전판매, 설명의무}"""

        parsed = agent._parse_structured_response(llm_response)

        assert parsed["intent"] is not None
        assert len(parsed["keywords"]) > 0
        assert len(parsed["clarification_options"]) == 0
        assert parsed["confidence"] >= 0.6  # Should have reasonable confidence
