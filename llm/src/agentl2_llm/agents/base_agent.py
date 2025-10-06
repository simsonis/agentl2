"""
Base agent class for the legal chatbot system.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime

from pydantic import BaseModel, Field
import openai
from loguru import logger


class AgentAction(str, Enum):
    """Types of actions an agent can take."""
    CONTINUE_CONVERSATION = "continue_conversation"
    FORWARD_TO_SEARCH = "forward_to_search"
    FORWARD_TO_RESPONSE = "forward_to_response"
    REQUEST_CLARIFICATION = "request_clarification"
    COMPLETE = "complete"


class AgentResponse(BaseModel):
    """Response from an agent."""
    action: AgentAction
    message: Optional[str] = None
    intent: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    clarification_options: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class ConversationContext(BaseModel):
    """Context for agent conversations."""
    conversation_id: str
    user_messages: List[str] = Field(default_factory=list)
    agent_responses: List[AgentResponse] = Field(default_factory=list)
    extracted_intent: Optional[str] = None
    extracted_keywords: List[str] = Field(default_factory=list)
    session_metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents in the legal chatbot system."""

    def __init__(
        self,
        name: str,
        openai_client: openai.AsyncOpenAI,
        model: str = "gpt-4",
        temperature: float = 0.3
    ):
        self.name = name
        self.client = openai_client
        self.model = model
        self.temperature = temperature
        self.system_prompt = self._get_system_prompt()

    @abstractmethod
    def _get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass

    @abstractmethod
    async def process(
        self,
        user_input: str,
        context: ConversationContext
    ) -> AgentResponse:
        """Process user input and return agent response."""
        pass

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500
    ) -> str:
        """Call the LLM with messages."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=self.temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"LLM call failed for {self.name}: {e}")
            raise

    def _build_conversation_history(self, context: ConversationContext) -> List[Dict[str, str]]:
        """Build conversation history for LLM context."""
        messages = [{"role": "system", "content": self.system_prompt}]

        priority_context = self._build_priority_context_message(context)
        if priority_context:
            messages.append({"role": "system", "content": priority_context})

        # Add conversation history
        for i, (user_msg, agent_resp) in enumerate(
            zip(context.user_messages, context.agent_responses)
        ):
            messages.append({"role": "user", "content": user_msg})
            if agent_resp.message:
                messages.append({"role": "assistant", "content": agent_resp.message})


        return messages

    def _build_priority_context_message(self, context: ConversationContext) -> str:
        """Construct a high-priority context summary for the LLM."""
        priority_memory = context.session_metadata.get("priority_memory", {}) if context.session_metadata else {}

        intents = priority_memory.get("intents") or ([] if not context.extracted_intent else [context.extracted_intent])
        keywords = priority_memory.get("keywords") or context.extracted_keywords

        lines: List[str] = []
        if intents:
            lines.append(f"최신 의도: {intents[0]}")
            if len(intents) > 1:
                lines.append("보조 의도 후보: " + "; ".join(intents[1:3]))

        if keywords:
            lines.append("핵심 키워드: " + ", ".join(keywords[:6]))

        if not lines:
            return ""

        return "최근 대화 맥락 요약(반드시 참조):\n" + "\n".join(f"- {line}" for line in lines)


    def _parse_structured_response(self, llm_response: str) -> Dict[str, Any]:
        """Parse structured response from LLM."""
        result = {
            "intent": None,
            "keywords": [],
            "clarification_options": [],
            "confidence": 0.0
        }

        lines = llm_response.strip().split('\n')
        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse intent
            if line.startswith('1. intent'):
                try:
                    intent_part = line.split('=', 1)[1].strip()
                    result["intent"] = intent_part.strip('{}').strip()
                except:
                    pass

            # Parse keywords
            elif line.startswith('2. search keywords'):
                try:
                    keywords_part = line.split('=', 1)[1].strip()
                    # Extract keywords from {a,b,c,...} format
                    keywords_str = keywords_part.strip('{}').strip()
                    if keywords_str:
                        keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                        result["keywords"] = keywords
                except:
                    pass

            # Parse clarification options
            elif line.startswith('3.') or line.startswith('3(option)'):
                try:
                    option_part = line.split('=', 1)[1].strip() if '=' in line else line
                    option_text = option_part.strip('{}').strip()
                    if option_text:
                        result["clarification_options"].append(option_text)
                except:
                    pass

        # Set confidence based on completeness
        if result["intent"] and result["keywords"]:
            result["confidence"] = 0.9
        elif result["intent"] or result["keywords"]:
            result["confidence"] = 0.6
        else:
            result["confidence"] = 0.3

        return result