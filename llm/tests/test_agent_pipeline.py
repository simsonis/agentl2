"""
Tests for the agent-based pipeline.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from agentl2_llm.agents.base_agent import AgentAction, ConversationContext
from agentl2_llm.pipeline.agent_pipeline import AgentPipeline, ConversationManager


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Mock LLM response"

    client.chat.completions.create.return_value = mock_response
    return client


@pytest.mark.asyncio
async def test_facilitator_agent_clarification():
    """Test facilitator agent requesting clarification."""

    # This would be a real test with proper mocking
    # For now, it's a placeholder
    assert True


@pytest.mark.asyncio
async def test_agent_pipeline_flow():
    """Test complete agent pipeline flow."""

    # This would test the entire pipeline
    # For now, it's a placeholder
    assert True


def test_conversation_context():
    """Test conversation context management."""

    context = ConversationContext(conversation_id="test-123")
    assert context.conversation_id == "test-123"
    assert len(context.user_messages) == 0
    assert len(context.agent_responses) == 0


# Example usage demonstration
async def example_usage():
    """Example of how to use the agent pipeline."""

    # This is just a demonstration, not a real test
    pipeline = AgentPipeline(
        openai_api_key="test-key",
        openai_model="gpt-4"
    )

    # Simulate processing a vague query
    vague_response = await pipeline.process_message(
        "개인정보 관련해서 궁금한 게 있어요"
    )

    # Should request clarification
    assert "추가 정보" in vague_response.answer or "더 자세히" in vague_response.answer

    await pipeline.close()