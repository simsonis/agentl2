-- PostgreSQL 14+ required
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS raw_law_data (
    law_serial_no INT PRIMARY KEY,
    law_id VARCHAR(20),
    law_name_ko TEXT NOT NULL,
    law_name_zh VARCHAR(255),
    law_abbreviation VARCHAR(255),
    promulgation_no INT,
    promulgation_date DATE,
    enforce_date DATE NOT NULL,
    is_current CHAR(1),
    law_category_name VARCHAR(50),
    ministry_code VARCHAR(10),
    ministry_name VARCHAR(100),
    ministry_contact VARCHAR(100),
    revision_type_name VARCHAR(50),
    is_sub_statute CHAR(1),

    basic_info_xml TEXT,
    article_xml TEXT,
    supplement_xml TEXT,
    revision_reason_xml TEXT,
    history_xml TEXT,

    collection_id VARCHAR(50) NOT NULL,
    api_request_url TEXT NOT NULL,
    raw_response_json JSONB,
    collected_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_law_version UNIQUE (law_id, enforce_date)
);

COMMENT ON TABLE raw_law_data IS '국가법령정보센터 API를통해수집한법령원본데이터저장테이블';
COMMENT ON COLUMN raw_law_data.law_serial_no IS '특정시행일자를기준으로하는법령의고유일련번호';
COMMENT ON COLUMN raw_law_data.law_id IS '시행일자와무관하게법령자체를식별하는고유 ID (API의 MST에해당)';
COMMENT ON COLUMN raw_law_data.law_name_ko IS '법령의한글명칭';
COMMENT ON COLUMN raw_law_data.law_name_zh IS '법령의한자명칭';
COMMENT ON COLUMN raw_law_data.law_abbreviation IS '법령의약칭';
COMMENT ON COLUMN raw_law_data.promulgation_no IS '법령공포시부여된번호';
COMMENT ON COLUMN raw_law_data.promulgation_date IS '법령이공포된날짜';
COMMENT ON COLUMN raw_law_data.enforce_date IS '법령의효력이시작되는날짜 (버전관리의핵심)';
COMMENT ON COLUMN raw_law_data.is_current IS '현행법령인지, 과거의연혁법령인지여부';
COMMENT ON COLUMN raw_law_data.law_category_name IS '법령의종류 (법률, 대통령령, 총리령, 부령, 규칙등)';
COMMENT ON COLUMN raw_law_data.ministry_code IS '법령을담당하는소관부처의표준코드';
COMMENT ON COLUMN raw_law_data.ministry_name IS '소관부처의이름';
COMMENT ON COLUMN raw_law_data.ministry_contact IS '소관부처의연락처정보';
COMMENT ON COLUMN raw_law_data.revision_type_name IS '제정, 일부개정, 전부개정등제개정의형태';
COMMENT ON COLUMN raw_law_data.is_sub_statute IS '다른법령과의관계가자법인지타법인지여부';
COMMENT ON COLUMN raw_law_data.basic_info_xml IS '법령상세조회 API의 <기본정보> 태그내용';
COMMENT ON COLUMN raw_law_data.article_xml IS '법령상세조회 API의 <조문> 태그내용';
COMMENT ON COLUMN raw_law_data.supplement_xml IS '법령상세조회 API의 <부칙> 태그내용';
COMMENT ON COLUMN raw_law_data.revision_reason_xml IS '법령상세조회 API의 <제개정이유> 태그내용';
COMMENT ON COLUMN raw_law_data.history_xml IS '법령상세조회 API의 <연혁> 태그내용';
COMMENT ON COLUMN raw_law_data.collection_id IS '데이터수집파이프라인실행시부여되는고유식별자';
COMMENT ON COLUMN raw_law_data.api_request_url IS '데이터를획득한 API 요청 URL (디버깅및재현용)';
COMMENT ON COLUMN raw_law_data.raw_response_json IS 'API 응답원본 JSON. 누락된필드검증및스키마변경추적용';
COMMENT ON COLUMN raw_law_data.collected_at IS '레코드가 DB에삽입된시간';
COMMENT ON CONSTRAINT uq_law_version ON raw_law_data IS '동일한법령이다른시행일자로여러버전이존재하므로, [법령ID, 시행일자] 조합으로중복수집을방지';

