# AgentL2 - 법률 온톨로지 DB 기반 AI 법률 어시스턴트

## 🎯 프로젝트 개요

**AgentL2**는 법률 온톨로지 데이터베이스와 LLM을 결합한 지능형 법률 서비스 플랫폼입니다.

### 핵심 기능
1. **법률 데이터 수집** - 국가법령정보센터 API를 통한 법령/판례 자동 수집
2. **서식 데이터베이스** - 계약서 서식 29만 건 (템플릿, 조항, 문단) PostgreSQL 저장
3. **6단계 에이전트 파이프라인** - 전달자→검색자→분석가→응답자→인용자→검증자
4. **웹 기반 챗봇 UI** - React/Next.js 기반 법률 상담 인터페이스

### 데이터 현황
- **계약서 서식**: 10,477개 템플릿, 70,029개 조항, 209,883개 문단 ✅ 적재 완료
- **ML 판례 데이터셋**: 99,028건 (사건명분류, 판결예측, 법령분류, 요약 등) ✅ 적재 완료
- **온톨로지 라벨**: 1,534개 법률 개념 매핑 ✅ 적재 완료
- **법령/판례 API**: 국가법령정보센터 수집 🔄 준비 중

## 🚀 빠른 시작

### 1. 환경 설정
```bash
# .env 파일 생성 (API 키, DB 비밀번호 등)
cp .env.example .env
# .env 파일 편집: OPENAI_API_KEY, LAW_API_OC 등 설정
```

### 2. 전체 시스템 시작
```bash
# Docker Compose로 5개 서비스 일괄 시작
docker-compose up -d
# 또는
docker-start.bat  # Windows

# 서비스 상태 확인
docker-compose ps
```

### 3. 접속 확인
- **웹 UI**: http://localhost:3000 (챗봇 인터페이스)
- **LLM API**: http://localhost:8001/docs (FastAPI Swagger)
- **DB 관리**: http://localhost:8080 (Adminer)
- **메트릭**: http://localhost:8000/metrics (Collector)

### 4. 데이터 수집 (선택사항)
```bash
# 법령 수집
make laws ARGS='--query "금융소비자보호" --page 1 --pages 3 --collection-id poc-20250926'

# 판례 수집
make prec ARGS='--keywords "금융소비자보호 불완전판매" --date-range "20200101~20250926"'
```

## 📊 시스템 아키텍처

### 서비스 구성
```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentL2 플랫폼                              │
├─────────────────────────────────────────────────────────────────┤
│  [웹 UI (Next.js:3000)]                                         │
│         ↓                                                        │
│  [LLM 서버 (FastAPI:8001)]                                      │
│    ├─ 전달자 (Facilitator) - 의도파악/키워드추출                │
│    ├─ 검색자 (Search) - 다중라운드검색                           │
│    ├─ 분석가 (Analyst) - 법적분석/쟁점식별                      │
│    ├─ 응답자 (Response) - 답변내용생성                           │
│    ├─ 인용자 (Citation) - 인용/출처관리                         │
│    └─ 검증자 (Validator) - 종합검증/품질관리                    │
│         ↓                                                        │
│  [PostgreSQL:5432] ←→ [Adminer:8080]                           │
│    ├─ 법령/판례 테이블 (laws, precedents)                       │
│    ├─ 서식 DB (form_templates, articles, paragraphs)           │
│    └─ 온톨로지 (form_labels: 1,534개 법률 개념)                │
│         ↑                                                        │
│  [Collector:8000] - 법령/판례 API 수집                          │
└─────────────────────────────────────────────────────────────────┘
```

### 데이터 레이어

#### 1. 법률 온톨로지 데이터베이스
**서식 데이터 (Form Templates)** - 계약서 생성/검토용
- `form_templates`: 10,477개 서식 템플릿
- `form_articles`: 70,029개 조항 구조
- `form_paragraphs`: 209,883개 상세 문단
- `form_labels`: 1,534개 법률 개념 라벨
  - 예: 1001002(목적조항), 1001003(정의조항), 1001004(의무조항)
- `form_entities`: 변수/플레이스홀더 (@회사1, @주소1 등)

**ML 판례 데이터셋** - 머신러닝 학습/검색용 (적재 완료)
- `ml_casename_cls`: 11,294건 사건명 분류
- `ml_ljp`: 13,335건 판결 예측 (Legal Judgment Prediction)
- `ml_raw_samples`: 51,101건 원본 판례
- `ml_statute_cls`: 3,298건 법령 분류
- `ml_summarization`: 20,000건 판례 요약

**법령/판례 API 데이터** - 법률 자문/검색용 (수집 준비 중)
- `laws`: 법령 전문, 조문, 개정 이력
- `precedents`: 판례 원문, 판시사항, 판결요지

#### 2. LLM 서비스 레이어
**6단계 에이전트 파이프라인**
1. **Facilitator**: 사용자 질문 분석 → 검색 키워드 추출
2. **Search**: 관련 법령/판례/서식 검색 (PostgreSQL 쿼리)
3. **Analyst**: 법적 쟁점 식별 및 분석
4. **Response**: 구조화된 답변 생성
5. **Citation**: 법령 조문/판례 인용 추가
6. **Validator**: 답변 품질 검증 및 후속 질문 제안

### LLM 활용 시나리오

#### 시나리오 1: 계약서 생성
```
사용자: "B2B 비밀유지계약서 작성해줘"
  ↓
[Facilitator] 키워드 추출: "비밀유지", "B2B", "기업간"
  ↓
[Search] form_templates WHERE template_type='NDA' AND use_case LIKE '%기업간%'
         → 10,477개 템플릿 중 매칭
  ↓
[Analyst] 필수 조항 식별: 목적, 정의, 의무, 손해배상, 유효기간
  ↓
[Response] form_articles + form_paragraphs 조합하여 계약서 초안 생성
  ↓
[Citation] 관련 법령 (부정경쟁방지법 제2조 등) 삽입
  ↓
[Validator] 누락 조항 체크, 법적 리스크 검토
```

#### 시나리오 2: 계약서 검토
```
사용자: "이 NDA 계약서에 문제 없나요?" (파일 업로드)
  ↓
[Search] form_labels에서 표준 조항 라벨 1,534개 로드
  ↓
[Analyst] 업로드된 계약서 vs. 표준 서식 비교
         - 누락 조항 식별 (form_articles 기준)
         - 불리한 조항 탐지 (form_paragraphs 유사도)
  ↓
[Response] 리스크 리포트 생성
  ↓
[Citation] 관련 판례 인용 (precedents 테이블)
```

#### 시나리오 3: 법률 자문
```
사용자: "금융소비자보호법 설명의무 위반 시 처벌은?"
  ↓
[Search] laws WHERE law_name LIKE '%금융소비자보호%'
         + precedents WHERE keywords LIKE '%설명의무%'
  ↓
[Analyst] 법령 조문 분석 + 판례 검토
  ↓
[Response] 구조화된 답변 (법적 근거 + 처벌 내용)
  ↓
[Citation] 법조문 인용 + 판례 요지
```

## 필수 환경 변수

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `OPENAI_API_KEY` | OpenAI API 키 (LLM 서비스용) | (필수) |
| `POSTGRES_DB` | PostgreSQL DB 이름 | `agentl2` |
| `POSTGRES_USER` | DB 사용자명 | `agentl2_app` |
| `POSTGRES_PASSWORD` | DB 비밀번호 | `change_me` |
| `POSTGRES_PORT` | Postgres 포트 | `5432` |
| `DATABASE_URL` | SQLAlchemy 접속 문자열 | `postgresql+psycopg://agentl2_app:change_me@postgres:5432/agentl2` |
| `LAW_API_OC` | 국가법령정보센터 API 키 | (필수) |
| `PREC_API_OC` | 판례 API 키 | (선택) |
| `COLLECTOR_METRICS_PORT` | Collector 메트릭 포트 | `8000` |

> 전체 환경 변수는 `.env.example` 참고. `.env`는 커밋하지 마세요.

## 실행 예시

```bash
# 컨테이너 기동/종료
make up
make down

# DB 초기화 스크립트 재적용
make init-db

# 법령 수집 (지정한 쿼리/페이지 범위, collection-id)
make laws ARGS='\
  --query "금융소비자보호" \
  --page 1 --pages 3 \
  --page-size 100 \
  --collection-id "poc-20250926" \
'

# 판례 수집 (키워드 + 날짜 범위)
make prec ARGS='\
  --keywords "금융소비자보호 불완전판매 설명의무 약관 은행" \
  --date-range "20200101~20250926" \
  --page 1 --pages 2 \
  --page-size 100 \
  --collection-id "poc-20250926" \
'

# Collector 로그 추적
make logs
```

Collector 컨테이너는 `/metrics` (기본 8000 포트)에서 수집 건수, 중복 스킵, 실패, 최근 실행 타임스탬프를 텍스트 형식으로 노출합니다.

