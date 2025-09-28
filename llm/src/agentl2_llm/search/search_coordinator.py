"""
Search coordination across internal and external sources.
"""

from __future__ import annotations

import time
from typing import List

from loguru import logger

from ..models import SearchResults, QueryIntent
from .internal_search import InternalSearcher
from .external_search import ExternalSearcher


class SearchCoordinator:
    """Coordinates search across internal and external sources."""

    def __init__(self):
        self.internal_searcher = InternalSearcher()
        self.external_searcher = ExternalSearcher()

    async def close(self):
        """Close all search connections."""
        await self.external_searcher.close()

    async def search(
        self,
        keywords: List[str],
        intent: QueryIntent,
        include_internal: bool = True,
        include_external: bool = True,
        limit: int = 20
    ) -> SearchResults:
        """Coordinate search across all available sources."""
        start_time = time.time()
        results = SearchResults()

        logger.info(f"Starting search for keywords: {keywords}, intent: {intent}")

        try:
            # Internal search (currently returns empty results)
            if include_internal:
                logger.info("Searching internal database...")
                internal_results = await self.internal_searcher.search(keywords, intent)
                results.add_internal(internal_results)
                logger.info(f"Internal search returned {len(internal_results)} results")

            # External search
            if include_external:
                logger.info("Searching external sources...")
                external_results = await self.external_searcher.search(keywords, intent, limit)
                results.add_external(external_results)
                logger.info(f"External search returned {len(external_results)} results")

        except Exception as e:
            logger.error(f"Error during search coordination: {e}")

        # Calculate search duration
        results.search_duration = time.time() - start_time

        logger.info(f"Search completed in {results.search_duration:.2f}s, total results: {results.total_count}")
        return results

    async def get_search_status(self) -> dict:
        """Get status of all search capabilities."""
        internal_status = self.internal_searcher.get_status()

        return {
            "internal": internal_status,
            "external": {
                "casenote_kr": {
                    "available": True,
                    "law_search_url": "https://casenote.kr/search_law/",
                    "precedent_search_url": "https://casenote.kr/search/",
                }
            }
        }