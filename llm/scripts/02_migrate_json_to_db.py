#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 데이터를 PostgreSQL DB로 이행하는 스크립트
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# DB 연결 설정
DB_CONFIG = {
    'host': 'postgres',  # Docker 내부에서는 서비스명 사용
    'port': 5432,
    'database': 'agentl2',
    'user': 'agentl2_app',
    'password': 'change_me'
}

# 데이터 디렉토리 (절대 경로)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DATA_DIR = PROJECT_ROOT / '1.데이터' / 'extracted'


def get_db_connection():
    """DB 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)


def extract_template_code(filename: str) -> str:
    """파일명에서 템플릿 코드 추출"""
    # 파일명: 비밀유지계약서_0417.json -> NDA_0417
    match = re.search(r'_(\d+)\.json$', filename)
    if match:
        return f"NDA_{match.group(1)}"
    return filename.replace('.json', '')


def extract_entities(text: str) -> List[Dict[str, str]]:
    """텍스트에서 엔티티 추출"""
    entities = []

    # 정규표현식 패턴
    patterns = {
        'company': r'@회사명?\d*|@회사\d+',
        'person': r'@성명\d*',
        'address': r'@주소\d*',
        'date': r'@날짜\d*',
        'number': r'@숫자\d*',
        'jurisdiction': r'@관할\d*',
        'position': r'@직위\d*'
    }

    for entity_type, pattern in patterns.items():
        matches = re.findall(pattern, text)
        for match in matches:
            entities.append({
                'entity_type': entity_type,
                'placeholder': match,
                'variable_name': match.replace('@', '')
            })

    return entities


def map_article_type(content_labels: List[str], article_title: str) -> str:
    """content_labels와 제목으로 조항 유형 매핑"""
    label_mapping = {
        '1001002': 'purpose',          # 목적
        '1001003': 'definition',       # 비밀정보 정의
        '1001004': 'obligation',       # 비밀유지의무
        '1001005': 'disclosure',       # 정보 공개
        '1001006': 'government',       # 정부기관 제공
        '1001007': 'usage',           # 사용 제한/복사
        '1001008': 'restriction',      # 사용 제한
        '1001009': 'return',          # 반환
        '1001010': 'ip_rights',       # 지적재산권
        '1001011': 'penalty',         # 손해배상
        '1001012': 'notification',    # 통지
        '1001013': 'term',            # 유효기간/계약기간
        '1001014': 'transfer',        # 양도금지
        '1001017': 'warranty',        # 보증
        '1001019': 'dispute',         # 분쟁해결
        '1001021': 'signature',       # 서명
        '1001022': 'date',            # 날짜
        '1001023': 'party_a',         # 갑 정보
        '1001024': 'party_a_rep',     # 갑 대표
        '1001025': 'party_b',         # 을 정보
        '1001026': 'party_b_rep',     # 을 대표
        '1001027': 'general',         # 기타
        '1001029': 'amendment',       # 계약 변경
        '1001030': 'governing_law',   # 준거법
        '1001031': 'confidentiality'  # 비밀관리
    }

    for label in content_labels:
        if label in label_mapping:
            return label_mapping[label]

    # 제목 기반 추론
    if '목적' in article_title:
        return 'purpose'
    elif '정의' in article_title:
        return 'definition'
    elif '의무' in article_title:
        return 'obligation'
    elif '손해배상' in article_title:
        return 'penalty'

    return 'general'


def extract_tags(content_text: str, content_labels: List[str]) -> List[str]:
    """문단에서 태그 추출"""
    tags = []

    # 텍스트 기반 태그
    tag_patterns = {
        '제3자_제공_금지': r'제3자.*공개|제3자.*제공',
        '서면_동의_필수': r'서면.*동의|서면.*승인',
        '복제_금지': r'복제.*금지|복사.*금지',
        '반환_의무': r'반환.*의무|반환하여야',
        '손해배상_책임': r'손해.*배상|손해를.*배상',
        '비밀_표시_필수': r'비밀.*표시|비밀유지.*표시',
        '정부기관_제공': r'법원.*제공|정부기관.*제공'
    }

    for tag, pattern in tag_patterns.items():
        if re.search(pattern, content_text):
            tags.append(tag)

    # 라벨 기반 태그
    label_tags = {
        '1001011': '손해배상_조항',
        '1001009': '자료반환_조항',
        '1001006': '정부기관_조항',
        '1001013': '유효기간_조항'
    }

    for label in content_labels:
        if label in label_tags:
            tags.append(label_tags[label])

    return list(set(tags))  # 중복 제거


def migrate_json_file(filepath: Path, conn):
    """단일 JSON 파일을 DB로 이행"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    doc = data['document']
    cursor = conn.cursor()

    try:
        # 1. form_templates 삽입
        template_code = extract_template_code(filepath.name)
        cursor.execute("""
            INSERT INTO form_templates (
                template_code, template_type, template_name, status,
                main_category, sub_category, page_count, source_file,
                total_articles
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (
            template_code,
            doc.get('doc_type', '1001'),
            f"비밀유지계약서 ({template_code})",
            'active',
            doc.get('main_category', '계약서'),
            doc.get('sub_category', '비밀유지'),
            doc.get('page_count'),
            filepath.name,
            len([sd for sd in doc.get('sub_documents', []) if sd.get('is_article_title')])
        ))
        template_id = cursor.fetchone()[0]

        # 2. 엔티티 수집 (중복 제거)
        all_entities = {}
        for sub_doc in doc.get('sub_documents', []):
            for content in sub_doc.get('contents', []):
                text = content.get('text', '')
                entities = extract_entities(text)
                for entity in entities:
                    key = entity['placeholder']
                    if key not in all_entities:
                        all_entities[key] = entity

        # 3. form_entities 삽입
        if all_entities:
            entity_values = [
                (template_id, e['entity_type'], e['placeholder'], e['variable_name'],
                 'text', e['placeholder'].endswith('1'))  # 첫 번째 엔티티는 필수로 간주
                for e in all_entities.values()
            ]
            execute_values(cursor, """
                INSERT INTO form_entities
                (template_id, entity_type, placeholder, variable_name, data_type, is_required)
                VALUES %s
            """, entity_values)

        # 4. 조항 처리
        article_map = {}  # sub_document_id -> article_id 매핑

        for sub_doc in doc.get('sub_documents', []):
            article_num = sub_doc.get('article')

            if article_num and sub_doc.get('is_article_title'):
                # 조항 제목인 경우
                content_text = sub_doc.get('contents', [{}])[0].get('text', '')
                content_labels = sub_doc.get('content_labels', [])

                cursor.execute("""
                    INSERT INTO form_articles (
                        template_id, article_num, article_title, article_type,
                        sort_order, depth, is_required
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    template_id,
                    article_num,
                    content_text,
                    map_article_type(content_labels, content_text),
                    sub_doc.get('sort_order'),
                    sub_doc.get('depth', 0),
                    article_num in [1, 2, 3, 4]  # 초반 조항들은 필수로 간주
                ))
                article_id = cursor.fetchone()[0]
                article_map[sub_doc['id']] = article_id

        # 5. 문단 처리
        for sub_doc in doc.get('sub_documents', []):
            article_num = sub_doc.get('article')

            # 조항에 속한 문단만 처리
            if article_num and not sub_doc.get('is_article_title'):
                # 해당 조항의 article_id 찾기
                article_id = None
                for sd_id, a_id in article_map.items():
                    # 같은 article 번호를 가진 조항 찾기
                    for sd in doc['sub_documents']:
                        if sd['id'] == sd_id and sd.get('article') == article_num:
                            article_id = a_id
                            break
                    if article_id:
                        break

                if not article_id:
                    continue

                content_text = sub_doc.get('contents', [{}])[0].get('text', '')
                content_labels = sub_doc.get('content_labels', [])

                cursor.execute("""
                    INSERT INTO form_paragraphs (
                        article_id, paragraph_num, sub_paragraph_num, depth,
                        content_text, format_code, sort_order, is_article_title, tags
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    article_id,
                    sub_doc.get('paragraph'),
                    sub_doc.get('subParagraph'),
                    sub_doc.get('depth', 1),
                    content_text,
                    sub_doc.get('format_content'),
                    sub_doc.get('sort_order'),
                    False,
                    extract_tags(content_text, content_labels)
                ))
                paragraph_id = cursor.fetchone()[0]

                # 6. 라벨 매핑
                if content_labels:
                    # 라벨이 없으면 삽입
                    for label_code in content_labels:
                        cursor.execute("""
                            INSERT INTO form_labels (label_code, label_name, label_category)
                            VALUES (%s, %s, %s)
                            ON CONFLICT (label_code) DO NOTHING
                        """, (label_code, f"라벨_{label_code}", 'general'))

                        cursor.execute("""
                            INSERT INTO form_label_mappings (paragraph_id, label_code)
                            VALUES (%s, %s)
                            ON CONFLICT DO NOTHING
                        """, (paragraph_id, label_code))

        conn.commit()
        print(f"[OK] {filepath.name} 이행 완료 (template_id: {template_id})")
        return template_id

    except Exception as e:
        conn.rollback()
        print(f"[FAIL] {filepath.name} 이행 실패: {e}")
        raise


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("JSON -> PostgreSQL 데이터 이행 시작")
    print("=" * 60)

    # JSON 파일 목록 (전체)
    json_files = list(DATA_DIR.glob('*.json'))
    print(f"\n[OK] 발견된 JSON 파일: {len(json_files)}개")

    if not json_files:
        print(f"[WARNING] {DATA_DIR} 에 JSON 파일이 없습니다.")
        return

    # DB 연결
    conn = get_db_connection()
    print(f"[OK] DB 연결 성공: {DB_CONFIG['database']}")

    # 이행 실행
    migrated_count = 0
    failed_count = 0

    for json_file in json_files:
        try:
            migrate_json_file(json_file, conn)
            migrated_count += 1
        except Exception as e:
            failed_count += 1
            print(f"   [ERROR] 상세 에러: {str(e)}")

    conn.close()

    # 결과 출력
    print("\n" + "=" * 60)
    print(f"[OK] 이행 완료: {migrated_count}개")
    print(f"[FAIL] 이행 실패: {failed_count}개")
    print("=" * 60)


if __name__ == '__main__':
    main()
