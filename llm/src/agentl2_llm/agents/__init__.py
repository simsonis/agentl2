"""Agent-based components for legal chatbot."""

from .base_agent import BaseAgent, AgentResponse
from .facilitator_agent import FacilitatorAgent
from .search_agent import SearchAgent
from .response_agent import ResponseAgent

__all__ = [
    "BaseAgent",
    "AgentResponse",
    "FacilitatorAgent",
    "SearchAgent",
    "ResponseAgent"
]