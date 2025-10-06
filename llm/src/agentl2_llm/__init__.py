"""
agentl2_llm - LLM-based legal chatbot module

This module provides intelligent legal query processing through an agent-based
architecture for the agentl2 legal AI assistant.
"""

__version__ = "0.1.0"

# Agent-based pipeline (new approach)
# Legacy import removed - using EnhancedAgentPipeline instead
# from .pipeline.agent_pipeline import AgentPipeline, ConversationManager
from .agents.facilitator_agent import FacilitatorAgent
from .agents.search_agent import SearchAgent
from .agents.response_agent import ResponseAgent

# Legacy components (for compatibility)
from .pipeline.chatbot import LegalChatbot
from .search.search_coordinator import SearchCoordinator
from .response.response_generator import ResponseGenerator

__all__ = [
    # New agent-based system
    # "AgentPipeline",  # Legacy - removed
    # "ConversationManager",  # Legacy - removed
    "FacilitatorAgent",
    "SearchAgent",
    "ResponseAgent",
    # Legacy system
    "LegalChatbot",
    "SearchCoordinator",
    "ResponseGenerator",
]