## 사용 메모 (PoC)
- 법령 대상: 「금융소비자보호에 관한 법률」, 같은 시행령·시행규칙.
- 판례 키워드: 금융소비자보호, 불완전판매, 설명의무, 약관, 은행.
- PoC 수집 기간: `20200101~20250926`.

## API 파라미터 참고
- `lawSearch.do`: `OC`, `target`, `type`, `query`, `display`, `page`, `sort`.
- `lawService.do`: `OC`, `target`, `ID`, `type`.
- `precSearch.do`: `OC`, `target`, `type`, `search`, `startDate`, `endDate`, `display`, `page`.

## 관측성
- Loguru 기반 JSON 로그로 모든 실행 상황을 구조화된 형태로 기록합니다.
- 내장 HTTP 서버가 `/metrics` 텍스트 엔드포인트를 제공하며, 수집/중복/실패 건수와 실행 시작·종료 시각을 즉시 확인할 수 있습니다.

## 테스트 전략
- `pytest` 단위 테스트(`collector/tests`)로 UUID 규칙과 파서를 검증합니다.
- 추후 Mock API와의 통합 시나리오를 추가할 수 있도록 명령형 구조로 설계했습니다.

## 문제 해결 FAQ
- **Idempotency가 지켜지나요?**  
  법령은 `[법령ID, 시행일자]`, 판례는 `[법원코드, 사건번호, 선고일자]` 조합으로 중복을 차단하고, 재수집 시 기존 레코드를 덮어씁니다.
- **Rate Limit 오류가 발생합니다.**  
  `.env`의 `LAW_API_RATE_LIMIT_RPS`, `PREC_API_RATE_LIMIT_RPS` 값을 API 정책에 맞춰 조정하세요. 내부 토큰 버킷으로 요청 간격을 균형 있게 분배합니다.
- **페이지네이션 범위를 조절하고 싶습니다.**  
  `--page`, `--pages`, `--page-size` 옵션으로 범위를 지정하면 됩니다. 필요시 `_extract_items`를 커스터마이징하여 다양한 응답 구조를 지원합니다.
- **날짜 파싱 오류가 납니다.**  
  입력은 `YYYYMMDD` 형식을 권장하며, 응답은 `YYYYMMDD`, `YYYY-MM-DD`, `YYYY.MM.DD`, ISO8601 등을 자동 파싱합니다. 지원 외 형식은 예외로 처리되므로 로그를 확인하세요.

## 🗂️ 프로젝트 구조

```
agentl2/
├── collector/          # 법령/판례 데이터 수집 모듈
│   ├── agentl2/
│   │   ├── cli/       # 수집 CLI (laws, prec)
│   │   ├── api/       # API 클라이언트 (국가법령정보센터)
│   │   └── db/        # PostgreSQL ORM 모델
│   └── tests/         # 단위 테스트
├── llm/               # LLM 서비스 (FastAPI)
│   ├── api/           # 6단계 에이전트 파이프라인
│   │   ├── facilitator_agent.py
│   │   ├── search_agent.py
│   │   ├── analyst_agent.py
│   │   ├── response_agent.py
│   │   ├── citation_agent.py
│   │   └── validator_agent.py
│   ├── scripts/       # DB 마이그레이션 스크립트
│   │   ├── 01_create_form_tables_no_vector.sql
│   │   ├── 10_fix_template_code.py
│   │   └── 11_migrate_full_content.py
│   └── real_agent_server.py  # FastAPI 서버
├── ui/                # React/Next.js 웹 UI
│   ├── src/
│   │   ├── app/       # Next.js 13 App Router
│   │   └── components/
│   └── public/
├── db/                # 데이터베이스 초기화 스크립트
├── docker-compose.yml # 전체 시스템 구성
└── .env.example       # 환경 변수 템플릿
```

## 📈 데이터 현황 및 통계

### PostgreSQL 데이터베이스
```sql
-- 서식 DB (계약서 생성/검토용) ✅ 적재 완료
SELECT 'form_templates' as table, COUNT(*) FROM form_templates;   -- 10,477
SELECT 'form_articles' as table, COUNT(*) FROM form_articles;     -- 70,029
SELECT 'form_paragraphs' as table, COUNT(*) FROM form_paragraphs; -- 209,883
SELECT 'form_labels' as table, COUNT(*) FROM form_labels;         -- 1,534

-- ML 판례 데이터셋 (외부 수집 완료) ✅ 적재 완료
SELECT 'ml_casename_cls' as table, COUNT(*) FROM ml_casename_cls;   -- 11,294
SELECT 'ml_ljp' as table, COUNT(*) FROM ml_ljp;                     -- 13,335
SELECT 'ml_raw_samples' as table, COUNT(*) FROM ml_raw_samples;     -- 51,101
SELECT 'ml_statute_cls' as table, COUNT(*) FROM ml_statute_cls;     -- 3,298
SELECT 'ml_summarization' as table, COUNT(*) FROM ml_summarization; -- 20,000

-- 법령/판례 DB (국가법령정보센터 API 수집 대기) 🔄 준비 중
SELECT 'laws' as table, COUNT(*) FROM laws;           -- 0 (수집 필요)
SELECT 'precedents' as table, COUNT(*) FROM precedents; -- 0 (수집 필요)
```

