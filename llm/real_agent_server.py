"""
Real Agent Server with Enhanced Pipeline and Admin APIs.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, AsyncGenerator, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn

# Load environment variables from .env file
load_dotenv(Path(__file__).parent.parent / ".env")

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentl2_llm.pipeline.enhanced_agent_pipeline import EnhancedAgentPipeline
from agentl2_llm.models import LegalResponse


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    conversation_id: Optional[str] = None


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
pipeline: Optional[EnhancedAgentPipeline] = None

# Configuration files
CONFIG_DIR = Path("./config")
AGENT_CONFIG_FILE = CONFIG_DIR / "agent_configs.json"
GLOBAL_CONFIG_FILE = CONFIG_DIR / "global_settings.json"

# Ensure config directory exists
CONFIG_DIR.mkdir(exist_ok=True)


@app.on_event("startup")
async def startup_event():
    """Initialize the enhanced agent pipeline on startup."""
    global pipeline
    # Use a dummy API key for testing - in production, use real OPENAI_API_KEY
    openai_api_key = os.getenv("OPENAI_API_KEY", "sk-test-dummy-key-for-development")
    try:
        pipeline = EnhancedAgentPipeline(
            openai_api_key=openai_api_key,
            openai_model="gpt-4",
            temperature=0.3
        )
        print("Enhanced Agent Pipeline initialized")
    except Exception as e:
        print(f"Failed to initialize pipeline: {e}")
        pipeline = None


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global pipeline
    if pipeline:
        await pipeline.close()
        print("Enhanced Agent Pipeline closed")


def load_agent_configs() -> Dict[str, Any]:
    """Load agent configurations from file or defaults."""
    if AGENT_CONFIG_FILE.exists():
        try:
            with open(AGENT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading agent configs: {e}")

    # Return default configs
    return {
        "facilitator": {
            "name": "전달자 (Facilitator)",
            "role": "의도파악/키워드추출",
            "model": "gpt-4",
            "systemPrompt": """당신은 사용자의 법률 질문을 분석하여 핵심 키워드를 추출하고 법적 의도를 파악하는 전문가입니다.

주요 역할:
1. 사용자 질문에서 핵심 법률 용어와 키워드 추출
2. 질문의 법적 의도 분류 (법령 검색, 판례 분석, 해석 등)
3. 다음 단계 에이전트가 활용할 수 있는 구조화된 정보 생성

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
2. 유사 판례 및 해석례 검색
3. 내부 DB와 외부 소스를 활용한 다중 검색
4. 검색 결과의 관련성 평가 및 우선순위 결정

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
1. 검색된 법령과 판례를 바탕으로 법적 쟁점 식별
2. 적용 가능한 법리와 원칙 분석
3. 사안의 복잡성과 중요도 평가
4. 잠재적 법적 위험 요소 파악

논리적이고 체계적인 분석을 제공하세요.""",
            "temperature": 0.4,
            "maxTokens": 1500,
            "topP": 1.0,
            "frequencyPenalty": 0.0,
            "presencePenalty": 0.0
        },
        "response": {
            "name": "응답자 (Response)",
            "role": "답변내용생성",
            "model": "gpt-4",
            "systemPrompt": """당신은 법적 분석을 바탕으로 사용자에게 명확한 답변을 제공하는 전문가입니다.

