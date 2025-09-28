"""
External search implementation for casenote.kr.
"""

from __future__ import annotations

import asyncio
import urllib.parse
from datetime import datetime
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup
from loguru import logger

from ..models import SearchResult, QueryIntent, SourceType, SearchSource


class CasenoteSearcher:
    """Searches casenote.kr for legal information."""

    LAW_SEARCH_URL = "https://casenote.kr/search_law/"
    PRECEDENT_SEARCH_URL = "https://casenote.kr/search/"

    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "User-Agent": "agentl2-llm/0.1.0 (Legal Research Bot)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
            }
        )

    async def close(self):
        """Close the HTTP session."""
        await self.session.aclose()

    async def search_laws(self, keywords: List[str], limit: int = 10) -> List[SearchResult]:
        """Search for laws on casenote.kr."""
        if not keywords:
            return []

        # Combine keywords into search query
        query = " ".join(keywords[:3])  # Limit to first 3 keywords
        encoded_query = urllib.parse.quote(query)
        url = f"{self.LAW_SEARCH_URL}?q={encoded_query}"

        try:
            logger.info(f"Searching laws on casenote.kr: {query}")
            response = await self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_law_results(soup, query, url, limit)

            logger.info(f"Found {len(results)} law results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error searching laws on casenote.kr: {e}")
            return []

    async def search_precedents(self, keywords: List[str], limit: int = 10) -> List[SearchResult]:
        """Search for precedents on casenote.kr."""
        if not keywords:
            return []

        # Combine keywords into search query
        query = " ".join(keywords[:3])  # Limit to first 3 keywords
        encoded_query = urllib.parse.quote(query)
        url = f"{self.PRECEDENT_SEARCH_URL}?q={encoded_query}"

        try:
            logger.info(f"Searching precedents on casenote.kr: {query}")
            response = await self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = self._parse_precedent_results(soup, query, url, limit)

            logger.info(f"Found {len(results)} precedent results for query: {query}")
            return results

        except Exception as e:
            logger.error(f"Error searching precedents on casenote.kr: {e}")
            return []

    def _parse_law_results(self, soup: BeautifulSoup, query: str, search_url: str, limit: int) -> List[SearchResult]:
        """Parse law search results from HTML."""
        results = []

        # Look for common result containers
        result_selectors = [
            '.search-result',
            '.law-result',
            '.result-item',
            'article',
            '.card',
            'li'
        ]

        result_elements = []
        for selector in result_selectors:
            elements = soup.select(selector)
            if elements:
                result_elements = elements[:limit]
                break

        if not result_elements:
            # Fallback: look for any elements with links
            result_elements = soup.find_all('a', href=True)[:limit]

        for idx, element in enumerate(result_elements):
            try:
                result = self._extract_law_result(element, query, search_url, idx)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Error parsing law result element: {e}")
                continue

        return results[:limit]

    def _parse_precedent_results(self, soup: BeautifulSoup, query: str, search_url: str, limit: int) -> List[SearchResult]:
        """Parse precedent search results from HTML."""
        results = []

        # Look for common result containers
        result_selectors = [
            '.search-result',
            '.precedent-result',
            '.case-result',
            '.result-item',
            'article',
            '.card',
            'li'
        ]

        result_elements = []
        for selector in result_selectors:
            elements = soup.select(selector)
            if elements:
                result_elements = elements[:limit]
                break

        if not result_elements:
            # Fallback: look for any elements with links
            result_elements = soup.find_all('a', href=True)[:limit]

        for idx, element in enumerate(result_elements):
            try:
                result = self._extract_precedent_result(element, query, search_url, idx)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Error parsing precedent result element: {e}")
                continue

        return results[:limit]

    def _extract_law_result(self, element, query: str, search_url: str, index: int) -> Optional[SearchResult]:
        """Extract law result information from HTML element."""
        try:
            # Extract title
            title_element = (
                element.find('h1') or element.find('h2') or
                element.find('h3') or element.find('h4') or
                element.find('a') or element
            )
            title = title_element.get_text(strip=True) if title_element else f"법령 결과 {index + 1}"

            # Extract content/snippet
            content_element = element.find('p') or element
            content = content_element.get_text(strip=True)
            if len(content) > 300:
                content = content[:297] + "..."

            # Extract URL
            link_element = element.find('a', href=True)
            url = link_element['href'] if link_element else search_url
            if url.startswith('/'):
                url = "https://casenote.kr" + url

            # Calculate relevance score based on keyword matches
            relevance_score = self._calculate_relevance(title + " " + content, query)

            source = SearchSource(
                url=url,
                title=title,
                source_type=SourceType.EXTERNAL_LAW,
                confidence=0.7,  # Medium confidence for external sources
                date=datetime.now(),
                excerpt=content[:150] + "..." if len(content) > 150 else content
            )

            return SearchResult(
                title=title,
                content=content,
                source=source,
                relevance_score=relevance_score,
                keywords_matched=self._find_matched_keywords(title + " " + content, query)
            )

        except Exception as e:
            logger.warning(f"Error extracting law result: {e}")
            return None

    def _extract_precedent_result(self, element, query: str, search_url: str, index: int) -> Optional[SearchResult]:
        """Extract precedent result information from HTML element."""
        try:
            # Extract title
            title_element = (
                element.find('h1') or element.find('h2') or
                element.find('h3') or element.find('h4') or
                element.find('a') or element
            )
            title = title_element.get_text(strip=True) if title_element else f"판례 결과 {index + 1}"

            # Extract content/snippet
            content_element = element.find('p') or element
            content = content_element.get_text(strip=True)
            if len(content) > 300:
                content = content[:297] + "..."

            # Extract URL
            link_element = element.find('a', href=True)
            url = link_element['href'] if link_element else search_url
            if url.startswith('/'):
                url = "https://casenote.kr" + url

            # Calculate relevance score
            relevance_score = self._calculate_relevance(title + " " + content, query)

            source = SearchSource(
                url=url,
                title=title,
                source_type=SourceType.EXTERNAL_PRECEDENT,
                confidence=0.7,  # Medium confidence for external sources
                date=datetime.now(),
                excerpt=content[:150] + "..." if len(content) > 150 else content
            )

            return SearchResult(
                title=title,
                content=content,
                source=source,
                relevance_score=relevance_score,
                keywords_matched=self._find_matched_keywords(title + " " + content, query)
            )

        except Exception as e:
            logger.warning(f"Error extracting precedent result: {e}")
            return None

    def _calculate_relevance(self, text: str, query: str) -> float:
        """Calculate relevance score based on keyword matches."""
        text_lower = text.lower()
        query_words = query.split()

        matches = 0
        for word in query_words:
            if word.lower() in text_lower:
                matches += 1

        if not query_words:
            return 0.0

        return min(matches / len(query_words), 1.0)

    def _find_matched_keywords(self, text: str, query: str) -> List[str]:
        """Find which keywords from the query match the text."""
        text_lower = text.lower()
        query_words = query.split()

        matched = []
        for word in query_words:
            if word.lower() in text_lower:
                matched.append(word)

        return matched


class ExternalSearcher:
    """Coordinator for external search services."""

    def __init__(self):
        self.casenote = CasenoteSearcher()

    async def close(self):
        """Close all external search connections."""
        await self.casenote.close()

    async def search(self, keywords: List[str], intent: QueryIntent, limit: int = 10) -> List[SearchResult]:
        """Search external sources based on intent."""
        results = []

        try:
            if intent in [QueryIntent.LAW_SEARCH, QueryIntent.LEGAL_INTERPRETATION]:
                law_results = await self.casenote.search_laws(keywords, limit // 2)
                results.extend(law_results)

            if intent in [QueryIntent.PRECEDENT_SEARCH, QueryIntent.LEGAL_INTERPRETATION]:
                precedent_results = await self.casenote.search_precedents(keywords, limit // 2)
                results.extend(precedent_results)

            # For general inquiries, search both
            if intent == QueryIntent.GENERAL_INQUIRY:
                law_results = await self.casenote.search_laws(keywords, limit // 2)
                precedent_results = await self.casenote.search_precedents(keywords, limit // 2)
                results.extend(law_results)
                results.extend(precedent_results)

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:limit]

        except Exception as e:
            logger.error(f"Error in external search: {e}")
            return []