CREATE TABLE IF NOT EXISTS raw_precedent_data (
    prec_serial_no INT PRIMARY KEY,
    case_name TEXT,
    case_number VARCHAR(100) NOT NULL,
    judgment_date DATE,
    court_name VARCHAR(100),
    court_code VARCHAR(10),
    case_type_code VARCHAR(10),
    case_type_name VARCHAR(50),
    judgment_type_code VARCHAR(10),
    judgment_type_name VARCHAR(50),
    judgment_result TEXT,
    referenced_statutes TEXT,
    referenced_precedents TEXT,
    summary TEXT,
    conclusion TEXT,
    reasoning TEXT,
    full_text TEXT,

    collection_id VARCHAR(50) NOT NULL,
    api_request_url TEXT NOT NULL,
    raw_response_json JSONB,
    collected_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_case_info UNIQUE (case_number, judgment_date, court_code)
);

COMMENT ON TABLE raw_precedent_data IS '국가법령정보센터 API를통해수집한판례원본데이터저장테이블';
COMMENT ON COLUMN raw_precedent_data.prec_serial_no IS '판례의고유일련번호';
COMMENT ON COLUMN raw_precedent_data.case_name IS '사건의공식명칭';
COMMENT ON COLUMN raw_precedent_data.case_number IS '법원에서부여한사건번호 (예: 2017다212121)';
COMMENT ON COLUMN raw_precedent_data.judgment_date IS '판결, 결정, 명령등이선고된날짜';
COMMENT ON COLUMN raw_precedent_data.court_name IS '판결을내린법원의이름 (예: 대법원, 서울고등법원)';
COMMENT ON COLUMN raw_precedent_data.court_code IS '법원표준코드';
COMMENT ON COLUMN raw_precedent_data.case_type_code IS '사건의종류를나타내는코드 (예: 민사, 형사)';
COMMENT ON COLUMN raw_precedent_data.case_type_name IS '사건의종류이름';
COMMENT ON COLUMN raw_precedent_data.judgment_type_code IS '심판의종류를나타내는코드 (예: 판결, 결정)';
COMMENT ON COLUMN raw_precedent_data.judgment_type_name IS '심판의종류이름';
COMMENT ON COLUMN raw_precedent_data.judgment_result IS '판결의주문결과) 내용';
COMMENT ON COLUMN raw_precedent_data.referenced_statutes IS '판결에서참조한법령조문목록';
COMMENT ON COLUMN raw_precedent_data.referenced_precedents IS '판결에서참조한다른판례목록';
COMMENT ON COLUMN raw_precedent_data.summary IS '법원이판결의핵심쟁점에대해요약한사항 (판시사항)';
COMMENT ON COLUMN raw_precedent_data.conclusion IS '판결의요지또는결론부분';
COMMENT ON COLUMN raw_precedent_data.reasoning IS '판결이유에해당하는본문';
COMMENT ON COLUMN raw_precedent_data.full_text IS '판결문전체원문';
COMMENT ON COLUMN raw_precedent_data.collection_id IS '데이터수집파이프라인실행시부여되는고유식별자';
COMMENT ON COLUMN raw_precedent_data.api_request_url IS '데이터를획득한 API 요청 URL (디버깅및재현용)';
COMMENT ON COLUMN raw_precedent_data.raw_response_json IS 'API 응답원본 JSON. 누락된필드검증및스키마변경추적용';
COMMENT ON COLUMN raw_precedent_data.collected_at IS '레코드가 DB에삽입된시간';
COMMENT ON CONSTRAINT uq_case_info ON raw_precedent_data IS '판례일련번호가없는경우를대비하여, [사건번호, 선고일자, 법원코드] 조합으로중복수집을방지하기위한 UNIQUE 제약조건';
