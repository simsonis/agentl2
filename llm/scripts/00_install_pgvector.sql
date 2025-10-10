-- ================================================
-- pgvector Extension 설치
-- ================================================

-- 1. pgvector extension 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. 설치 확인
SELECT
    extname AS extension_name,
    extversion AS version
FROM pg_extension
WHERE extname = 'vector';

-- 3. 사용 가능 여부 확인
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'vector'
    ) THEN
        RAISE NOTICE '✅ pgvector extension 설치 완료!';
        RAISE NOTICE '📊 Vector 타입을 사용할 수 있습니다.';
    ELSE
        RAISE EXCEPTION '❌ pgvector extension 설치 실패!';
    END IF;
END $$;
