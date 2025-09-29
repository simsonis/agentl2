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
            "name": "?달??(Facilitator)",
            "role": "?도?악/?워?추?",
            "model": "gpt-4",
            "systemPrompt": """?신? ?용?의 법률 질문??분석?여 ?심 ?워?? 추출?고 법적 ?도??악?는 ?문가?니??

주요 ??:
1. ?용??질문?서 ?심 법률 ?어? ?워??추출
2. 질문??법적 ?도 분류 (법령 검?? ?? 분석, ?석 ??
3. ?음 ?계 ?이?트가 ?용?????는 구조?된 ?보 ?성

?답 ?식? 간결?고 명확?게 ?성?세??""",
            "temperature": 0.3,
            "maxTokens": 1000,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "search": {
            "name": "검?자 (Search)",
            "role": "?중?운????",
            "model": "gpt-4",
            "systemPrompt": """?신? 법령 ??? 검?을 ?행?는 ?문가?니??

주요 ??:
1. ?워?? 바탕?로 관??법령 검??
2. ?사 ?? ??석례 검??
3. ?? DB? ?? ?스??용???중 검??
4. 검??결과??관?성 ?? ??선?위 결정

?확?고 ?괄?인 검??결과??공?세??""",
            "temperature": 0.2,
            "maxTokens": 1200,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "analyst": {
            "name": "분석가 (Analyst)",
            "role": "법적분석/?점?별",
            "model": "gpt-4",
            "systemPrompt": """?신? 법적 ?점???별?고 분석?는 ?문가?니??

주요 ??:
1. 검?된 법령????바탕?로 법적 ?점 ?별
2. ?용 가?한 법리? ?칙 분석
3. ?안??복잡?과 중요????
4. ?재??법적 ?험 ?소 ?악

?리?이?체계?인 분석???공?세??""",
            "temperature": 0.4,
            "maxTokens": 1500,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "response": {
            "name": "?답??(Response)",
            "role": "???용?성",
            "model": "gpt-4",
            "systemPrompt": """?신? 법적 분석??바탕?로 ?용?에?명확???????공?는 ?문가?니??

주요 ??:
1. 분석 결과?바탕?로 구체?이??용?인 ?? ?성
2. 법적 근거?명시?며 ?해?기 ?게 ?명
3. ?용?의 ?황??맞는 조치 ?항 ?안
4. 추? 고려?항?나 주의???내

명확?고 ?해?기 ?운 ?어????세??""",
            "temperature": 0.5,
            "maxTokens": 2000,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "citation": {
            "name": "?용??(Citation)",
            "role": "?용/출처관?",
            "model": "gpt-4",
            "systemPrompt": """?신? 법률 ?????용?출처??리?는 ?문가?니??

주요 ??:
1. 참조??법령???확??조문 ?출처 ?리
2. ?용???????건번호 ??? ?리
3. ?? ?료???뢰??검?
4. 법적 근거??계층??구조??

?확?고 체계?인 ?용 ?식?????세??""",
            "temperature": 0.1,
            "maxTokens": 800,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "validator": {
            "name": "검증자 (Validator)",
            "role": "종합검??질관?",
            "model": "gpt-4",
            "systemPrompt": """?신? 최종 ?????확?과 ?질??검증하???문가?니??

주요 ??:
1. ?? ?용??법적 ?확??검?
2. ?리????????성????
3. ?용 출처???확???인
4. ?용?에??????는지 최종 ??

?? ?질 기??????며 객??으?검증하?요.""",
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
        return {"success": True, "message": "?정???공?으???되?습?다."}
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
        return {"success": True, "message": "글로벌 ?정???공?으???되?습?다."}
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
            "message": "모든 ?정??기본값으?초기?되?습?다.",
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
