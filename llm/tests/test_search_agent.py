"""Tests for Search Agent."""

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

from agentl2_llm.agents.search_agent import SearchAgent
from agentl2_llm.agents.base_agent import (
    ConversationContext,
    AgentResponse,
    AgentAction
)
from agentl2_llm.models import SearchResults, SearchResult, SearchSource, SourceType


class TestSearchAgent:
    """Test suite for SearchAgent."""

    @pytest.fixture
    def mock_search_coordinator(self):
        """Mock SearchCoordinator."""
        coordinator = AsyncMock()

        # Mock search results
        mock_results = SearchResults(
            internal_results=[
                SearchResult(
                    title="개인정보보호법 제15조",
                    source=SearchSource(
                        url="https://law.go.kr/LSW/lsInfoP.do?lsId=008032",
                        title="개인정보보호법 제15조 (개인정보의 수집·이용)",
                        source_type=SourceType.INTERNAL_LAW,
                        confidence=0.95,
                        excerpt="개인정보처리자는 다음 각 호의 어느 하나에 해당하는 경우에는..."
                    ),
                    relevance_score=0.95
                )
            ],
            external_results=[],
            total_count=1,
            search_duration=0.3
        )

        coordinator.search = AsyncMock(return_value=mock_results)

        return coordinator

    @pytest.mark.asyncio
    async def test_initialization(self, mock_openai_client, mock_search_coordinator):
        """Test agent initialization."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        assert agent.name == "Search"
        assert agent.model == "gpt-4"
        assert agent.temperature == 0.2
        assert agent.search_coordinator == mock_search_coordinator

    @pytest.mark.asyncio
    async def test_process_with_keywords(
        self,
        mock_openai_client,
        mock_search_coordinator,
        sample_context_with_history
    ):
        """Test processing with extracted keywords."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        # Add keywords to context
        sample_context_with_history.extracted_keywords = [
            "개인정보보호법", "동의", "수집"
        ]

        response = await agent.process(
            "개인정보 수집 시 동의 필요 여부",
            sample_context_with_history
        )

        assert isinstance(response, AgentResponse)
        assert response.action == AgentAction.FORWARD_TO_RESPONSE
        assert "search_results" in response.metadata
        assert response.confidence > 0.0

        # Verify search was called
        mock_search_coordinator.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_no_keywords(
        self,
        mock_openai_client,
        mock_search_coordinator,
        sample_context
    ):
        """Test processing without keywords."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        # Mock LLM to extract keywords
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content="검색 키워드: 개인정보보호법, 수집, 동의"
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await agent.process(
            "개인정보 수집에 대해 알고 싶습니다",
            sample_context
        )

        assert isinstance(response, AgentResponse)
        # Should have extracted keywords
        assert "search_results" in response.metadata

    @pytest.mark.asyncio
    async def test_process_empty_search_results(
        self,
        mock_openai_client,
        mock_search_coordinator,
        sample_context_with_history
    ):
        """Test processing when search returns no results."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        # Mock empty search results
        empty_results = SearchResults(
            internal_results=[],
            external_results=[],
            total_count=0,
            search_duration=0.1
        )
        mock_search_coordinator.search = AsyncMock(return_value=empty_results)

        sample_context_with_history.extracted_keywords = ["존재하지않는키워드"]

        response = await agent.process(
            "검색 질의",
            sample_context_with_history
        )

        assert isinstance(response, AgentResponse)
        assert response.confidence < 0.5  # Low confidence with no results

    @pytest.mark.asyncio
    async def test_multi_round_search(
        self,
        mock_openai_client,
        mock_search_coordinator,
        sample_context_with_history
    ):
        """Test multi-round search capability."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        # First round keywords
        sample_context_with_history.extracted_keywords = ["개인정보보호법"]

        # Mock LLM to suggest additional keywords
        mock_completion = MagicMock()
        mock_completion.choices = [
            MagicMock(
                message=MagicMock(
                    content="추가 검색 필요: 동의, 명시적 동의, 수집"
                )
            )
        ]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_completion)

        response = await agent.process(
            "개인정보 수집 동의 절차",
            sample_context_with_history
        )

        assert isinstance(response, AgentResponse)
        # Should have performed search
        assert mock_search_coordinator.search.called

    @pytest.mark.asyncio
    async def test_error_handling(
        self,
        mock_openai_client,
        mock_search_coordinator,
        sample_context
    ):
        """Test error handling when search fails."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        # Mock search to raise error
        mock_search_coordinator.search = AsyncMock(
            side_effect=Exception("Search service error")
        )

        sample_context.extracted_keywords = ["테스트"]

        response = await agent.process(
            "검색 질의",
            sample_context
        )

        assert isinstance(response, AgentResponse)
        assert response.confidence == 0.0
        assert "검색" in response.message or "오류" in response.message

    @pytest.mark.asyncio
    async def test_relevance_scoring(
        self,
        mock_openai_client,
        mock_search_coordinator,
        sample_context_with_history
    ):
        """Test that search results are scored by relevance."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        # Mock multiple results with different relevance
        mock_results = SearchResults(
            internal_results=[
                SearchResult(
                    title="매우 관련성 높은 결과",
                    source=SearchSource(
                        url="https://example.com/1",
                        title="개인정보보호법 제15조",
                        source_type=SourceType.INTERNAL_LAW,
                        confidence=0.95,
                        excerpt="..."
                    ),
                    relevance_score=0.95
                ),
                SearchResult(
                    title="관련성 중간 결과",
                    source=SearchSource(
                        url="https://example.com/2",
                        title="개인정보보호법 시행령",
                        source_type=SourceType.INTERNAL_LAW,
                        confidence=0.7,
                        excerpt="..."
                    ),
                    relevance_score=0.7
                )
            ],
            external_results=[],
            total_count=2,
            search_duration=0.4
        )

        mock_search_coordinator.search = AsyncMock(return_value=mock_results)
        sample_context_with_history.extracted_keywords = ["개인정보보호법"]

        response = await agent.process(
            "개인정보보호법 관련 검색",
            sample_context_with_history
        )

        assert isinstance(response, AgentResponse)
        search_results = response.metadata.get("search_results")
        assert search_results is not None
        assert search_results.total_count == 2

        # Check that results are ordered by relevance
        all_results = search_results.get_all_results()
        if len(all_results) >= 2:
            assert all_results[0].relevance_score >= all_results[1].relevance_score

    @pytest.mark.asyncio
    async def test_internal_and_external_search(
        self,
        mock_openai_client,
        mock_search_coordinator,
        sample_context_with_history
    ):
        """Test combining internal and external search results."""
        agent = SearchAgent(
            openai_client=mock_openai_client,
            search_coordinator=mock_search_coordinator,
            model="gpt-4",
            temperature=0.2
        )

        # Mock results from both sources
        mock_results = SearchResults(
            internal_results=[
                SearchResult(
                    title="내부 DB 법령",
                    source=SearchSource(
                        url="internal://law/1",
                        title="개인정보보호법",
                        source_type=SourceType.INTERNAL_LAW,
                        confidence=0.9,
                        excerpt="..."
                    ),
                    relevance_score=0.9
                )
            ],
            external_results=[
                SearchResult(
                    title="외부 API 판례",
                    source=SearchSource(
                        url="https://casenote.kr/1",
                        title="대법원 2020다12345",
                        source_type=SourceType.EXTERNAL_PRECEDENT,
                        confidence=0.85,
                        excerpt="..."
                    ),
                    relevance_score=0.85
                )
            ],
            total_count=2,
            search_duration=0.6
        )

        mock_search_coordinator.search = AsyncMock(return_value=mock_results)
        sample_context_with_history.extracted_keywords = ["개인정보보호법", "판례"]

        response = await agent.process(
            "개인정보보호법 관련 판례 검색",
            sample_context_with_history
        )

        assert isinstance(response, AgentResponse)
        search_results = response.metadata["search_results"]

        assert len(search_results.internal_results) > 0
        assert len(search_results.external_results) > 0
        assert search_results.total_count == 2
