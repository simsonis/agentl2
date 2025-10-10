-- ================================================
-- 임베딩 벡터 컬럼 추가 (pgvector 설치 후 실행)
-- ================================================

-- 주의: 이 스크립트는 pgvector extension이 설치된 후에만 실행 가능합니다.
-- 설치 확인: SELECT * FROM pg_extension WHERE extname = 'vector';

-- 1. 벡터 컬럼 추가
ALTER TABLE form_templates
ADD COLUMN IF NOT EXISTS embedding_vector VECTOR(1536);

ALTER TABLE form_articles
ADD COLUMN IF NOT EXISTS embedding_vector VECTOR(1536);

ALTER TABLE form_paragraphs
ADD COLUMN IF NOT EXISTS embedding_vector VECTOR(768);

ALTER TABLE form_clauses
ADD COLUMN IF NOT EXISTS embedding_vector VECTOR(1536);

ALTER TABLE form_labels
ADD COLUMN IF NOT EXISTS embedding_vector VECTOR(768);

-- 2. 벡터 인덱스 생성 (IVFFlat)
-- 주의: 데이터가 충분히 있어야 인덱스 생성 가능 (최소 수백 개 권장)

-- form_templates 인덱스
CREATE INDEX IF NOT EXISTS idx_template_embedding ON form_templates
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

-- form_articles 인덱스
CREATE INDEX IF NOT EXISTS idx_article_embedding ON form_articles
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

-- form_paragraphs 인덱스
CREATE INDEX IF NOT EXISTS idx_paragraph_embedding ON form_paragraphs
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 50);

-- form_clauses 인덱스
CREATE INDEX IF NOT EXISTS idx_clause_embedding ON form_clauses
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 100);

-- form_labels 인덱스
CREATE INDEX IF NOT EXISTS idx_label_embedding ON form_labels
USING ivfflat (embedding_vector vector_cosine_ops)
WITH (lists = 50);

-- 3. 벡터 관련 유틸리티 함수 생성

-- 코사인 유사도 계산 함수
CREATE OR REPLACE FUNCTION vector_cosine_similarity(a VECTOR, b VECTOR)
RETURNS FLOAT AS $$
BEGIN
    RETURN 1 - (a <=> b);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION vector_cosine_similarity IS '두 벡터 간 코사인 유사도 계산 (0~1, 1이 가장 유사)';

-- 4. 벡터 통계 뷰 생성

CREATE OR REPLACE VIEW vector_coverage_stats AS
SELECT
    'form_templates' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(embedding_vector) AS with_vectors,
    ROUND(COUNT(embedding_vector) * 100.0 / NULLIF(COUNT(*), 0), 2) AS coverage_percent
FROM form_templates
UNION ALL
SELECT
    'form_articles',
    COUNT(*),
    COUNT(embedding_vector),
    ROUND(COUNT(embedding_vector) * 100.0 / NULLIF(COUNT(*), 0), 2)
FROM form_articles
UNION ALL
SELECT
    'form_paragraphs',
    COUNT(*),
    COUNT(embedding_vector),
    ROUND(COUNT(embedding_vector) * 100.0 / NULLIF(COUNT(*), 0), 2)
FROM form_paragraphs
UNION ALL
SELECT
    'form_clauses',
    COUNT(*),
    COUNT(embedding_vector),
    ROUND(COUNT(embedding_vector) * 100.0 / NULLIF(COUNT(*), 0), 2)
FROM form_clauses
UNION ALL
SELECT
    'form_labels',
    COUNT(*),
    COUNT(embedding_vector),
    ROUND(COUNT(embedding_vector) * 100.0 / NULLIF(COUNT(*), 0), 2)
FROM form_labels;

COMMENT ON VIEW vector_coverage_stats IS '각 테이블의 벡터 임베딩 적용률 통계';

-- 5. 샘플 쿼리 함수 생성

-- 유사 템플릿 검색 함수
CREATE OR REPLACE FUNCTION search_similar_templates(
    query_embedding VECTOR(1536),
    limit_count INTEGER DEFAULT 5
)
RETURNS TABLE (
    template_code VARCHAR,
    template_name VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.template_code,
        t.template_name,
        vector_cosine_similarity(t.embedding_vector, query_embedding) AS similarity
    FROM form_templates t
    WHERE t.embedding_vector IS NOT NULL
    ORDER BY t.embedding_vector <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_similar_templates IS '쿼리 임베딩과 유사한 템플릿 검색';

-- 유사 조항 검색 함수
CREATE OR REPLACE FUNCTION search_similar_articles(
    query_embedding VECTOR(1536),
    template_type_filter VARCHAR DEFAULT NULL,
    article_type_filter VARCHAR DEFAULT NULL,
    limit_count INTEGER DEFAULT 10
)
RETURNS TABLE (
    template_code VARCHAR,
    article_title VARCHAR,
    article_type VARCHAR,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.template_code,
        a.article_title,
        a.article_type,
        vector_cosine_similarity(a.embedding_vector, query_embedding) AS similarity
    FROM form_articles a
    JOIN form_templates t ON t.id = a.template_id
    WHERE a.embedding_vector IS NOT NULL
      AND (template_type_filter IS NULL OR t.template_type = template_type_filter)
      AND (article_type_filter IS NULL OR a.article_type = article_type_filter)
    ORDER BY a.embedding_vector <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_similar_articles IS '쿼리 임베딩과 유사한 조항 검색 (필터 옵션 포함)';

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ 벡터 컬럼 및 인덱스 추가 완료!';
    RAISE NOTICE '📊 추가된 벡터 컬럼: 5개';
    RAISE NOTICE '🔍 생성된 벡터 인덱스: 5개';
    RAISE NOTICE '🛠️  생성된 유틸리티 함수: 3개';
    RAISE NOTICE '';
    RAISE NOTICE '📌 다음 단계:';
    RAISE NOTICE '1. 임베딩 생성 스크립트 실행';
    RAISE NOTICE '2. SELECT * FROM vector_coverage_stats; 로 적용률 확인';
    RAISE NOTICE '3. 유사도 검색 테스트';
END $$;
