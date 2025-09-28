"""
Basic tests for the LLM module.
"""

import pytest
from agentl2_llm.query.intent_classifier import IntentClassifier
from agentl2_llm.query.keyword_extractor import KeywordExtractor
from agentl2_llm.models import QueryIntent


@pytest.mark.asyncio
async def test_intent_classification():
    """Test intent classification."""
    classifier = IntentClassifier()

    # Test law search intent
    query = await classifier.classify("개인정보보호법 제15조 내용이 궁금합니다")
    assert query.intent == QueryIntent.LAW_SEARCH
    assert "개인정보보호법" in query.legal_entities

    # Test precedent search intent
    query = await classifier.classify("개인정보 관련 대법원 판례를 찾고 있습니다")
    assert query.intent == QueryIntent.PRECEDENT_SEARCH

    # Test legal interpretation intent
    query = await classifier.classify("이 조문의 의미를 해석해 주세요")
    assert query.intent == QueryIntent.LEGAL_INTERPRETATION


@pytest.mark.asyncio
async def test_keyword_extraction():
    """Test keyword extraction."""
    extractor = KeywordExtractor()

    keywords = await extractor.extract("가명정보 처리 시 개인정보보호법 적용 기준")

    assert "가명정보" in keywords
    assert "개인정보보호법" in keywords
    assert len(keywords) > 0


def test_legal_entity_extraction():
    """Test legal entity extraction."""
    extractor = KeywordExtractor()

    entities = extractor.extract_legal_entities("개인정보보호법 제15조와 대법원 2020다1234 판결")

    assert "개인정보보호법" in entities["laws"]
    assert "2020다1234" in entities["case_numbers"]