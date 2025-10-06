"""Tests for Base Agent."""

import pytest
from unittest.mock import MagicMock
import sys

# AsyncMock compatibility for Python 3.7
if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock
else:
    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super(AsyncMock, self).__call__(*args, **kwargs)

from agentl2_llm.agents.base_agent import (
    BaseAgent,
    AgentResponse,
    AgentAction,
    ConversationContext
)


class TestBaseAgent:
    """Test suite for BaseAgent and related models."""

    def test_agent_action_enum(self):
        """Test AgentAction enum values."""
        assert AgentAction.CONTINUE_CONVERSATION.value == "continue_conversation"
        assert AgentAction.FORWARD_TO_SEARCH.value == "forward_to_search"
        assert AgentAction.FORWARD_TO_RESPONSE.value == "forward_to_response"
        assert AgentAction.REQUEST_CLARIFICATION.value == "request_clarification"
        assert AgentAction.COMPLETE.value == "complete"

    def test_agent_response_creation(self):
        """Test AgentResponse model creation."""
        response = AgentResponse(
            action=AgentAction.FORWARD_TO_SEARCH,
            message="검색을 수행하겠습니다",
            intent="개인정보 문의",
            keywords=["개인정보보호법", "동의"],
            confidence=0.85
        )

        assert response.action == AgentAction.FORWARD_TO_SEARCH
        assert response.message == "검색을 수행하겠습니다"
        assert response.intent == "개인정보 문의"
        assert len(response.keywords) == 2
        assert response.confidence == 0.85
        assert isinstance(response.metadata, dict)
        assert isinstance(response.clarification_options, list)

    def test_agent_response_defaults(self):
        """Test AgentResponse default values."""
        response = AgentResponse(
            action=AgentAction.COMPLETE
        )

        assert response.message is None
        assert response.intent is None
        assert response.keywords == []
        assert response.clarification_options == []
        assert response.confidence == 0.0
        assert response.metadata == {}

    def test_agent_response_confidence_validation(self):
        """Test confidence score validation (0.0 to 1.0)."""
        # Valid confidence
        response = AgentResponse(
            action=AgentAction.COMPLETE,
            confidence=0.5
        )
        assert response.confidence == 0.5

        # Edge cases
        response_min = AgentResponse(
            action=AgentAction.COMPLETE,
            confidence=0.0
        )
        assert response_min.confidence == 0.0

        response_max = AgentResponse(
            action=AgentAction.COMPLETE,
            confidence=1.0
        )
        assert response_max.confidence == 1.0

    def test_conversation_context_creation(self):
        """Test ConversationContext model creation."""
        context = ConversationContext(
            conversation_id="test-123",
            user_messages=["첫 번째 질문"],
            extracted_intent="법령 검색",
            extracted_keywords=["개인정보보호법"]
        )

        assert context.conversation_id == "test-123"
        assert len(context.user_messages) == 1
        assert context.extracted_intent == "법령 검색"
        assert len(context.extracted_keywords) == 1
        assert isinstance(context.agent_responses, list)
        assert isinstance(context.session_metadata, dict)

    def test_conversation_context_defaults(self):
        """Test ConversationContext default values."""
        context = ConversationContext(
            conversation_id="test-456"
        )

        assert context.user_messages == []
        assert context.agent_responses == []
        assert context.extracted_intent is None
        assert context.extracted_keywords == []
        assert context.session_metadata == {}

    def test_parse_structured_response_full(self, mock_openai_client):
        """Test parsing fully structured LLM response."""
        # Create a concrete implementation for testing
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Test prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="Test",
            openai_client=mock_openai_client
        )

        llm_response = """1. intent = {개인정보 수집 동의 절차 확인}
2. search keywords = {개인정보보호법, 동의, 명시적 동의, 수집}
3(option). = {수집 항목은 무엇인가요?}
3(option). = {수집 목적은 무엇인가요?}"""

        parsed = agent._parse_structured_response(llm_response)

        assert parsed["intent"] == "개인정보 수집 동의 절차 확인"
        assert "개인정보보호법" in parsed["keywords"]
        assert "동의" in parsed["keywords"]
        assert len(parsed["clarification_options"]) == 2
        assert parsed["confidence"] >= 0.6

    def test_parse_structured_response_partial(self, mock_openai_client):
        """Test parsing partial LLM response."""
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Test prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="Test",
            openai_client=mock_openai_client
        )

        llm_response = """1. intent = {법률 문의}
2. search keywords = {}"""

        parsed = agent._parse_structured_response(llm_response)

        assert parsed["intent"] == "법률 문의"
        assert parsed["confidence"] < 0.9  # Lower confidence without keywords

    def test_parse_structured_response_malformed(self, mock_openai_client):
        """Test parsing malformed LLM response."""
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Test prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="Test",
            openai_client=mock_openai_client
        )

        llm_response = "This is not a properly formatted response"

        parsed = agent._parse_structured_response(llm_response)

        assert parsed["intent"] is None
        assert parsed["keywords"] == []
        assert parsed["clarification_options"] == []
        assert parsed["confidence"] <= 0.3

    @pytest.mark.asyncio
    async def test_call_llm_success(self, mock_openai_client):
        """Test successful LLM call."""
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Test prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="Test",
            openai_client=mock_openai_client,
            model="gpt-4",
            temperature=0.5
        )

        messages = [
            {"role": "system", "content": "You are a test agent"},
            {"role": "user", "content": "Test question"}
        ]

        result = await agent._call_llm(messages, max_tokens=100)

        assert isinstance(result, str)
        mock_openai_client.chat.completions.create.assert_called_once()

        # Verify call parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        # call_args is a tuple (args, kwargs), we need the kwargs part
        _, kwargs = call_args
        assert kwargs['model'] == "gpt-4"
        assert kwargs['temperature'] == 0.5
        assert kwargs['max_tokens'] == 100

    @pytest.mark.asyncio
    async def test_call_llm_error(self, mock_openai_client):
        """Test LLM call error handling."""
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Test prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="Test",
            openai_client=mock_openai_client
        )

        # Mock LLM to raise error
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception) as exc_info:
            await agent._call_llm(messages)

        assert "API Error" in str(exc_info.value)

    def test_build_conversation_history_empty(
        self,
        mock_openai_client,
        sample_context
    ):
        """Test building conversation history with empty context."""
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Test system prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="Test",
            openai_client=mock_openai_client
        )

        messages = agent._build_conversation_history(sample_context)

        # Should only have system prompt
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Test system prompt"

    def test_build_conversation_history_with_messages(
        self,
        mock_openai_client,
        sample_context_with_history
    ):
        """Test building conversation history with existing messages."""
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Test system prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="Test",
            openai_client=mock_openai_client
        )

        messages = agent._build_conversation_history(sample_context_with_history)

        # Should have system + user + assistant
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert any(msg["role"] == "user" for msg in messages)
        assert any(msg["role"] == "assistant" for msg in messages)

    def test_agent_initialization(self, mock_openai_client):
        """Test agent initialization with custom parameters."""
        class TestAgent(BaseAgent):
            def _get_system_prompt(self) -> str:
                return "Custom system prompt"

            async def process(self, user_input: str, context: ConversationContext) -> AgentResponse:
                return AgentResponse(action=AgentAction.COMPLETE)

        agent = TestAgent(
            name="CustomAgent",
            openai_client=mock_openai_client,
            model="gpt-4-turbo",
            temperature=0.7
        )

        assert agent.name == "CustomAgent"
        assert agent.model == "gpt-4-turbo"
        assert agent.temperature == 0.7
        assert agent.client == mock_openai_client
        assert agent.system_prompt == "Custom system prompt"
