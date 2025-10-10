-- ================================================
-- 데이터 이행 검증 쿼리
-- ================================================

-- 0. 전체 테이블 레코드 수 확인
SELECT
    '📊 전체 테이블 레코드 수' AS section,
    '' AS detail;

SELECT
    'form_templates' AS table_name,
    COUNT(*) AS record_count,
    '서식 템플릿' AS description
FROM form_templates
UNION ALL
SELECT
    'form_articles',
    COUNT(*),
    '조항 구조'
FROM form_articles
UNION ALL
SELECT
    'form_paragraphs',
    COUNT(*),
    '문단 내용'
FROM form_paragraphs
UNION ALL
SELECT
    'form_labels',
    COUNT(*),
    '라벨 정의'
FROM form_labels
UNION ALL
SELECT
    'form_label_mappings',
    COUNT(*),
    '라벨 매핑'
FROM form_label_mappings
UNION ALL
SELECT
    'form_entities',
    COUNT(*),
    '엔티티/변수'
FROM form_entities
ORDER BY table_name;

-- 1. 템플릿 목록 확인
SELECT
    '📑 템플릿 목록' AS section,
    '' AS template_code,
    '' AS template_name,
    '' AS articles,
    '' AS paragraphs,
    '' AS entities;

SELECT
    '' AS section,
    t.template_code,
    t.template_name,
    COUNT(DISTINCT a.id)::TEXT AS articles,
    COUNT(DISTINCT p.id)::TEXT AS paragraphs,
    COUNT(DISTINCT e.id)::TEXT AS entities
FROM form_templates t
LEFT JOIN form_articles a ON a.template_id = t.id
LEFT JOIN form_paragraphs p ON p.article_id = a.id
LEFT JOIN form_entities e ON e.template_id = t.id
GROUP BY t.id, t.template_code, t.template_name
ORDER BY t.template_code
LIMIT 10;

-- 2. 특정 템플릿의 구조 확인 (NDA_0417 예시)
SELECT
    '🔍 템플릿 상세 구조 (NDA_0417)' AS section,
    '' AS level,
    '' AS article_num,
    '' AS title,
    '' AS type;

SELECT
    '' AS section,
    CASE
        WHEN a.depth = 0 THEN '📌 조항'
        WHEN a.depth = 1 THEN '  └ 하위조항'
        ELSE '    └ 세부조항'
    END AS level,
    CONCAT('제', a.article_num, '조') AS article_num,
    a.article_title AS title,
    a.article_type AS type
FROM form_articles a
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_code = 'NDA_0417'
ORDER BY a.sort_order
LIMIT 20;

-- 3. 조항별 문단 수 확인
SELECT
    '📝 조항별 문단 수' AS section,
    '' AS article_title,
    '' AS paragraph_count,
    '' AS avg_length;

SELECT
    '' AS section,
    a.article_title,
    COUNT(p.id)::TEXT AS paragraph_count,
    ROUND(AVG(LENGTH(p.content_text)))::TEXT AS avg_length
FROM form_articles a
JOIN form_templates t ON t.id = a.template_id
LEFT JOIN form_paragraphs p ON p.article_id = a.id
WHERE t.template_code = 'NDA_0417'
GROUP BY a.id, a.article_title, a.sort_order
ORDER BY a.sort_order;

-- 4. 라벨 사용 빈도
SELECT
    '🏷️  라벨 사용 빈도 TOP 10' AS section,
    '' AS label_code,
    '' AS label_name,
    '' AS usage_count;

SELECT
    '' AS section,
    l.label_code,
    l.label_name,
    COUNT(lm.id)::TEXT AS usage_count
FROM form_labels l
LEFT JOIN form_label_mappings lm ON lm.label_code = l.label_code
GROUP BY l.label_code, l.label_name
ORDER BY COUNT(lm.id) DESC
LIMIT 10;

-- 5. 엔티티/변수 유형별 분포
SELECT
    '🔤 엔티티 유형별 분포' AS section,
    '' AS entity_type,
    '' AS count,
    '' AS sample;

