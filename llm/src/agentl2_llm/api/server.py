"""
FastAPI server for Enhanced Agent Pipeline.
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from loguru import logger

from ..pipeline.enhanced_agent_pipeline import EnhancedAgentPipeline
from ..models import LegalResponse


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    conversation_id: Optional[str] = None


class ChatStreamResponse(BaseModel):
    type: str  # "agent_step", "content", "complete"
    agent: str = None
    step: str = None
    content: str = None
    final_response: Dict[str, Any] = None


class AgentConfig(BaseModel):
    name: str
    role: str
    model: str
    systemPrompt: str
    temperature: float
    maxTokens: int
    topP: float = 1.0
    frequencyPenalty: float = 0.0
    presencePenalty: float = 0.0


class AgentConfigurations(BaseModel):
    facilitator: AgentConfig
    search: AgentConfig
    analyst: AgentConfig
    response: AgentConfig
    citation: AgentConfig
    validator: AgentConfig


class GlobalSettings(BaseModel):
    defaultModel: str
    maxRetries: int
    timeout: int
    enableLogging: bool


app = FastAPI(title="AgentL2 LLM Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline: EnhancedAgentPipeline = None

# Configuration file path
CONFIG_DIR = Path("./config")
AGENT_CONFIG_FILE = CONFIG_DIR / "agent_configs.json"
GLOBAL_CONFIG_FILE = CONFIG_DIR / "global_settings.json"

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)


def serialize_legal_response(response: LegalResponse) -> Dict[str, Any]:
    """Serialize LegalResponse for streaming clients."""
    return {
        "answer": response.answer,
        "sources": [
            {
                "source_name": source.title,
                "description": source.excerpt,
                "link": source.url,
                "source_type": source.source_type.value
                if hasattr(source.source_type, "value")
                else str(source.source_type),
                "confidence": source.confidence,
            }
            for source in response.sources
        ],
        "followUps": response.follow_up_questions,
        "confidence": response.confidence,
        "processing_time": response.processing_time,
        "related_keywords": response.related_keywords,
    }


def chunk_response_text(text_value: str) -> List[str]:
    """Split long answer text into smaller streaming chunks."""
    if not text_value:
        return []

    parts = text_value.split('. ')
    chunks: List[str] = []
    for index, part in enumerate(parts):
        clean = part.strip()
        if not clean:
            continue
        suffix = '. ' if index < len(parts) - 1 else ''
        chunks.append(clean + suffix)
    return chunks


@app.on_event("startup")
async def startup_event():
    """Initialize the agent pipeline on startup."""
    global pipeline
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        try:
            pipeline = EnhancedAgentPipeline(
                openai_api_key=openai_api_key,
                openai_model="gpt-4",
                temperature=0.3
            )
            logger.info("Enhanced Agent Pipeline initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize pipeline: {e}")
            pipeline = None
    else:
        logger.warning("OPENAI_API_KEY not set - pipeline will be unavailable")
        pipeline = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global pipeline
    if pipeline:
        await pipeline.close()
        logger.info("Enhanced Agent Pipeline closed")


async def process_with_streaming(
    user_message: str,
    conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Process message through agent pipeline with streaming updates."""

    if not pipeline:
        raise RuntimeError("Agent pipeline not initialized")

    event_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

    async def event_handler(agent: str, payload: Dict[str, Any]) -> None:
        await event_queue.put(
            {
                "type": "agent_step",
                "agent": agent,
                "payload": payload,
            }
        )

    async def runner() -> None:
        try:
            response: LegalResponse = await pipeline.process_message(
                user_message,
                conversation_id,
                event_handler=event_handler,
            )

            for chunk in chunk_response_text(response.answer):
                await event_queue.put(
                    {
                        "type": "content",
                        "content": chunk,
                    }
                )

            await event_queue.put(
                {
                    "type": "complete",
                    "final_response": serialize_legal_response(response),
                }
            )
        except Exception as exc:
            logger.error(f"Error in streaming process: {exc}")
            await event_queue.put({"type": "error", "error": str(exc)})
        finally:
            await event_queue.put({"type": "_sentinel"})

    worker = asyncio.create_task(runner())

    try:
        while True:
            event = await event_queue.get()
            if event.get("type") == "_sentinel":
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
    finally:
        await worker

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response through enhanced agent pipeline."""

    if not pipeline:
        raise HTTPException(status_code=500, detail="Agent pipeline not initialized")

    # Extract user message from messages
    user_message = ""
    for message in reversed(request.messages):
        if message.get("role") == "user":
            user_message = message.get("content", "")
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    return StreamingResponse(
        process_with_streaming(user_message, request.conversation_id),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@app.post("/chat")
async def chat(request: ChatRequest):
    """Process chat message through enhanced agent pipeline."""

    if not pipeline:
        raise HTTPException(status_code=500, detail="Agent pipeline not initialized")

    # Extract user message from messages
    user_message = ""
    for message in reversed(request.messages):
        if message.get("role") == "user":
            user_message = message.get("content", "")
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    try:
        response: LegalResponse = await pipeline.process_message(user_message, request.conversation_id)

        return {
            "answer": response.answer,
            "sources": [
                {
                    "source_name": source.title,
                    "description": source.excerpt,
                    "link": source.url
                } for source in response.sources
            ],
            "followUps": response.follow_up_questions,
            "confidence": response.confidence,
            "processing_time": response.processing_time
        }

    except Exception as e:
        logger.error(f"Error processing chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status = "healthy" if pipeline else "unhealthy"

    pipeline_status = None
    if pipeline:
        try:
            pipeline_status = await pipeline.get_pipeline_status()
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            status = "degraded"

    return {
        "status": status,
        "pipeline": pipeline_status
    }


def load_default_agent_configs() -> Dict[str, Any]:
    """Load default agent configurations."""
    return {
        "facilitator": {
            "name": "전달자(Facilitator)",
            "role": "의도파악/키워드추출",
            "model": "gpt-4",
            "systemPrompt": """당신은 사용자의 법률 질문을 분석하여 핵심 키워드를 추출하고 법적 의도를 파악하는 전문가입니다.

주요 역할:
1. 사용자 질문에서 핵심 법률 용어와 키워드를 추출
2. 질문의 법적 의도 분류 (법령 검색, 판례 분석, 해석 요청)
3. 다음 단계 에이전트가 사용할 수 있는 구조화된 정보 생성

응답 형식은 간결하고 명확하게 작성하세요.""",
            "temperature": 0.3,
            "maxTokens": 1000,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "search": {
            "name": "검색자 (Search)",
            "role": "다중라운드검색",
            "model": "gpt-4",
            "systemPrompt": """당신은 법령 및 판례 검색을 수행하는 전문가입니다.

주요 역할:
1. 키워드를 바탕으로 관련 법령 검색
2. 판례 및 해석례 검색
3. 내부 DB와 외부 리소스를 활용한 다중 검색
4. 검색 결과의 관련성 및 우선순위 결정

정확하고 포괄적인 검색 결과를 제공하세요.""",
            "temperature": 0.2,
            "maxTokens": 1200,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "analyst": {
            "name": "분석가 (Analyst)",
            "role": "법적분석/쟁점식별",
            "model": "gpt-4",
            "systemPrompt": """당신은 법적 쟁점을 식별하고 분석하는 전문가입니다.

주요 역할:
1. 검색된 법령 및 판례를 바탕으로 법적 쟁점 식별
2. 적용 가능한 법리와 원칙 분석
3. 사안의 복잡도와 중요도 평가
4. 잠재적 법적 위험 요소 파악

논리적이고 체계적인 분석을 제공하세요.""",
            "temperature": 0.4,
            "maxTokens": 1500,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "response": {
            "name": "응답자(Response)",
            "role": "답변내용생성",
            "model": "gpt-4",
            "systemPrompt": """당신은 법적 분석을 바탕으로 사용자에게 명확한 답변을 제공하는 전문가입니다.

