# agentl2 데이터 수집 모듈

## 빠른 시작 (3줄 요약)
1. `.env.example`을 복사해 `.env`를 만들고(API 키·DB 비밀번호 등 민감정보는 `.env`에만, 커밋 금지).
2. `make up`으로 PostgreSQL·Adminer·Collector를 한 번에 기동합니다.
3. `make laws ARGS='--query "금융소비자보호" --page 1 --pages 3 --collection-id poc-20250926'` 형태로 수집 CLI를 실행합니다.

## 필수 환경 변수

| 변수 | 설명 | 기본값 |
| --- | --- | --- |
| `POSTGRES_DB` | 수집 데이터를 저장할 DB 이름 | `agentl2` |
| `POSTGRES_USER` | DB 사용자명 | `agentl2_app` |
| `POSTGRES_PASSWORD` | DB 비밀번호 | `change_me` |
| `POSTGRES_PORT` | 호스트에서 노출할 Postgres 포트 | `5432` |
| `DATABASE_URL` | Collector가 사용할 SQLAlchemy 접속 문자열 | `postgresql+psycopg://agentl2_app:change_me@postgres:5432/agentl2` |
| `COLLECTOR_METRICS_PORT` | `/metrics` 엔드포인트 포트 | `8000` |
| `LAW_API_OC` | 국가법령정보센터 API 발급키 | (필수) |
| `LAW_API_DEFAULT_PAGE_SIZE` | 법령 수집 기본 페이지 크기 | `100` |
| `LAW_API_RATE_LIMIT_RPS` | 법령 API 초당 요청 제한 | `3` |
| `PREC_API_OC` | 판례 API 키(미설정 시 법령 키 재사용) | (선택) |
| `PREC_API_DEFAULT_PAGE_SIZE` | 판례 수집 기본 페이지 크기 | `100` |
| `PREC_API_RATE_LIMIT_RPS` | 판례 API 초당 요청 제한 | `3` |

> 추가 변수는 `.env.example` 참고. `.env`는 커밋하지 마세요.

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

## 추후 확장 포인트
- `graph/` : Neo4j 등 그래프 저장소 연동 준비.
- `ontology/` : OWL/SWRL 기반 온톨로지 변환 및 검증.
- `llm/` : 프롬프트·검증·슈퍼바이저 파이프라인을 위한 자리 마련.
