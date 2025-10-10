-- ================================================
-- AgentL2 서식 관리 DB 스키마 생성 스크립트 (Vector 제외)
-- ================================================

-- 기존 테이블 삭제 (역순)
DROP TABLE IF EXISTS form_usage_logs CASCADE;
DROP TABLE IF EXISTS form_variations CASCADE;
DROP TABLE IF EXISTS form_entities CASCADE;
DROP TABLE IF EXISTS form_label_mappings CASCADE;
DROP TABLE IF EXISTS form_labels CASCADE;
DROP TABLE IF EXISTS form_clauses CASCADE;
DROP TABLE IF EXISTS form_paragraphs CASCADE;
DROP TABLE IF EXISTS form_articles CASCADE;
DROP TABLE IF EXISTS form_templates CASCADE;

-- ================================================
-- 1. form_templates (서식 템플릿 마스터)
-- ================================================
CREATE TABLE form_templates (
    id SERIAL PRIMARY KEY,
    template_code VARCHAR(50) UNIQUE NOT NULL,
    template_type VARCHAR(50) NOT NULL,
    template_name VARCHAR(200) NOT NULL,
    version VARCHAR(20) DEFAULT 'v1.0',
    status VARCHAR(20) DEFAULT 'active',
    description TEXT,
    use_case TEXT,
    main_category VARCHAR(100),
    sub_category VARCHAR(100),
    related_laws TEXT[],
    total_articles INTEGER DEFAULT 0,
    page_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source_file VARCHAR(255)
    -- embedding_vector는 pgvector 설치 후 추가
);

CREATE INDEX idx_template_type ON form_templates(template_type);
CREATE INDEX idx_template_status ON form_templates(status);
CREATE INDEX idx_template_category ON form_templates(main_category, sub_category);

COMMENT ON TABLE form_templates IS '서식 템플릿 마스터 테이블';
COMMENT ON COLUMN form_templates.template_code IS '서식 고유 코드 (예: NDA_001)';

-- ================================================
-- 2. form_articles (조항 구조)
-- ================================================
CREATE TABLE form_articles (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    article_num INTEGER,
    article_title VARCHAR(200),
    article_type VARCHAR(50),
    sort_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT false,
    parent_article_id INTEGER REFERENCES form_articles(id),
    depth INTEGER DEFAULT 0
    -- embedding_vector는 pgvector 설치 후 추가
);

CREATE INDEX idx_article_template ON form_articles(template_id);
CREATE INDEX idx_article_type ON form_articles(article_type);
CREATE INDEX idx_article_sort ON form_articles(template_id, sort_order);

COMMENT ON TABLE form_articles IS '조항 구조 테이블';
COMMENT ON COLUMN form_articles.article_type IS '조항 유형 (purpose, definition, obligation, penalty 등)';
COMMENT ON COLUMN form_articles.depth IS '계층 깊이 (0=조, 1=항, 2=호)';

-- ================================================
-- 3. form_paragraphs (항/호 상세)
-- ================================================
CREATE TABLE form_paragraphs (
    id SERIAL PRIMARY KEY,
    article_id INTEGER NOT NULL REFERENCES form_articles(id) ON DELETE CASCADE,
    paragraph_num INTEGER,
    sub_paragraph_num INTEGER,
    depth INTEGER DEFAULT 1,
    content_text TEXT NOT NULL,
    format_code VARCHAR(50),
    sort_order INTEGER NOT NULL,
    is_article_title BOOLEAN DEFAULT false,
    tags TEXT[],
    content_tsv TSVECTOR  -- 전체 텍스트 검색용
    -- embedding_vector는 pgvector 설치 후 추가
);

CREATE INDEX idx_paragraph_article ON form_paragraphs(article_id);
CREATE INDEX idx_paragraph_sort ON form_paragraphs(article_id, sort_order);
CREATE INDEX idx_paragraph_tags ON form_paragraphs USING GIN(tags);
CREATE INDEX idx_paragraph_fts ON form_paragraphs USING GIN(content_tsv);

COMMENT ON TABLE form_paragraphs IS '항/호 상세 내용 테이블';
COMMENT ON COLUMN form_paragraphs.tags IS '태그 배열 (제3자_제공_금지, 서면_동의_필수 등)';
COMMENT ON COLUMN form_paragraphs.content_tsv IS '전체 텍스트 검색용 tsvector';

