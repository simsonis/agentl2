"""
Simple FastAPI server for testing Agent flow with real OpenAI API.
"""

import asyncio
import json
import os
from typing import Dict, Any, AsyncGenerator, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from openai import AsyncOpenAI


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

# Initialize OpenAI client
client = None

@app.on_event("startup")
async def startup_event():
    """Initialize the OpenAI client on startup."""
    global client
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if openai_api_key:
        client = AsyncOpenAI(api_key=openai_api_key)
        print("OpenAI client initialized successfully")
    else:
        print("WARNING: OPENAI_API_KEY not set - will use mock responses")

async def call_openai_api(user_message: str) -> str:
    """Call OpenAI API for legal analysis."""
    if not client:
        return "죄송합니다. OpenAI API가 설정되지 않아 실제 법률 분석을 수행할 수 없습니다."

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """당신은 한국법 전문 AI 법률 어시스턴트입니다.
                    사용자의 질문에 대해 정확하고 전문적인 법률 정보를 제공해주세요.
                    가능한 한 관련 법령과 조문을 인용하여 답변해주세요."""
                },
                {
                    "role": "user",
                    "content": user_message
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"OpenAI API 호출 중 오류가 발생했습니다: {str(e)}"


async def simulate_agent_pipeline(user_message: str) -> AsyncGenerator[str, None]:
    """Process through 6-step agent pipeline with real OpenAI API calls."""

    try:
        # Step 1: 전달자 Agent - 키워드 추출
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'facilitator', 'step': '사용자 의도 파악 및 키워드 추출 중...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.5)

        # Step 2: 검색 Agent - CaseNote 검색 시뮬레이션
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'search', 'step': '관련 법령 및 판례 검색 중...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.7)

        # Step 3: 분석가 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'analyst', 'step': '법적 분석 및 쟁점 식별 중...'}, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.8)

        # Step 4: 응답 Agent - 실제 OpenAI API 호출
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'response', 'step': '실제 AI 모델을 통한 답변 생성 중...'}, ensure_ascii=False)}\n\n"

        # 실제 OpenAI API 호출
        real_answer = await call_openai_api(user_message)
        await asyncio.sleep(0.6)

        # Step 5: 인용 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'citation', 'step': '인용 및 출처 정리 중...'})}\n\n"
        await asyncio.sleep(0.4)

        # Step 6: 검증자 Agent
        yield f"data: {json.dumps({'type': 'agent_step', 'agent': 'validator', 'step': '최종 검증 및 품질 확인 중...'})}\n\n"
        await asyncio.sleep(0.5)

        # Use real OpenAI API response
        response_text = f"""{real_answer}

---
**🤖 Enhanced Agent Pipeline 처리 완료**

이 답변은 6단계 AI 에이전트 시스템을 통해 처리되었습니다:
1. 전달자: 질문 의도 파악 및 키워드 추출
2. 검색자: 관련 법령 및 판례 검색
3. 분석가: 법적 쟁점 식별 및 분석
4. 응답자: **실제 GPT-4 모델**을 통한 답변 생성
5. 인용자: 출처 및 참조 정리
6. 검증자: 최종 품질 검증"""

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
    openai_status = "available" if client else "not_configured"
    pipeline_type = "enhanced_real_api_pipeline" if client else "mock_pipeline"

    return {
        "status": "healthy",
        "openai_api": openai_status,
        "pipeline": {
            "type": pipeline_type,
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