SELECT
    '' AS section,
    entity_type,
    COUNT(*)::TEXT AS count,
    STRING_AGG(DISTINCT placeholder, ', ') AS sample
FROM form_entities
GROUP BY entity_type
ORDER BY COUNT(*) DESC;

-- 6. 태그 사용 통계
SELECT
    '🔖 태그 사용 통계' AS section,
    '' AS tag,
    '' AS usage_count;

SELECT
    '' AS section,
    UNNEST(tags) AS tag,
    COUNT(*)::TEXT AS usage_count
FROM form_paragraphs
WHERE tags IS NOT NULL AND array_length(tags, 1) > 0
GROUP BY tag
ORDER BY COUNT(*) DESC
LIMIT 15;

-- 7. 샘플 문단 확인 (손해배상 조항)
SELECT
    '💰 손해배상 조항 샘플' AS section,
    '' AS template,
    '' AS article,
    '' AS content_preview;

SELECT
    '' AS section,
    t.template_code AS template,
    a.article_title AS article,
    LEFT(p.content_text, 100) || '...' AS content_preview
FROM form_paragraphs p
JOIN form_articles a ON a.id = p.article_id
JOIN form_templates t ON t.id = a.template_id
WHERE a.article_type = 'penalty'
LIMIT 5;

-- 8. 전체 텍스트 검색 테스트
SELECT
    '🔍 전체 텍스트 검색 테스트: "제3자"' AS section,
    '' AS template,
    '' AS article,
    '' AS match_count;

SELECT
    '' AS section,
    t.template_code AS template,
    a.article_title AS article,
    COUNT(p.id)::TEXT AS match_count
FROM form_paragraphs p
JOIN form_articles a ON a.id = p.article_id
JOIN form_templates t ON t.id = a.template_id
WHERE p.content_tsv @@ to_tsquery('korean', '제3자')
GROUP BY t.template_code, a.article_title
ORDER BY COUNT(p.id) DESC
LIMIT 10;

-- 9. 데이터 품질 체크
SELECT
    '⚠️  데이터 품질 체크' AS section,
    '' AS check_item,
    '' AS result;

SELECT
    '' AS section,
    '빈 문단 수' AS check_item,
    COUNT(*)::TEXT AS result
FROM form_paragraphs
WHERE content_text IS NULL OR TRIM(content_text) = ''
UNION ALL
SELECT
    '',
    '라벨 없는 문단 수',
    COUNT(*)::TEXT
FROM form_paragraphs p
LEFT JOIN form_label_mappings lm ON lm.paragraph_id = p.id
WHERE lm.id IS NULL
UNION ALL
SELECT
    '',
    '조항 없는 템플릿 수',
    COUNT(*)::TEXT
FROM form_templates t
LEFT JOIN form_articles a ON a.template_id = t.id
WHERE a.id IS NULL;

-- 10. 통계 요약
SELECT
    '📈 통계 요약' AS section,
    '' AS metric,
    '' AS value;

SELECT
    '' AS section,
    '전체 서식 수' AS metric,
    COUNT(*)::TEXT AS value
FROM form_templates
UNION ALL
SELECT
    '',
    '평균 조항 수',
    ROUND(AVG(article_count))::TEXT
FROM (
    SELECT COUNT(a.id) AS article_count
    FROM form_templates t
    LEFT JOIN form_articles a ON a.template_id = t.id
    GROUP BY t.id
) sub
UNION ALL
SELECT
    '',
    '평균 문단 수',
    ROUND(AVG(paragraph_count))::TEXT
FROM (
    SELECT COUNT(p.id) AS paragraph_count
    FROM form_templates t
    LEFT JOIN form_articles a ON a.template_id = t.id
    LEFT JOIN form_paragraphs p ON p.article_id = a.id
    GROUP BY t.id
) sub
UNION ALL
SELECT
    '',
    '전체 텍스트 길이 (문자)',
    TO_CHAR(SUM(LENGTH(content_text)), '999,999,999') AS value
FROM form_paragraphs;

-- 완료 메시지
SELECT
    '✅ 데이터 검증 완료!' AS message;
