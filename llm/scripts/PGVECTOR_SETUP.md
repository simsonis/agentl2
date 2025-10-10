# pgvector Extension 설치 가이드

## 📋 개요

pgvector는 PostgreSQL에서 벡터 검색을 지원하는 extension입니다.
LLM 임베딩 벡터를 저장하고 유사도 검색을 수행할 수 있습니다.

## 🚀 설치 방법

### 방법 1: Docker 이미지 변경 (권장)

현재 `postgres:15-alpine` 이미지에는 pgvector가 포함되지 않습니다.
pgvector가 사전 설치된 이미지로 변경해야 합니다.

#### 1. docker-compose.yml 수정

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15  # 기존: postgres:15-alpine
    container_name: agentl2-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${POSTGRES_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
```

#### 2. 컨테이너 재생성

```bash
# 기존 컨테이너 중지 및 삭제
docker-compose down

# 새 이미지로 재생성
docker-compose up -d postgres

# 설치 확인
docker exec -it agentl2-postgres psql -U agentl2_app -d agentl2 -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 방법 2: 기존 컨테이너에 빌드 (고급)

Alpine 이미지에서는 컴파일이 어렵습니다. Debian 기반 이미지 사용을 권장합니다.

```bash
# 컨테이너 접속
docker exec -it agentl2-postgres sh

# 필요 패키지 설치 (Alpine)
apk add --no-cache git build-base postgresql-dev

# pgvector 소스 다운로드
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector

# 빌드 및 설치
make
make install

# PostgreSQL 재시작
pg_ctl restart
```

## 📊 Extension 활성화

### 1. Extension 생성

```bash
docker exec -it agentl2-postgres psql -U agentl2_app -d agentl2
```

```sql
-- pgvector extension 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- 설치 확인
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

### 2. 벡터 컬럼 추가

```sql
-- form_templates에 임베딩 벡터 추가 (OpenAI ada-002: 1536차원)
ALTER TABLE form_templates
ADD COLUMN embedding_vector VECTOR(1536);

-- form_articles에 임베딩 벡터 추가
ALTER TABLE form_articles
ADD COLUMN embedding_vector VECTOR(1536);

-- form_paragraphs에 임베딩 벡터 추가 (작은 모델: 768차원)
ALTER TABLE form_paragraphs
ADD COLUMN embedding_vector VECTOR(768);

-- form_clauses에 임베딩 벡터 추가
ALTER TABLE form_clauses
ADD COLUMN embedding_vector VECTOR(1536);

-- form_labels에 임베딩 벡터 추가
ALTER TABLE form_labels
ADD COLUMN embedding_vector VECTOR(768);
```

### 3. 벡터 인덱스 생성

```sql
-- IVFFlat 인덱스 (빠른 검색, 약간의 정확도 트레이드오프)
CREATE INDEX idx_template_embedding ON form_templates
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_article_embedding ON form_articles
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_paragraph_embedding ON form_paragraphs
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 50);

CREATE INDEX idx_clause_embedding ON form_clauses
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_label_embedding ON form_labels
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 50);
```

## 🔍 사용 예시

### 1. 임베딩 벡터 삽입

```sql
-- 예시: 템플릿 임베딩 업데이트
UPDATE form_templates
SET embedding_vector = '[0.1, 0.2, 0.3, ...]'::vector
WHERE template_code = 'NDA_001';
```

### 2. 유사도 검색 (Cosine Similarity)

```sql
-- 사용자 쿼리 임베딩과 가장 유사한 템플릿 찾기
SELECT
    template_code,
    template_name,
    1 - (embedding_vector <=> '[query_embedding]'::vector) AS similarity
FROM form_templates
WHERE embedding_vector IS NOT NULL
ORDER BY embedding_vector <=> '[query_embedding]'::vector
LIMIT 5;
```

### 3. 조합 검색 (필터 + 벡터)

```sql
-- "비밀유지" 카테고리에서 손해배상 관련 조항 검색
SELECT
    a.article_title,
    p.content_text,
    1 - (p.embedding_vector <=> '[query_embedding]'::vector) AS similarity
