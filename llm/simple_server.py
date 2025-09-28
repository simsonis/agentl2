"""
Simple FastAPI server for testing Agent flow.
"""

import asyncio
import json
from typing import Dict, Any, AsyncGenerator, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    conversation_id: str = None


app = FastAPI(title="AgentL2 LLM Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def simulate_agent_pipeline(user_message: str) -> AsyncGenerator[str, None]:
    """Simulate the 6-step agent pipeline with streaming updates."""

    try:
        # Step 1: 전달자 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'facilitator', 'step': '사용자 의도 파악 및 키워드 추출 중...'})}\n\n"
        await asyncio.sleep(0.5)

        # Step 2: 검색 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'search', 'step': '관련 법령 및 판례 검색 중...'})}\n\n"
        await asyncio.sleep(0.7)

        # Step 3: 분석가 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'analyst', 'step': '법적 분석 및 쟁점 식별 중...'})}\n\n"
        await asyncio.sleep(0.8)

        # Step 4: 응답 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'response', 'step': '답변 내용 생성 중...'})}\n\n"
        await asyncio.sleep(0.6)

        # Step 5: 인용 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'citation', 'step': '인용 및 출처 정리 중...'})}\n\n"
        await asyncio.sleep(0.4)

        # Step 6: 검증자 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'validator', 'step': '최종 검증 및 품질 확인 중...'})}\n\n"
        await asyncio.sleep(0.5)

        # Generate simulated response based on user message
        response_text = f"""'{user_message}'에 대한 답변입니다.

🔍 **Agent 체인 분석 결과:**

**1단계 (전달자)**: 사용자의 질문에서 핵심 키워드를 추출하고 법적 의도를 파악했습니다.

**2단계 (검색)**: 관련 법령, 판례, 해석례를 다중 소스에서 검색했습니다.

**3단계 (분석가)**: 법적 쟁점을 식별하고 적용 가능한 법리를 분석했습니다.

**4단계 (응답)**: 분석 결과를 바탕으로 구체적이고 실용적인 답변을 생성했습니다.

**5단계 (인용)**: 참조된 법령과 판례의 출처를 정리했습니다.

**6단계 (검증자)**: 답변의 정확성과 완성도를 최종 확인했습니다.

이는 6단계 Agent 체인을 통해 처리된 고품질 법률 답변입니다."""

        # Stream the response content
        content_parts = response_text.split('. ')
        for i, part in enumerate(content_parts):
            if part.strip():
                content = part + ('. ' if i < len(content_parts) - 1 else '')
                yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"
                await asyncio.sleep(0.1)

        # Send final response with sources
        final_data = {
            'type': 'complete',
            'final_response': {
                'answer': response_text,
                'sources': [
                    {
                        'source_name': '개인정보보호법 제15조',
                        'description': 'Agent 체인에서 검색된 관련 법령',
                        'link': 'https://www.law.go.kr/LSW/lsInfoP.do?lsId=008032'
                    },
                    {
                        'source_name': '관련 판례 2022다12345',
                        'description': 'Agent 체인에서 분석된 참조 판례',
                        'link': '#'
                    }
                ],
                'followUps': [
                    '더 구체적인 상황에 대해 알려주세요',
                    '관련 법령의 시행령도 확인하고 싶습니다',
                    '비슷한 판례가 더 있는지 궁금합니다'
                ],
                'confidence': 0.87,
                'processing_time': 3.5
            }
        }
        yield f"data: {json.dumps(final_data)}\n\n"

    except Exception as e:
        error_data = {
            'type': 'error',
            'error': f'Agent 체인 처리 중 오류: {str(e)}'
        }
        yield f"data: {json.dumps(error_data)}\n\n"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """Stream chat response through simulated agent pipeline."""

    # Extract user message
    user_message = ""
    for message in reversed(request.messages):
        if message.get("role") == "user":
            user_message = message.get("content", "")
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    return StreamingResponse(
        simulate_agent_pipeline(user_message),
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
    return {
        "status": "healthy",
        "pipeline": {
            "type": "simulated_6_agent_pipeline",
            "status": "operational",
            "agents": {
                "facilitator": {"status": "operational", "role": "의도파악/키워드추출"},
                "search": {"status": "operational", "role": "다중라운드검색"},
                "analyst": {"status": "operational", "role": "법적분석/쟁점식별"},
                "response": {"status": "operational", "role": "답변내용생성"},
                "citation": {"status": "operational", "role": "인용/출처관리"},
                "validator": {"status": "operational", "role": "종합검증/품질관리"}
            }
        }
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )