#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON을 직접 PostgreSQL에 이행 (Python으로 직접 연결)"""

import json
import re
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

DATA_DIR = Path(r'C:\Users\ppier\Projects\agentl2\1.데이터\extracted')

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'agentl2',
    'user': 'agentl2_app',
    'password': 'change_me'
}

def map_article_type(labels, title):
    """조항 유형 매핑"""
    mapping = {
        '1001002': 'purpose', '1001003': 'definition', '1001004': 'obligation',
        '1001008': 'restriction', '1001009': 'return', '1001010': 'ip_rights',
        '1001011': 'penalty', '1001013': 'term'
    }
    for label in labels:
        if label in mapping:
            return mapping[label]
    return 'general'

def extract_tags(text):
    """태그 추출"""
    tags = []
    if '제3자' in text:
        tags.append('제3자_관련')
    if '손해배상' in text:
        tags.append('손해배상_조항')
    if '서면' in text and '동의' in text:
        tags.append('서면_동의_필수')
    return tags

def migrate_file(filepath, conn):
    """단일 파일 이행"""
    cursor = conn.cursor()

    data = json.load(open(filepath, 'r', encoding='utf-8'))
    doc = data['document']

    # 템플릿 코드
    match = re.search(r'_(\d+)\.json$', filepath.name)
    code = f"NDA_{match.group(1)}" if match else filepath.stem

    # 1. 템플릿 삽입/업데이트
    cursor.execute("""
        INSERT INTO form_templates (template_code, template_type, template_name, status, page_count, source_file)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (template_code) DO UPDATE SET page_count = EXCLUDED.page_count
        RETURNING id
    """, (code, doc.get('doc_type', '1001'), code, 'active', doc.get('page_count'), filepath.name))

    template_id = cursor.fetchone()[0]

    # 2. 조항 삽입
    articles_inserted = {}
    for sub_doc in doc.get('sub_documents', []):
        article_num = sub_doc.get('article')
        if article_num and sub_doc.get('is_article_title'):
            content = sub_doc.get('contents', [{}])[0].get('text', '')
            labels = sub_doc.get('content_labels', [])

            cursor.execute("""
                INSERT INTO form_articles (template_id, article_num, article_title, article_type, sort_order, depth)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                RETURNING id
            """, (template_id, article_num, content, map_article_type(labels, content),
                  sub_doc.get('sort_order'), sub_doc.get('depth', 0)))

            result = cursor.fetchone()
            if result:
                articles_inserted[article_num] = result[0]

    # 3. 문단 삽입
    paragraphs_count = 0
    for sub_doc in doc.get('sub_documents', []):
        article_num = sub_doc.get('article')
        if article_num and not sub_doc.get('is_article_title') and article_num in articles_inserted:
            content = sub_doc.get('contents', [{}])[0].get('text', '')
            if content and len(content) > 10:
                tags = extract_tags(content)

                cursor.execute("""
                    INSERT INTO form_paragraphs (article_id, paragraph_num, content_text, sort_order, tags)
                    VALUES (%s, %s, %s, %s, %s)
                """, (articles_inserted[article_num], sub_doc.get('paragraph'), content[:1000],
                      sub_doc.get('sort_order'), tags))
                paragraphs_count += 1

                # 라벨 처리
                labels = sub_doc.get('content_labels', [])
                if labels:
                    paragraph_id = cursor.fetchone()
                    # ... (라벨 생략)

    return len(articles_inserted), paragraphs_count

def main():
    files = list(DATA_DIR.glob('*.json'))
    print(f"Found {len(files)} files")

    process_count = int(input(f"Process how many? (1-{len(files)}): ") or "50")
    files = files[:process_count]

    conn = psycopg2.connect(**DB_CONFIG)
    print("Connected to DB")

    success_files = 0
    total_articles = 0
    total_paragraphs = 0

    for i, file in enumerate(files, 1):
        try:
            articles, paragraphs = migrate_file(file, conn)
            total_articles += articles
            total_paragraphs += paragraphs
            success_files += 1

            if i % 10 == 0:
                conn.commit()
                print(f"Progress: {i}/{len(files)} | Articles: {total_articles} | Paragraphs: {total_paragraphs}")

        except Exception as e:
            print(f"Error at {file.name}: {str(e)[:80]}")
            conn.rollback()

    conn.commit()
    conn.close()

    print(f"\nCompleted!")
    print(f"Files: {success_files}/{len(files)}")
    print(f"Articles: {total_articles}")
    print(f"Paragraphs: {total_paragraphs}")

if __name__ == '__main__':
    main()
