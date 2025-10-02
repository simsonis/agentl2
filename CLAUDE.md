# AgentL2 Development Guide

## 🔧 공식 포트 설정

**절대 변경하지 마세요! 이 포트들은 고정입니다:**

- **UI Server (Next.js)**: `3000`
- **LLM Server (FastAPI)**: `8001`

## 📋 시작 명령어

### LLM 서버 시작
```bash
cd llm
python real_agent_server.py
```

### UI 서버 시작
```bash
cd ui
npm run dev -- --port 3000
```

## 🔍 상태 확인

### 포트 사용 확인
```bash
netstat -an | findstr ":3000\|:8001"
```

### 충돌 프로세스 정리
```bash
# Node.js 프로세스 종료
taskkill /F /im node.exe

# Python 프로세스 종료
taskkill /F /im python.exe
```

## 🏗️ 아키텍처

- **UI (Next.js)**: 포트 3000에서 실행되는 React 기반 챗봇 인터페이스
- **LLM (FastAPI)**: 포트 8001에서 실행되는 6단계 에이전트 파이프라인
  - 전달자 (Facilitator): 의도파악/키워드추출
  - 검색자 (Search): 다중라운드검색
  - 분석가 (Analyst): 법적분석/쟁점식별
  - 응답자 (Response): 답변내용생성
  - 인용자 (Citation): 인용/출처관리
  - 검증자 (Validator): 종합검증/품질관리

## ⚠️ 주의사항

1. **포트 변경 금지**: 3000, 8001 외의 포트 사용 절대 금지
2. **simple_server.py 사용 금지**: 삭제됨. real_agent_server.py만 사용
3. **환경 변수**: .env 파일의 OPENAI_API_KEY 필수
4. **프로세스 정리**: 서버 재시작 전 기존 프로세스 종료 필수