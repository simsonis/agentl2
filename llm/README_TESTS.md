# AgentL2 LLM 테스트 가이드

## 📋 테스트 개요

이 디렉토리에는 AgentL2 LLM 파이프라인의 단위 테스트와 통합 테스트가 포함되어 있습니다.

### 테스트 구조

```
llm/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # 공통 fixtures
│   ├── test_base_agent.py       # BaseAgent 테스트
│   ├── test_facilitator_agent.py # Facilitator Agent 테스트
│   ├── test_search_agent.py     # Search Agent 테스트
│   └── test_pipeline.py         # Pipeline 통합 테스트
├── pytest.ini                   # Pytest 설정
└── requirements-test.txt        # 테스트 의존성
```

## 🚀 빠른 시작

### 1. 테스트 환경 설정

```bash
cd llm

# 테스트 의존성 설치
pip install -r requirements-test.txt
```

### 2. 전체 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 특정 파일만 테스트
pytest tests/test_facilitator_agent.py

# 특정 테스트 함수만 실행
pytest tests/test_facilitator_agent.py::TestFacilitatorAgent::test_initialization
```

### 3. 커버리지 확인

```bash
# 커버리지 리포트와 함께 테스트
pytest --cov=src/agentl2_llm --cov-report=html

# HTML 리포트 확인 (브라우저에서 열기)
# htmlcov/index.html
```

## 📊 테스트 구성

### conftest.py - 공통 Fixtures

테스트에서 재사용 가능한 fixtures를 제공합니다:

- `mock_openai_client`: OpenAI API 클라이언트 Mock
- `sample_context`: 빈 대화 컨텍스트
- `sample_context_with_history`: 대화 기록이 있는 컨텍스트
- `mock_llm_response_clear`: 명확한 의도의 LLM 응답
- `mock_llm_response_needs_clarification`: 추가 질문이 필요한 LLM 응답
- `mock_search_results`: Mock 검색 결과

### test_base_agent.py

BaseAgent의 핵심 기능 테스트:
- AgentAction enum 검증
- AgentResponse 모델 생성 및 검증
- ConversationContext 모델 테스트
- LLM 호출 성공/실패 처리
- 대화 기록 구성
- 구조화된 응답 파싱

### test_facilitator_agent.py

Facilitator Agent 테스트:
- 에이전트 초기화
- 명확한 의도 처리
- 모호한 질문 처리 (clarification 요청)
- 대화 기록과 함께 처리
- 에러 핸들링
- 의도/키워드 완성도 검증
- 대화 요약 추출

### test_search_agent.py

Search Agent 테스트:
- 에이전트 초기화
- 키워드 기반 검색
- 키워드 없을 때 자동 추출
- 검색 결과 없을 때 처리
- 다중 라운드 검색
- 관련성 점수 평가
- 내부/외부 검색 통합
- 에러 핸들링

### test_pipeline.py

Pipeline 통합 테스트:
- 파이프라인 초기화
- 새 대화 처리 (6단계 모두 실행)
- Clarification이 필요한 경우
- 대화 ID로 계속 진행
- 대화 턴 제한 적용
- 이벤트 핸들러 호출 확인
- 에러 핸들링
- 파이프라인 상태 조회
- 대화 상태 조회 및 정리

## 🎯 테스트 작성 가이드

### 비동기 테스트

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

### Mock 사용

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_with_mock(mock_openai_client):
    # Mock 응답 설정
    mock_completion = MagicMock()
    mock_completion.choices = [
        MagicMock(message=MagicMock(content="Test response"))
    ]
    mock_openai_client.chat.completions.create = AsyncMock(
        return_value=mock_completion
    )

    # 테스트 실행
    agent = FacilitatorAgent(openai_client=mock_openai_client)
    response = await agent.process("test", context)

    # 검증
    assert response is not None
```

### Fixture 재사용

```python
def test_with_fixtures(mock_openai_client, sample_context):
    # fixture를 파라미터로 받아서 사용
    agent = FacilitatorAgent(openai_client=mock_openai_client)
    # ... 테스트 로직
```

## 📈 커버리지 목표

| 모듈 | 목표 커버리지 | 현재 상태 |
|-----|--------------|----------|
| base_agent.py | 90%+ | ✅ |
| facilitator_agent.py | 85%+ | ✅ |
| search_agent.py | 85%+ | ✅ |
| enhanced_agent_pipeline.py | 80%+ | ✅ |
| 기타 agents | 70%+ | 🟡 Pending |

## 🔍 테스트 실행 옵션

```bash
# 특정 마커만 실행
pytest -m unit           # 단위 테스트만
pytest -m integration    # 통합 테스트만
pytest -m "not slow"     # 느린 테스트 제외

# Verbose 출력
pytest -v

# 실패 시 즉시 중단
pytest -x

# 병렬 실행 (pytest-xdist 필요)
pytest -n auto

# 특정 패턴 매칭
pytest -k "facilitator"  # 이름에 'facilitator'가 포함된 테스트만
```

## 🐛 디버깅

```bash
# 상세한 출력과 함께 실행
pytest -vv

# 실패한 테스트만 재실행
pytest --lf

# 마지막으로 실패한 테스트부터 실행
pytest --ff

# PDB 디버거 사용
pytest --pdb
```

## ✅ 테스트 체크리스트

새로운 Agent나 기능 추가 시 다음을 확인하세요:

- [ ] 초기화 테스트
- [ ] 정상 케이스 테스트
- [ ] 에러 핸들링 테스트
- [ ] 경계 조건 테스트 (빈 입력, 최대 길이 등)
- [ ] Mock을 사용한 외부 의존성 격리
- [ ] 비동기 함수는 `@pytest.mark.asyncio` 사용
- [ ] Fixture 재사용으로 코드 중복 제거

## 🚧 향후 개선 사항

- [ ] Analyst Agent 테스트 추가
- [ ] Response Agent 테스트 추가
- [ ] Citation Agent 테스트 추가
- [ ] Validator Agent 테스트 추가
- [ ] 검색 통합 테스트 추가
- [ ] E2E 테스트 추가
- [ ] 성능 테스트 추가
- [ ] CI/CD 통합

## 📚 참고 자료

- [Pytest 공식 문서](https://docs.pytest.org/)
- [pytest-asyncio 문서](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock 문서](https://docs.python.org/3/library/unittest.mock.html)
