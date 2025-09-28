"""
FastAPI server for Enhanced Agent Pipeline.
"""

import asyncio
import json
from typing import Dict, Any, AsyncGenerator, List

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
    conversation_id: str = None


class ChatStreamResponse(BaseModel):
    type: str  # "agent_step", "content", "complete"
    agent: str = None
    step: str = None
    content: str = None
    final_response: Dict[str, Any] = None


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


@app.on_event("startup")
async def startup_event():
    """Initialize the agent pipeline on startup."""
    global pipeline
    import os

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise RuntimeError("OPENAI_API_KEY environment variable is required")

    pipeline = EnhancedAgentPipeline(
        openai_api_key=openai_api_key,
        openai_model="gpt-4",
        temperature=0.3
    )
    logger.info("Enhanced Agent Pipeline initialized")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    global pipeline
    if pipeline:
        await pipeline.close()
        logger.info("Enhanced Agent Pipeline closed")


async def process_with_streaming(user_message: str, conversation_id: str = None) -> AsyncGenerator[str, None]:
    """Process message through agent pipeline with streaming updates."""

    try:
        # Start processing
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'facilitator', 'step': '의도 파악 및 키워드 추출 중...'})}\n\n"
        await asyncio.sleep(0.1)  # Small delay for UI feedback

        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'search', 'step': '관련 법령 및 판례 검색 중...'})}\n\n"
        await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'analyst', 'step': '법적 분석 및 쟁점 식별 중...'})}\n\n"
        await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'response', 'step': '답변 내용 생성 중...'})}\n\n"
        await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'citation', 'step': '인용 및 출처 정리 중...'})}\n\n"
        await asyncio.sleep(0.1)

        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'validator', 'step': '최종 검증 및 품질 확인 중...'})}\n\n"
        await asyncio.sleep(0.1)

        # Process through pipeline
        response: LegalResponse = await pipeline.process_message(user_message, conversation_id)

        # Stream the final response content
        content_chunks = response.answer.split('. ')
        for i, chunk in enumerate(content_chunks):
            if chunk.strip():
                content = chunk + ('. ' if i < len(content_chunks) - 1 else '')
                yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                await asyncio.sleep(0.05)  # Simulate streaming

        # Send final complete response
        final_data = {
            'type': 'complete',
            'final_response': {
                'answer': response.answer,
                'sources': [
                    {
                        'source_name': source.title,
                        'description': source.excerpt,
                        'link': source.url
                    } for source in response.sources
                ],
                'followUps': response.follow_up_questions,
                'confidence': response.confidence,
                'processing_time': response.processing_time
            }
        }
        yield f"data: {json.dumps(final_data)}\n\n"

    except Exception as e:
        logger.error(f"Error in streaming process: {e}")
        error_data = {
            'type': 'error',
            'error': str(e)
        }
        yield f"data: {json.dumps(error_data)}\n\n"


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


if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )