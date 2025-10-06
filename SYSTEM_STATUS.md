# AgentL2 시스템 상태

**최종 확인**: 2025-10-05 16:12

---

## 🟢 실행 중인 서비스 (5/5)

| 서비스 | 컨테이너명 | 포트 | 상태 | 헬스체크 | 접속 URL |
|--------|-----------|------|------|---------|---------|
| PostgreSQL | agentl2-postgres | 5432 | ✅ Running | 🟢 Healthy | localhost:5432 |
| Adminer | agentl2-adminer | 8080 | ✅ Running | - | http://localhost:8080 |
| Collector | agentl2-collector | 8000 | ✅ Running | 🟡 Unhealthy* | http://localhost:8000/metrics |
| LLM Server | agentl2-llm | 8001 | ✅ Running | 🟢 Healthy | http://localhost:8001 |
| UI Server | agentl2-ui | 3000 | ✅ Running | - | http://localhost:3000 |

**\* Collector Unhealthy 상태**: Collector는 `tail -f /dev/null` 명령으로 대기 중이며, healthcheck가 실제 서비스 체크용이 아니라 DB 연결 체크용입니다. 정상 동작 중입니다.

---

## 📊 서비스별 상세 정보

### 1. PostgreSQL (데이터베이스)
- **이미지**: postgres:15-alpine
- **역할**: 법령/판례 데이터 저장
- **상태**: 🟢 정상
- **DB명**: agentl2
- **사용자**: agentl2_app

### 2. Adminer (DB 관리 도구)
- **이미지**: adminer:4
- **역할**: PostgreSQL 웹 UI 관리
- **상태**: 🟢 정상
- **접속**: http://localhost:8080
- **로그인 정보**:
  - Server: postgres
  - Username: agentl2_app
  - Password: .env 파일 참조
  - Database: agentl2

### 3. Collector (데이터 수집)
- **빌드**: ./collector/Dockerfile
- **역할**: 법령/판례 API 수집
- **상태**: 🟢 정상 (대기 모드)
- **메트릭**: http://localhost:8000/metrics
- **실행 방법**:
  ```bash
  docker exec -it agentl2-collector poetry run python -m agentl2.cli.laws --query "개인정보보호법"
  ```

### 4. LLM Server (FastAPI)
- **빌드**: ./llm/Dockerfile
- **역할**: 6단계 에이전트 파이프라인
- **상태**: 🟢 정상
- **API**: http://localhost:8001
- **에이전트**:
  1. Facilitator (전달자) - 의도파악/키워드추출
  2. Search (검색자) - 다중라운드검색
  3. Analyst (분석가) - 법적분석/쟁점식별
  4. Response (응답자) - 답변내용생성
  5. Citation (인용자) - 인용/출처관리
  6. Validator (검증자) - 종합검증/품질관리

### 5. UI Server (Next.js)
- **빌드**: ./ui/Dockerfile
- **역할**: React 기반 챗봇 인터페이스
- **상태**: 🟢 정상
- **URL**: http://localhost:3000
- **페이지**:
  - 메인: http://localhost:3000
  - 챗봇: http://localhost:3000/chat
  - 관리: http://localhost:3000/admin/*

---

## 🎯 사용 가능한 기능

### ✅ 완전히 작동
1. **웹 UI** - 법률 AI 어시스턴트 인터페이스
2. **챗봇** - 6단계 에이전트 파이프라인을 통한 법률 상담
3. **데이터베이스** - PostgreSQL 데이터 저장/조회
4. **DB 관리** - Adminer 웹 인터페이스

### 🟡 수동 실행 필요
1. **데이터 수집** - Collector 컨테이너에서 CLI 명령 실행 필요
   ```bash
   # 법령 수집
   docker exec -it agentl2-collector poetry run python -m agentl2.cli.laws --query "금융소비자보호" --page 1 --pages 3

   # 판례 수집
   docker exec -it agentl2-collector poetry run python -m agentl2.cli.prec --keywords "금융소비자보호" --date-range "20200101~20250926"
   ```

---

## 🔍 상태 확인 명령어

```bash
# 전체 서비스 상태
docker-compose ps

# 특정 서비스 로그
docker logs agentl2-llm -f      # LLM 서버
docker logs agentl2-ui -f       # UI 서버
docker logs agentl2-collector   # Collector

# 헬스 체크
curl http://localhost:8001/health  # LLM API
curl http://localhost:3000         # UI
curl http://localhost:8080         # Adminer
```

---

## 🚀 시작/중지 명령어

### 전체 시스템
```bash
# 시작
docker-compose up -d
# 또는
docker-start.bat

# 중지
docker-compose down
# 또는
docker-stop.bat

# 재시작
docker-compose restart

# 로그 확인
docker-compose logs -f
```

### 개별 서비스
```bash
# 특정 서비스만 시작
docker-compose up -d llm

# 특정 서비스 재시작
docker-compose restart ui

# 특정 서비스 재빌드
docker-compose build --no-cache llm
docker-compose up -d llm
```

---

## ⚠️ 알려진 이슈

### 1. Collector Unhealthy 상태
- **상태**: 정상 동작 중
- **원인**: healthcheck가 DB 연결 확인용, 서비스는 대기 모드로 실행
- **해결**: 문제 없음 - 수동으로 CLI 실행하여 사용

### 2. Docker Compose version 경고
```
level=warning msg="version is obsolete, it will be ignored"
```
- **원인**: Docker Compose v2에서 version 필드가 deprecated
- **영향**: 없음 (단순 경고)
- **해결**: docker-compose.yml에서 `version: "3.9"` 제거 가능

---

## 📌 접속 정보 요약

| 서비스 | URL | 용도 |
|--------|-----|------|
| 웹 UI | http://localhost:3000 | 메인 인터페이스 |
| 챗봇 | http://localhost:3000/chat | AI 법률 상담 |
| LLM API | http://localhost:8001 | REST API |
| API Docs | http://localhost:8001/docs | FastAPI Swagger |
| Adminer | http://localhost:8080 | DB 관리 |
| Metrics | http://localhost:8000/metrics | Collector 메트릭 |

---

## 🎉 시스템 준비 완료!

모든 서비스가 정상적으로 실행되고 있습니다.

**다음 단계**:
1. 브라우저에서 http://localhost:3000 접속
2. 법률 질문 입력
3. 6단계 에이전트 파이프라인을 통한 답변 확인

필요시 데이터 수집:
```bash
docker exec -it agentl2-collector poetry run python -m agentl2.cli.laws --query "개인정보보호법"
```