### ML 판례 데이터셋 상세
**외부 머신러닝 데이터셋 (적재 완료: 99,028건)**

| 테이블 | 레코드 수 | 설명 |
|--------|----------|------|
| `ml_casename_cls` | 11,294 | 판례 사건명 분류 데이터 |
| `ml_ljp` | 13,335 | Legal Judgment Prediction (판결 예측) |
| `ml_raw_samples` | 51,101 | 원본 판례 샘플 (가장 많은 데이터) |
| `ml_statute_cls` | 3,298 | 법령 분류 데이터 |
| `ml_summarization` | 20,000 | 판례 요약 데이터 |

**주요 컬럼 구조:**
- **ml_casename_cls**: casetype, casename, facts (사실관계)
- **ml_ljp**: casetype, casename, facts, claim_acceptance_lv (청구인용도), gist_of_claim (청구요지), ruling (판결)
- **ml_raw_samples**: 원본 판례 텍스트 및 메타데이터
- **ml_statute_cls**: 법령 분류 및 적용 법조문
- **ml_summarization**: 판례 요약문 (AI 학습용)

**데이터 출처**: 외부 법률 ML 데이터셋 (JSONL 형식)

**마이그레이션 상태**:
- ✅ PostgreSQL 적재 완료 (99,028건)
- 🔄 내부 `precedents` 테이블로 정규화 작업 준비 중
- 🔄 `laws` 테이블과 연계 예정 (법조문 참조)

### 서식 데이터 상세
- **템플릿 유형**: 비밀유지계약서(NDA), 위임장, 각서, 동의서 등
- **조항 유형**: purpose, definition, obligation, penalty, term, dispute 등
- **평균 통계**:
  - 템플릿당 평균 조항 수: 6.7개
  - 조항당 평균 문단 수: 3.0개
  - 전체 텍스트 용량: 약 500MB

## 🔮 향후 확장 계획

### Phase 1: 데이터 수집 (현재 진행 중)
- [x] PostgreSQL 서식 DB 구축 (29만 건 완료)
- [x] ML 판례 데이터셋 적재 (99,028건 완료)
- [ ] ML 판례 데이터 정규화 (`precedents` 테이블로 마이그레이션)
- [ ] 법령 데이터 수집 (국가법령정보센터 API)
- [ ] 판례 데이터 수집 (대법원 API)

### Phase 2: 검색 고도화
- [ ] pgvector 설치 및 임베딩 생성
- [ ] 의미 기반 유사도 검색 (Vector Search)
- [ ] 하이브리드 검색 (키워드 + 벡터)

### Phase 3: 온톨로지 확장
- [ ] Neo4j 그래프 DB 연동 (`graph/`)
- [ ] OWL/SWRL 기반 법률 온톨로지 (`ontology/`)
- [ ] 법령 간 관계 그래프 구축

### Phase 4: LLM 기능 확장
- [ ] 계약서 자동 생성 API
- [ ] 계약서 리스크 분석 API
- [ ] 판례 유사도 검색 및 추천
- [ ] 법령 개정 이력 추적

## 📚 참고 자료

### 데이터베이스 스키마
- [llm/scripts/README_MIGRATION.md](llm/scripts/README_MIGRATION.md) - 서식 DB 마이그레이션 가이드
- [llm/scripts/PGVECTOR_SETUP.md](llm/scripts/PGVECTOR_SETUP.md) - pgvector 설치 가이드

### 시스템 상태
- [SYSTEM_STATUS.md](SYSTEM_STATUS.md) - 전체 서비스 상태 및 접속 정보
- [CLAUDE.md](CLAUDE.md) - 개발 가이드 (포트 설정, 아키텍처)

### API 문서
- **LLM API**: http://localhost:8001/docs (FastAPI Swagger)
- **Collector 메트릭**: http://localhost:8000/metrics (Prometheus 형식)
