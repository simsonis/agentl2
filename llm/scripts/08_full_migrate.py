#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON 전체 데이터를 PostgreSQL로 완전 이행 (조항+문단+라벨+엔티티)"""

import json
import re
from pathlib import Path
import sys

DATA_DIR = Path(r'C:\Users\ppier\Projects\agentl2\1.데이터\extracted')
OUTPUT_FILE = Path(__file__).parent / 'full_insert.sql'

def escape_sql(text):
    """SQL 문자열 이스케이프"""
    if text is None:
        return 'NULL'
    return "'" + str(text).replace("'", "''").replace('\\', '\\\\') + "'"

def escape_array(items):
    """배열을 PostgreSQL ARRAY 형식으로 변환"""
    if not items:
        return "'{}'"
    escaped = [item.replace("'", "''") for item in items]
    return "ARRAY[" + ",".join([f"'{item}'" for item in escaped]) + "]"

def map_article_type(content_labels, title):
    """조항 유형 매핑"""
    mapping = {
        '1001002': 'purpose', '1001003': 'definition', '1001004': 'obligation',
        '1001005': 'disclosure', '1001006': 'government', '1001007': 'usage',
        '1001008': 'restriction', '1001009': 'return', '1001010': 'ip_rights',
        '1001011': 'penalty', '1001013': 'term', '1001017': 'warranty',
        '1001019': 'dispute', '1001027': 'general'
    }
    for label in content_labels:
        if label in mapping:
            return mapping[label]
    return 'general'

def extract_tags(text, labels):
    """태그 추출"""
    tags = []
    if '제3자' in text and ('공개' in text or '제공' in text):
        tags.append('제3자_제공_금지')
    if '서면' in text and '동의' in text:
        tags.append('서면_동의_필수')
    if '손해' in text and '배상' in text:
        tags.append('손해배상_조항')
    return tags

def main():
    files = list(DATA_DIR.glob('*.json'))
    print(f"Found {len(files)} JSON files")

    # 처리할 파일 수 제한 (테스트용)
    process_count = int(input(f"Process how many files? (1-{len(files)}): ") or "100")
    files = files[:process_count]

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("-- Full migration SQL\n")
        f.write("-- Including: templates, articles, paragraphs, labels, entities\n\n")
        f.write("BEGIN;\n\n")

        for i, file in enumerate(files, 1):
            try:
                data = json.load(open(file, 'r', encoding='utf-8'))
                doc = data['document']

                # 템플릿 코드
                match = re.search(r'_(\d+)\.json$', file.name)
                code = f"NDA_{match.group(1)}" if match else file.stem

                # 1. 템플릿 삽입
                f.write(f"-- File: {file.name}\n")
                f.write(f"INSERT INTO form_templates (template_code, template_type, template_name, status, page_count, source_file)\n")
                f.write(f"VALUES ({escape_sql(code)}, {escape_sql(doc.get('doc_type', '1001'))}, ")
                f.write(f"{escape_sql(f'{code}')}, 'active', {doc.get('page_count', 'NULL')}, {escape_sql(file.name)})\n")
                f.write(f"ON CONFLICT (template_code) DO UPDATE SET source_file = EXCLUDED.source_file\n")
                f.write(f"RETURNING id INTO @template_id;\n\n")

                # 실제로는 WITH를 사용하여 ID를 가져와야 함
                f.write(f"DO $$\n")
                f.write(f"DECLARE\n")
                f.write(f"  v_template_id INTEGER;\n")
                f.write(f"  v_article_id INTEGER;\n")
                f.write(f"  v_paragraph_id INTEGER;\n")
                f.write(f"BEGIN\n")
                f.write(f"  SELECT id INTO v_template_id FROM form_templates WHERE template_code = {escape_sql(code)};\n\n")

                # 2. 조항 처리
                articles_map = {}  # sub_doc_id -> article 번호 매핑

                for sub_doc in doc.get('sub_documents', []):
                    article_num = sub_doc.get('article')
                    if article_num and sub_doc.get('is_article_title'):
                        content = sub_doc.get('contents', [{}])[0].get('text', '')
                        labels = sub_doc.get('content_labels', [])
                        article_type = map_article_type(labels, content)

                        f.write(f"  -- Article {article_num}\n")
                        f.write(f"  INSERT INTO form_articles (template_id, article_num, article_title, article_type, sort_order, depth)\n")
                        f.write(f"  VALUES (v_template_id, {article_num}, {escape_sql(content)}, '{article_type}', {sub_doc.get('sort_order')}, {sub_doc.get('depth', 0)})\n")
                        f.write(f"  RETURNING id INTO v_article_id;\n\n")

                        articles_map[article_num] = True

                # 3. 문단 처리
                for sub_doc in doc.get('sub_documents', []):
                    article_num = sub_doc.get('article')
                    if article_num and not sub_doc.get('is_article_title') and article_num in articles_map:
                        content = sub_doc.get('contents', [{}])[0].get('text', '')
                        if content and len(content) > 10:  # 유의미한 내용만
                            labels = sub_doc.get('content_labels', [])
                            tags = extract_tags(content, labels)

                            f.write(f"  -- Paragraph for Article {article_num}\n")
                            f.write(f"  SELECT id INTO v_article_id FROM form_articles WHERE template_id = v_template_id AND article_num = {article_num} LIMIT 1;\n")
                            f.write(f"  INSERT INTO form_paragraphs (article_id, paragraph_num, content_text, sort_order, tags)\n")
                            f.write(f"  VALUES (v_article_id, {sub_doc.get('paragraph', 'NULL')}, {escape_sql(content[:500])}, ")
                            f.write(f"{sub_doc.get('sort_order')}, {escape_array(tags)})\n")
                            f.write(f"  RETURNING id INTO v_paragraph_id;\n\n")

                            # 라벨 매핑
                            if labels:
                                for label in labels[:3]:  # 최대 3개만
                                    f.write(f"  INSERT INTO form_labels (label_code, label_name, label_category) ")
                                    f.write(f"VALUES ('{label}', 'Label_{label}', 'general') ON CONFLICT DO NOTHING;\n")
                                    f.write(f"  INSERT INTO form_label_mappings (paragraph_id, label_code) ")
                                    f.write(f"VALUES (v_paragraph_id, '{label}') ON CONFLICT DO NOTHING;\n")

                f.write(f"END $$;\n\n")

                if i % 10 == 0:
                    f.write(f"COMMIT;\nBEGIN;\n\n")
                    print(f"Progress: {i}/{len(files)}")

            except Exception as e:
                print(f"Error at {file.name}: {str(e)[:100]}")

        f.write("COMMIT;\n")

    print(f"\nSQL file generated: {OUTPUT_FILE}")
    print(f"Lines: {sum(1 for _ in open(OUTPUT_FILE, 'r', encoding='utf-8'))}")
    print(f"\nExecute with:")
    print(f"docker exec -i agentl2-postgres psql -U agentl2_app -d agentl2 < {OUTPUT_FILE.name}")

if __name__ == '__main__':
    main()
