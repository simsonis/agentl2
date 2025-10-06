"""Pytest configuration and fixtures for agent tests."""

import pytest
from unittest.mock import MagicMock
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# AsyncMock is only available in Python 3.8+
# For Python 3.7, we need to create our own
if sys.version_info >= (3, 8):
    from unittest.mock import AsyncMock
else:
    class AsyncMock(MagicMock):
        async def __call__(self, *args, **kwargs):
            return super(AsyncMock, self).__call__(*args, **kwargs)

import openai
from agentl2_llm.agents.base_agent import ConversationContext, AgentResponse, AgentAction


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI async client."""
    client = MagicMock(spec=openai.AsyncOpenAI)

    # Mock the chat completions structure
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(
            message=MagicMock(
                content="1. intent = {개인정보 수집 동의 절차 문의}\n2. search keywords = {개인정보보호법, 동의, 수집}"
            )
        )
    ]

    # Create nested mock structure
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    client.chat.completions.create = AsyncMock(return_value=mock_completion)
    client.close = AsyncMock()

    return client


@pytest.fixture
def sample_context():
    """Sample conversation context for testing."""
    return ConversationContext(
        conversation_id="test-conversation-123",
        user_messages=[],
        agent_responses=[],
        extracted_intent=None,
        extracted_keywords=[]
    )


@pytest.fixture
def sample_context_with_history():
    """Sample conversation context with history."""
    return ConversationContext(
        conversation_id="test-conversation-456",
        user_messages=["개인정보 처리에 대해 궁금합니다"],
        agent_responses=[
            AgentResponse(
                action=AgentAction.REQUEST_CLARIFICATION,
                message="구체적으로 어떤 부분이 궁금하신가요?",
                intent=None,
                keywords=[],
                confidence=0.3
            )
        ],
        extracted_intent="개인정보 처리 문의",
        extracted_keywords=["개인정보", "처리"]
    )


@pytest.fixture
def mock_llm_response_clear():
    """Mock LLM response for clear intent."""
    return """1. intent = {개인정보 수집 동의 절차 확인 문의}
2. search keywords = {개인정보보호법, 동의, 명시적 동의, 개인정보 수집}"""


@pytest.fixture
def mock_llm_response_needs_clarification():
    """Mock LLM response that needs clarification."""
    return """1. intent = {개인정보 관련 문의}
2. search keywords = {개인정보}
3(option). = {어떤 종류의 개인정보를 수집하시나요? (이름, 주민번호, 연락처 등)}
3(option). = {개인정보를 어떤 목적으로 활용하실 계획인가요?}
3(option). = {개인정보 주체에게 동의를 받으셨나요?}"""


@pytest.fixture
def mock_search_results():
    """Mock search results."""
    from agentl2_llm.models import SearchResults, SearchResult, SearchSource, SourceType

    return SearchResults(
        internal_results=[
            SearchResult(
                title="개인정보보호법 제15조",
                source=SearchSource(
                    url="https://law.go.kr/LSW/lsInfoP.do?lsId=008032",
                    title="개인정보보호법 제15조",
                    source_type=SourceType.INTERNAL_LAW,
                    confidence=0.95,
                    excerpt="개인정보처리자는 다음 각 호의 어느 하나에 해당하는 경우에는 개인정보를 수집할 수 있으며..."
                ),
                relevance_score=0.95
            )
        ],
        external_results=[],
        total_count=1,
        search_duration=0.5
    )