FROM form_paragraphs p
JOIN form_articles a ON a.id = p.article_id
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_type = '1001'  -- 비밀유지계약서
  AND a.article_type = 'penalty'  -- 손해배상 조항
  AND p.embedding_vector IS NOT NULL
ORDER BY p.embedding_vector <=> '[query_embedding]'::vector
LIMIT 10;
```

## 📈 벡터 인덱스 유형 비교

| 인덱스 타입 | 속도 | 정확도 | 메모리 | 권장 사용 |
|------------|------|--------|--------|-----------|
| **IVFFlat** | 빠름 | 95%+ | 중간 | 대부분의 경우 (기본) |
| **HNSW** | 매우 빠름 | 98%+ | 높음 | 정확도 중요 시 |
| **없음** (Brute Force) | 느림 | 100% | 낮음 | 소규모 데이터 (<10k) |

### IVFFlat 파라미터 가이드

```sql
-- lists 값 설정 (일반적으로 sqrt(rows) 사용)
-- 10,000 rows → lists = 100
-- 100,000 rows → lists = 316
-- 1,000,000 rows → lists = 1000

CREATE INDEX ... WITH (lists = SQRT(row_count));
```

## 🔧 벡터 임베딩 생성 (Python)

```python
import openai
import psycopg2

# OpenAI 임베딩 생성
def get_embedding(text: str) -> list:
    response = openai.Embedding.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response['data'][0]['embedding']

# DB 업데이트
conn = psycopg2.connect(...)
cursor = conn.cursor()

# 템플릿 임베딩 생성
cursor.execute("SELECT id, template_name, description FROM form_templates")
for row in cursor.fetchall():
    template_id, name, desc = row
    text = f"{name}. {desc or ''}"
    embedding = get_embedding(text)

    cursor.execute("""
        UPDATE form_templates
        SET embedding_vector = %s
        WHERE id = %s
    """, (embedding, template_id))

conn.commit()
```

## ✅ 확인 사항

### 1. Extension 설치 확인

```sql
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 2. 벡터 컬럼 확인

```sql
SELECT
    table_name,
    column_name,
    data_type
FROM information_schema.columns
WHERE column_name = 'embedding_vector';
```

### 3. 인덱스 확인

```sql
SELECT
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE indexname LIKE '%embedding%';
```

### 4. 벡터 데이터 확인

```sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(embedding_vector) AS with_vectors,
    ROUND(COUNT(embedding_vector) * 100.0 / COUNT(*), 2) AS coverage_percent
FROM form_templates;
```

## 🚨 문제 해결

### 문제 1: "type vector does not exist"

**원인**: pgvector extension이 설치되지 않음

**해결**:
```bash
docker exec -it agentl2-postgres psql -U agentl2_app -d agentl2 -c "CREATE EXTENSION vector;"
```

### 문제 2: "extension vector is not available"

**원인**: pgvector가 PostgreSQL에 설치되지 않음

**해결**: Docker 이미지를 `pgvector/pgvector:pg15`로 변경

### 문제 3: 인덱스 생성 실패

**원인**: 벡터 데이터가 충분하지 않음 (IVFFlat은 최소 데이터 필요)

**해결**:
- 데이터가 충분히 쌓일 때까지 인덱스 없이 사용
- 또는 HNSW 인덱스 사용 (데이터 적을 때 더 안정적)

```sql
CREATE INDEX ... USING hnsw (embedding_vector vector_cosine_ops);
```

## 📚 참고 자료

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [PostgreSQL Vector Search Best Practices](https://neon.tech/docs/extensions/pgvector)

---

**완료 체크리스트:**
- [ ] Docker 이미지 변경 (`pgvector/pgvector:pg15`)
- [ ] Extension 생성 (`CREATE EXTENSION vector`)
- [ ] 벡터 컬럼 추가 (5개 테이블)
- [ ] 벡터 인덱스 생성 (5개 인덱스)
- [ ] 임베딩 생성 스크립트 작성
- [ ] 유사도 검색 테스트
