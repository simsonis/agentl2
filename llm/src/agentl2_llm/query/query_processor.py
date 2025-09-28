"""
Main query processing orchestrator.
"""

from __future__ import annotations

from .intent_classifier import IntentClassifier
from .keyword_extractor import KeywordExtractor
from ..models import LegalQuery


class QueryProcessor:
    """Orchestrates query analysis and processing."""

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.keyword_extractor = KeywordExtractor()

    async def process(self, query_text: str) -> LegalQuery:
        """Process a legal query and return structured analysis."""
        # Classify intent and extract basic keywords
        legal_query = await self.intent_classifier.classify(query_text)

        # Enhanced keyword extraction
        enhanced_keywords = await self.keyword_extractor.extract(query_text)

        # Extract legal entities
        legal_entities_dict = self.keyword_extractor.extract_legal_entities(query_text)

        # Merge all legal entities into a single list
        all_entities = []
        for entity_type, entities in legal_entities_dict.items():
            all_entities.extend(entities)

        # Update the legal query with enhanced information
        legal_query.keywords = enhanced_keywords
        legal_query.legal_entities = list(set(all_entities))  # Remove duplicates

        return legal_query