주요 역할:
1. 분석 결과를 바탕으로 구체적이고 실용적인 답변 작성
2. 법적 근거를 명시하며 이해하기 쉽게 설명
3. 사용자의 상황에 맞는 조치 사항 제안
4. 추가 고려사항이나 주의점 안내

명확하고 이해하기 쉬운 언어로 답변하세요.""",
            "temperature": 0.5,
            "maxTokens": 2000,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "citation": {
            "name": "인용자(Citation)",
            "role": "인용/출처관리",
            "model": "gpt-4",
            "systemPrompt": """당신은 법률 답변의 인용과 출처를 관리하는 전문가입니다.

주요 역할:
1. 참조한 법령의 정확한 조문 및 출처 관리
2. 인용한 판례의 사건번호 및 날짜 관리
3. 출처 자료의 신뢰성 검증
4. 법적 근거의 계층과 구조화

정확하고 체계적인 인용 형식을 유지하세요.""",
            "temperature": 0.1,
            "maxTokens": 800,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "validator": {
            "name": "검증자 (Validator)",
            "role": "종합검증/품질관리",
            "model": "gpt-4",
            "systemPrompt": """당신은 최종 답변의 정확성과 품질을 검증하는 전문가입니다.

주요 역할:
1. 답변 내용의 법적 정확성 검증
2. 논리적 일관성과 완결성 평가
3. 인용 출처의 정확성 확인
4. 사용자에게 도움이 되는지 최종 평가

높은 품질 기준을 유지하며 객관적으로 검증하세요.""",
            "temperature": 0.2,
            "maxTokens": 1000,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        }
    }


def load_default_global_settings() -> Dict[str, Any]:
    """Load default global settings."""
    return {
        "defaultModel": "gpt-4",
        "maxRetries": 3,
        "timeout": 30,
        "enableLogging": True
    }


@app.get("/admin/agent-configs")
async def get_agent_configs():
    """Get current agent configurations."""
    try:
        if AGENT_CONFIG_FILE.exists():
            with open(AGENT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                configs = json.load(f)
        else:
            configs = load_default_agent_configs()

        return {"success": True, "data": configs}
    except Exception as e:
        logger.error(f"Error loading agent configs: {e}")
        return {"success": False, "error": str(e), "data": load_default_agent_configs()}


@app.post("/admin/agent-configs")
async def save_agent_configs(configs: Dict[str, Any]):
    """Save agent configurations."""
    try:
        with open(AGENT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)

        logger.info("Agent configurations saved successfully")
        return {"success": True, "message": "설정이 성공적으로 저장되었습니다."}
    except Exception as e:
        logger.error(f"Error saving agent configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/global-settings")
async def get_global_settings():
    """Get current global settings."""
    try:
        if GLOBAL_CONFIG_FILE.exists():
            with open(GLOBAL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        else:
            settings = load_default_global_settings()

        return {"success": True, "data": settings}
    except Exception as e:
        logger.error(f"Error loading global settings: {e}")
        return {"success": False, "error": str(e), "data": load_default_global_settings()}


@app.post("/admin/global-settings")
async def save_global_settings(settings: Dict[str, Any]):
    """Save global settings."""
    try:
        with open(GLOBAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        logger.info("Global settings saved successfully")
        return {"success": True, "message": "글로벌 설정이 성공적으로 저장되었습니다."}
    except Exception as e:
        logger.error(f"Error saving global settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/reset-to-defaults")
async def reset_to_defaults():
    """Reset all configurations to default values."""
    try:
        # Save default configs
        default_agent_configs = load_default_agent_configs()
        default_global_settings = load_default_global_settings()

        with open(AGENT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_agent_configs, f, indent=2, ensure_ascii=False)

        with open(GLOBAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_global_settings, f, indent=2, ensure_ascii=False)

        logger.info("Configurations reset to defaults")
        return {
            "success": True,
            "message": "모든 설정이 기본값으로 초기화되었습니다.",
            "data": {
                "agentConfigs": default_agent_configs,
                "globalSettings": default_global_settings
            }
        }
    except Exception as e:
        logger.error(f"Error resetting to defaults: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