주요 역할:
1. 분석 결과를 바탕으로 구체적이고 실용적인 답변 생성
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
            "name": "인용자 (Citation)",
            "role": "인용/출처관리",
            "model": "gpt-4",
            "systemPrompt": """당신은 법률 답변의 인용과 출처를 정리하는 전문가입니다.

주요 역할:
1. 참조된 법령의 정확한 조문 및 출처 정리
2. 인용된 판례의 사건번호 및 요지 정리
3. 외부 자료의 신뢰성 검증
4. 법적 근거의 계층적 구조화

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
2. 논리적 일관성 및 완성도 평가
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


def load_global_settings() -> Dict[str, Any]:
    """Load global settings from file or defaults."""
    if GLOBAL_CONFIG_FILE.exists():
        try:
            with open(GLOBAL_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading global settings: {e}")

    # Return default settings
    return {
        "defaultModel": "gpt-4",
        "maxRetries": 3,
        "timeout": 30,
        "enableLogging": True
    }


async def process_with_streaming(
    user_message: str,
    conversation_id: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Process message through enhanced agent pipeline with streaming updates."""

    if not pipeline:
        yield f"data: {json.dumps({'type': 'error', 'error': 'Agent pipeline not initialized'})}\n\n"
        return

    event_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

    async def event_handler(agent: str, payload: Dict[str, Any]) -> None:
        await event_queue.put({
            "type": "agent_step",
            "agent": agent,
            "payload": payload,
        })

    async def runner() -> None:
        try:
            response: LegalResponse = await pipeline.process_message(
                user_message,
                conversation_id,
                event_handler=event_handler,
            )

            # Serialize the response
            serialized = {
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

            # Stream content in chunks
            content_parts = response.answer.split('. ')
            for i, part in enumerate(content_parts):
                if part.strip():
                    content = part + ('. ' if i < len(content_parts) - 1 else '')
                    await event_queue.put({
                        "type": "content",
                        "content": content,
                    })

            await event_queue.put({
                "type": "complete",
                "final_response": serialized,
            })
        except Exception as exc:
            print(f"Error in streaming process: {exc}")
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    status = "healthy" if pipeline else "unhealthy"

    pipeline_status = None
    if pipeline:
        try:
            pipeline_status = await pipeline.get_pipeline_status()
        except Exception as e:
            print(f"Error getting pipeline status: {e}")
            status = "degraded"

    return {
        "status": status,
        "openai_api": "available" if pipeline else "not_configured",
        "pipeline": pipeline_status
    }


# Admin API endpoints
@app.get("/admin/agent-configs")
async def get_agent_configs():
    """Get current agent configurations."""
    try:
        configs = load_agent_configs()
        return {"success": True, "data": configs}
    except Exception as e:
        print(f"Error loading agent configs: {e}")
        return {"success": False, "error": str(e), "data": load_agent_configs()}


@app.post("/admin/agent-configs")
async def save_agent_configs(configs: Dict[str, Any]):
    """Save agent configurations."""
    try:
        with open(AGENT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False)

        print("Agent configurations saved successfully")

        # TODO: Apply configs to running pipeline
        # This would require reloading the pipeline with new settings

        return {"success": True, "message": "설정이 성공적으로 저장되었습니다."}
    except Exception as e:
        print(f"Error saving agent configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/global-settings")
async def get_global_settings():
    """Get current global settings."""
    try:
        settings = load_global_settings()
        return {"success": True, "data": settings}
    except Exception as e:
        print(f"Error loading global settings: {e}")
        return {"success": False, "error": str(e), "data": load_global_settings()}


@app.post("/admin/global-settings")
async def save_global_settings(settings: Dict[str, Any]):
    """Save global settings."""
    try:
        with open(GLOBAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

        print("Global settings saved successfully")
        return {"success": True, "message": "글로벌 설정이 성공적으로 저장되었습니다."}
    except Exception as e:
        print(f"Error saving global settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/reset-to-defaults")
async def reset_to_defaults():
    """Reset all configurations to default values."""
    try:
        # Save default configs
        default_agent_configs = load_agent_configs()
        default_global_settings = load_global_settings()

        with open(AGENT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_agent_configs, f, indent=2, ensure_ascii=False)

        with open(GLOBAL_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_global_settings, f, indent=2, ensure_ascii=False)

        print("Configurations reset to defaults")
        return {
            "success": True,
            "message": "모든 설정이 기본값으로 초기화되었습니다.",
            "data": {
                "agentConfigs": default_agent_configs,
                "globalSettings": default_global_settings
            }
        }
    except Exception as e:
        print(f"Error resetting to defaults: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=False
    )