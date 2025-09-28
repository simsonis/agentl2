"""
Main legal chatbot pipeline.
"""

from __future__ import annotations

import time
import asyncio
from typing import Optional, Dict, Any

from loguru import logger

from ..models import LegalResponse
from ..query.query_processor import QueryProcessor
from ..search.search_coordinator import SearchCoordinator
from ..response.response_generator import ResponseGenerator


class LegalChatbot:
    """Main legal chatbot that orchestrates the entire pipeline."""

    def __init__(
        self,
        openai_api_key: str,
        openai_model: str = "gpt-4",
        search_limit: int = 20,
        enable_internal_search: bool = True,
        enable_external_search: bool = True
    ):
        """
        Initialize the legal chatbot.

        Args:
            openai_api_key: OpenAI API key for LLM
            openai_model: OpenAI model to use
            search_limit: Maximum number of search results
            enable_internal_search: Enable internal database search
            enable_external_search: Enable external search
        """
        self.query_processor = QueryProcessor()
        self.search_coordinator = SearchCoordinator()
        self.response_generator = ResponseGenerator(openai_api_key, openai_model)

        self.search_limit = search_limit
        self.enable_internal_search = enable_internal_search
        self.enable_external_search = enable_external_search

        logger.info("Legal chatbot initialized")

    async def close(self):
        """Close all connections and cleanup resources."""
        await self.search_coordinator.close()
        logger.info("Legal chatbot closed")

    async def process_query(
        self,
        user_query: str,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> LegalResponse:
        """
        Process a legal query and return a comprehensive response.

        Args:
            user_query: The user's legal question
            conversation_context: Optional context from previous conversation

        Returns:
            LegalResponse with answer, sources, and metadata
        """
        start_time = time.time()

        try:
            logger.info(f"Processing query: {user_query[:100]}...")

            # Step 1: Query Analysis
            logger.info("Analyzing query intent and extracting keywords...")
            legal_query = await self.query_processor.process(user_query)
            logger.info(f"Query analysis complete - Intent: {legal_query.intent}, Keywords: {legal_query.keywords}")

            # Step 2: Search Execution
            logger.info("Executing search across available sources...")
            search_results = await self.search_coordinator.search(
                keywords=legal_query.keywords,
                intent=legal_query.intent,
                include_internal=self.enable_internal_search,
                include_external=self.enable_external_search,
                limit=self.search_limit
            )
            logger.info(f"Search complete - Found {search_results.total_count} results")

            # Step 3: Response Generation
            logger.info("Generating response with verification...")
            response = await self.response_generator.generate(
                query=legal_query,
                search_results=search_results.get_all_results()
            )

            # Update processing time
            response.processing_time = time.time() - start_time

            logger.info(f"Query processing complete in {response.processing_time:.2f}s")
            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return self._generate_error_response(user_query, str(e))

    async def get_status(self) -> Dict[str, Any]:
        """Get the current status of all chatbot components."""
        search_status = await self.search_coordinator.get_search_status()

        return {
            "chatbot": {
                "status": "operational",
                "search_limit": self.search_limit,
                "internal_search_enabled": self.enable_internal_search,
                "external_search_enabled": self.enable_external_search,
            },
            "search": search_status,
            "response_generator": {
                "model": self.response_generator.model,
                "status": "operational"
            }
        }

    async def process_batch_queries(
        self,
        queries: list[str],
        max_concurrent: int = 3
    ) -> list[LegalResponse]:
        """
        Process multiple queries concurrently.

        Args:
            queries: List of user queries
            max_concurrent: Maximum number of concurrent processing

        Returns:
            List of LegalResponse objects
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_single(query: str) -> LegalResponse:
            async with semaphore:
                return await self.process_query(query)

        logger.info(f"Processing {len(queries)} queries with max concurrency {max_concurrent}")

        tasks = [process_single(query) for query in queries]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_responses = []
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                logger.error(f"Error processing query {i}: {response}")
                error_response = self._generate_error_response(queries[i], str(response))
                processed_responses.append(error_response)
            else:
                processed_responses.append(response)

        return processed_responses

    def _generate_error_response(self, query: str, error_message: str) -> LegalResponse:
        """Generate an error response when processing fails."""
        from ..models import LegalQuery, QueryIntent, SearchSource, SourceType

        # Create minimal query object
        error_query = LegalQuery(
            original_text=query,
            intent=QueryIntent.GENERAL_INQUIRY,
            keywords=[],
            confidence=0.0
        )

        return LegalResponse(
            answer=f"""죄송합니다. 질문을 처리하는 중에 오류가 발생했습니다.

오류 내용: {error_message}

다음 사항을 확인해 주세요:
- 네트워크 연결 상태
- 질문 내용이 명확한지
- 잠시 후 다시 시도해 보세요

지속적인 문제가 발생하면 관리자에게 문의하시기 바랍니다.""",
            sources=[],
            confidence=0.0,
            related_keywords=[],
            follow_up_questions=[
                "다른 방식으로 질문해 보시겠습니까?",
                "간단한 키워드로 검색해 보시겠습니까?"
            ],
            processing_time=1.0,
            query=error_query
        )


class ConversationManager:
    """Manages conversation context and history."""

    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.conversations: Dict[str, list] = {}

    def add_to_history(self, conversation_id: str, query: str, response: LegalResponse):
        """Add query and response to conversation history."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []

        self.conversations[conversation_id].append({
            "query": query,
            "response": response,
            "timestamp": time.time()
        })

        # Limit history size
        if len(self.conversations[conversation_id]) > self.max_history:
            self.conversations[conversation_id] = self.conversations[conversation_id][-self.max_history:]

    def get_context(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation context for improving responses."""
        if conversation_id not in self.conversations:
            return None

        history = self.conversations[conversation_id]
        if not history:
            return None

        # Extract context from recent conversation
        recent_keywords = []
        recent_intents = []

        for entry in history[-3:]:  # Last 3 exchanges
            response = entry["response"]
            if response.query:
                recent_keywords.extend(response.query.keywords)
                recent_intents.append(response.query.intent)

        return {
            "recent_keywords": list(set(recent_keywords)),
            "recent_intents": list(set(recent_intents)),
            "conversation_length": len(history),
            "last_query_time": history[-1]["timestamp"]
        }

    def clear_conversation(self, conversation_id: str):
        """Clear conversation history for a given ID."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]