-- tsvector 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION form_paragraphs_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('korean', COALESCE(NEW.content_text, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER tsvectorupdate BEFORE INSERT OR UPDATE
ON form_paragraphs FOR EACH ROW EXECUTE FUNCTION form_paragraphs_tsv_trigger();

-- ================================================
-- 4. form_clauses (재사용 가능한 표준 문구)
-- ================================================
CREATE TABLE form_clauses (
    id SERIAL PRIMARY KEY,
    clause_code VARCHAR(50) UNIQUE NOT NULL,
    clause_name VARCHAR(200) NOT NULL,
    clause_text TEXT NOT NULL,
    clause_category VARCHAR(100),
    applicable_types VARCHAR(50)[],
    variables JSONB,
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP
    -- embedding_vector는 pgvector 설치 후 추가
);

CREATE INDEX idx_clause_category ON form_clauses(clause_category);
CREATE INDEX idx_clause_usage ON form_clauses(usage_count DESC);

COMMENT ON TABLE form_clauses IS '재사용 가능한 표준 문구 라이브러리';
COMMENT ON COLUMN form_clauses.variables IS '변수 정의 JSON (예: {"회사명": "text", "기간": "number"})';

-- ================================================
-- 5. form_labels (라벨 정의 - 법률 개념 매핑)
-- ================================================
CREATE TABLE form_labels (
    label_code VARCHAR(50) PRIMARY KEY,
    label_name VARCHAR(200) NOT NULL,
    label_category VARCHAR(100),
    legal_concept VARCHAR(200),
    description TEXT,
    related_laws TEXT[]
    -- embedding_vector는 pgvector 설치 후 추가
);

CREATE INDEX idx_label_category ON form_labels(label_category);

COMMENT ON TABLE form_labels IS '라벨 정의 및 법률 개념 매핑';
COMMENT ON COLUMN form_labels.legal_concept IS '법률 개념 (비밀유지의무, 손해배상책임 등)';

-- ================================================
-- 6. form_label_mappings (라벨-조항 매핑)
-- ================================================
CREATE TABLE form_label_mappings (
    id SERIAL PRIMARY KEY,
    paragraph_id INTEGER NOT NULL REFERENCES form_paragraphs(id) ON DELETE CASCADE,
    label_code VARCHAR(50) NOT NULL REFERENCES form_labels(label_code) ON DELETE CASCADE,
    UNIQUE(paragraph_id, label_code)
);

CREATE INDEX idx_label_mapping_paragraph ON form_label_mappings(paragraph_id);
CREATE INDEX idx_label_mapping_label ON form_label_mappings(label_code);

COMMENT ON TABLE form_label_mappings IS '라벨과 문단 매핑 테이블';

-- ================================================
-- 7. form_entities (변수/플레이스홀더 정의)
-- ================================================
CREATE TABLE form_entities (
    id SERIAL PRIMARY KEY,
    template_id INTEGER NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    entity_type VARCHAR(50) NOT NULL,
    placeholder VARCHAR(100) NOT NULL,
    variable_name VARCHAR(100),
    data_type VARCHAR(50) DEFAULT 'text',
    is_required BOOLEAN DEFAULT false,
    validation_rule TEXT,
    default_value TEXT,
    UNIQUE(template_id, placeholder)
);

CREATE INDEX idx_entity_template ON form_entities(template_id);
CREATE INDEX idx_entity_type ON form_entities(entity_type);

COMMENT ON TABLE form_entities IS '서식 변수/플레이스홀더 정의';
COMMENT ON COLUMN form_entities.entity_type IS '엔티티 타입 (company, person, address, date, amount)';
COMMENT ON COLUMN form_entities.placeholder IS '플레이스홀더 (@회사1, @주소2 등)';

-- ================================================
-- 8. form_variations (서식 변형 관계)
-- ================================================
CREATE TABLE form_variations (
    id SERIAL PRIMARY KEY,
    base_template_id INTEGER NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    variant_template_id INTEGER NOT NULL REFERENCES form_templates(id) ON DELETE CASCADE,
    variation_type VARCHAR(50),
    differences JSONB,
    UNIQUE(base_template_id, variant_template_id)
);

CREATE INDEX idx_variation_base ON form_variations(base_template_id);
CREATE INDEX idx_variation_variant ON form_variations(variant_template_id);

COMMENT ON TABLE form_variations IS '서식 변형 관계 (기본형 ↔ 간소화형 등)';
COMMENT ON COLUMN form_variations.variation_type IS '변형 유형 (simplified, detailed, industry_specific)';

-- ================================================
-- 9. form_usage_logs (서식 사용 로그)
-- ================================================
CREATE TABLE form_usage_logs (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES form_templates(id),
    user_query TEXT,
    query_intent VARCHAR(100),
    selected_articles INTEGER[],
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    feedback_score INTEGER CHECK (feedback_score BETWEEN 1 AND 5)
);

CREATE INDEX idx_usage_template ON form_usage_logs(template_id);
CREATE INDEX idx_usage_intent ON form_usage_logs(query_intent);
CREATE INDEX idx_usage_time ON form_usage_logs(generated_at DESC);

COMMENT ON TABLE form_usage_logs IS 'LLM 서식 사용 로그 (학습용)';
COMMENT ON COLUMN form_usage_logs.query_intent IS '의도 분류 (generate, review, modify)';
COMMENT ON COLUMN form_usage_logs.feedback_score IS '사용자 피드백 점수 (1-5)';

-- ================================================
-- 완료 메시지
-- ================================================
DO $$
BEGIN
    RAISE NOTICE '✅ 서식 관리 DB 스키마 생성 완료! (Vector 제외)';
    RAISE NOTICE '📊 생성된 테이블: 9개';
    RAISE NOTICE '🔍 생성된 인덱스: 25개';
    RAISE NOTICE '⚠️  pgvector 설치 후 embedding_vector 컬럼 추가 필요';
END $$;
