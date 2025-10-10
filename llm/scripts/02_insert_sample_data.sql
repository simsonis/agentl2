-- ================================================
-- 샘플 데이터 삽입 (테스트용)
-- ================================================

-- 1. 템플릿 샘플 삽입
INSERT INTO form_templates (
    template_code, template_type, template_name, status,
    main_category, sub_category, page_count, total_articles, source_file
) VALUES
('NDA_001', '1001', '비밀유지계약서 (기업간 표준형)', 'active', '계약서', '비밀유지', 5, 11, 'sample_nda_001.json'),
('NDA_002', '1001', '비밀유지계약서 (근로자용)', 'active', '계약서', '비밀유지', 4, 12, 'sample_nda_002.json'),
('NDA_003', '1001', '비밀유지계약서 (간소화형)', 'active', '계약서', '비밀유지', 3, 10, 'sample_nda_003.json');

-- 2. 조항 샘플 삽입 (NDA_001)
INSERT INTO form_articles (
    template_id, article_num, article_title, article_type, sort_order, depth, is_required
)
SELECT t.id, 1, '제1조 (계약의 목적)', 'purpose', 1, 0, true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 2, '제2조 (비밀정보의 정의 및 요건)', 'definition', 2, 0, true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 3, '제3조 (비밀유지 의무 및 비밀정보의 관리)', 'obligation', 3, 0, true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 4, '제4조 (비밀정보의 사용 제한)', 'restriction', 4, 0, true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 10, '제10조 (손해배상 등)', 'penalty', 10, 0, true
FROM form_templates t WHERE t.template_code = 'NDA_001';

-- 3. 문단 샘플 삽입
INSERT INTO form_paragraphs (
    article_id, paragraph_num, content_text, format_code, sort_order, tags
)
SELECT
    a.id,
    NULL,
    '이 계약은 정보제공자와 정보수령자가 양 당사자 간의 향후 진행할 사업(이하 "목적 사업")에 관하여 상호 제공하는 "비밀정보"를 보호하기 위하여 필요한 사항을 규정함에 그 목적이 있다.',
    '1001AAC',
    1,
    ARRAY['계약목적', '비밀정보_보호']
FROM form_articles a
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_code = 'NDA_001' AND a.article_num = 1
UNION ALL
SELECT
    a.id,
    1,
    '이 계약서에서 "비밀정보"란 목적 사업과 관련하여 양 당사자가 업무를 진행하는 과정에서 어느 일방 당사자가 반대 당사자에게 서면, 구두, 전자적 방법에 의한 전송 또는 기타의 방법으로 제공하는 모든 노하우, 기술, 공정, 도면, 설계, 디자인, 코드, 실험, 시제품, 스펙, 데이터, 프로그램, 명세서, 아이디어, 사업정보, 경영정보 등 일체의 정보로서 유․무형의 여부 및 그 기록 형태를 불문한다.',
    '1001AAC',
    1,
    ARRAY['비밀정보_정의', '제공방법']
FROM form_articles a
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_code = 'NDA_001' AND a.article_num = 2
UNION ALL
SELECT
    a.id,
    1,
    '정보수령자는 정보제공자의 서면 동의 없이 비밀정보를 고의 또는 과실로 제3자에게 공개, 제공 또는 누설한 경우 등 이 계약을 위반함으로 인하여 정보제공자가 입은 손해를 배상하여야 한다.',
    '1001AAC',
    1,
    ARRAY['손해배상_조항', '제3자_제공_금지', '서면_동의_필수']
FROM form_articles a
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_code = 'NDA_001' AND a.article_num = 10;

-- 4. 라벨 정의 삽입
INSERT INTO form_labels (label_code, label_name, label_category, legal_concept, description) VALUES
('1001001', '전문', '계약구성요소', '계약의 전문', '계약 체결 당사자 및 배경 설명'),
('1001002', '목적 조항', '계약구성요소', '계약의 목적', '계약 체결의 목적을 명시'),
('1001003', '비밀정보 정의', '의무조항', '비밀정보의 범위', '비밀정보의 정의 및 범위 규정'),
('1001004', '비밀유지의무', '의무조항', '비밀유지 의무', '비밀정보 보호 의무 규정'),
('1001005', '정보 공개 제한', '의무조항', '제3자 제공 금지', '제3자에 대한 정보 공개 제한'),
('1001007', '사용 제한', '의무조항', '비밀정보 사용 제한', '비밀정보의 사용 범위 제한'),
('1001009', '반환 의무', '의무조항', '자료 반환', '비밀정보 반환 의무'),
('1001010', '지적재산권', '권리조항', '지식재산권', '지적재산권 관련 규정'),
('1001011', '손해배상', '책임조항', '손해배상 책임', '계약 위반 시 손해배상'),
('1001013', '계약기간', '일반조항', '유효기간', '계약의 유효기간'),
('1001019', '분쟁해결', '일반조항', '관할법원', '분쟁 해결 절차'),
('1001027', '기타', '일반조항', '기타사항', '기타 일반 조항')
ON CONFLICT (label_code) DO NOTHING;

-- 5. 라벨 매핑
INSERT INTO form_label_mappings (paragraph_id, label_code)
SELECT p.id, '1001002'
FROM form_paragraphs p
JOIN form_articles a ON a.id = p.article_id
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_code = 'NDA_001' AND a.article_num = 1
UNION ALL
SELECT p.id, '1001003'
FROM form_paragraphs p
JOIN form_articles a ON a.id = p.article_id
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_code = 'NDA_001' AND a.article_num = 2
UNION ALL
SELECT p.id, '1001011'
FROM form_paragraphs p
JOIN form_articles a ON a.id = p.article_id
JOIN form_templates t ON t.id = a.template_id
WHERE t.template_code = 'NDA_001' AND a.article_num = 10;

-- 6. 엔티티 삽입
INSERT INTO form_entities (
    template_id, entity_type, placeholder, variable_name, data_type, is_required
)
SELECT t.id, 'company', '@회사1', '갑_회사명', 'text', true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 'company', '@회사2', '을_회사명', 'text', true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 'address', '@주소1', '갑_주소', 'text', true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 'address', '@주소2', '을_주소', 'text', true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 'person', '@성명1', '갑_대표자명', 'text', true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 'person', '@성명2', '을_대표자명', 'text', true
FROM form_templates t WHERE t.template_code = 'NDA_001'
UNION ALL
SELECT t.id, 'number', '@숫자', '유효기간_년수', 'number', false
FROM form_templates t WHERE t.template_code = 'NDA_001';

-- 완료 메시지
DO $$
BEGIN
    RAISE NOTICE '✅ 샘플 데이터 삽입 완료!';
    RAISE NOTICE '📊 템플릿: 3개';
    RAISE NOTICE '📋 조항: 5개';
    RAISE NOTICE '📝 문단: 3개';
    RAISE NOTICE '🏷️  라벨: 12개';
    RAISE NOTICE '🔤 엔티티: 7개';
END $$;
