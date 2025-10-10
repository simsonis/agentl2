#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""조항+문단+라벨 전체 데이터를 SQL로 생성"""

import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(r'C:\Users\ppier\Projects\agentl2\1.데이터\extracted')
OUTPUT_FILE = Path(__file__).parent / 'full_content_insert.sql'

def escape_sql(text):
    """SQL 문자열 이스케이프"""
    if text is None:
        return 'NULL'
    text = str(text).replace("\\", "\\\\").replace("'", "''")
    # 너무 긴 텍스트는 잘라냄
    if len(text) > 5000:
        text = text[:5000] + '...[truncated]'
    return f"'{text}'"

def generate_template_code(filename: str) -> str:
    """파일명에서 template_code 생성"""
    hash_value = hashlib.md5(filename.encode('utf-8')).hexdigest()[:12].upper()
    return f"DOC_{hash_value}"

def map_article_type(labels, title):
    """조항 유형 매핑"""
    mapping = {
        '1001002': 'purpose', '1001003': 'definition', '1001004': 'obligation',
        '1001011': 'penalty', '1001013': 'term', '1001019': 'dispute'
    }
    for label in labels:
        if label in mapping:
            return mapping[label]
    return 'general'

def main():
    files = list(DATA_DIR.glob('*.json'))
    print(f"Found {len(files)} JSON files")

    # 처리할 파일 수 제한
    limit = int(input(f"Process how many files? (1-{len(files)}, default=100): ") or "100")
    files = files[:limit]

    stats = {'templates': 0, 'articles': 0, 'paragraphs': 0, 'labels': set()}

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("-- Full content migration: articles + paragraphs + labels\n")
        f.write(f"-- Processing {len(files)} files\n\n")
        f.write("BEGIN;\n\n")

        for file_idx, filepath in enumerate(files, 1):
            try:
                data = json.load(open(filepath, 'r', encoding='utf-8'))
                doc = data['document']
                template_code = generate_template_code(filepath.name)

                # 조항 수집 (제목만)
                articles = {}
                for sub_doc in doc.get('sub_documents', []):
                    article_num = sub_doc.get('article')
                    if article_num and sub_doc.get('is_article_title'):
                        content = sub_doc.get('contents', [{}])[0].get('text', '')
                        if content:
                            articles[article_num] = {
                                'title': content,
                                'labels': sub_doc.get('content_labels', []),
                                'sort_order': sub_doc.get('sort_order', 0),
                                'depth': sub_doc.get('depth', 0)
                            }

                # 조항 삽입
                for article_num, article_data in sorted(articles.items()):
                    article_type = map_article_type(article_data['labels'], article_data['title'])

                    f.write(f"-- File: {filepath.name}, Article {article_num}\n")
                    f.write(f"INSERT INTO form_articles (template_id, article_num, article_title, article_type, sort_order, depth)\n")
                    f.write(f"SELECT id, {article_num}, {escape_sql(article_data['title'])}, '{article_type}', ")
                    f.write(f"{article_data['sort_order']}, {article_data['depth']}\n")
                    f.write(f"FROM form_templates WHERE template_code = '{template_code}'\n")
                    f.write(f"ON CONFLICT DO NOTHING;\n\n")

                    stats['articles'] += 1

                # 문단 삽입
                for sub_doc in doc.get('sub_documents', []):
                    article_num = sub_doc.get('article')
                    if article_num and not sub_doc.get('is_article_title') and article_num in articles:
                        content = sub_doc.get('contents', [{}])[0].get('text', '')
                        if content and len(content) > 10:
                            para_num = sub_doc.get('paragraph')
                            sub_para_num = sub_doc.get('subParagraph')

                            # 태그 추출
                            tags = []
                            if '제3자' in content:
                                tags.append('제3자_관련')
                            if '손해배상' in content:
                                tags.append('손해배상')

                            f.write(f"INSERT INTO form_paragraphs (article_id, paragraph_num, sub_paragraph_num, content_text, sort_order, tags)\n")
                            f.write(f"SELECT a.id, {para_num or 'NULL'}, {sub_para_num or 'NULL'}, {escape_sql(content)}, ")
                            f.write(f"{sub_doc.get('sort_order', 0)}, ")

                            if tags:
                                f.write(f"ARRAY{tags}::TEXT[]\n")
                            else:
                                f.write(f"NULL\n")

                            f.write(f"FROM form_articles a\n")
                            f.write(f"JOIN form_templates t ON t.id = a.template_id\n")
                            f.write(f"WHERE t.template_code = '{template_code}' AND a.article_num = {article_num}\n")
                            f.write(f"ON CONFLICT DO NOTHING;\n\n")

                            stats['paragraphs'] += 1

                            # 라벨 처리
                            labels = sub_doc.get('content_labels', [])
                            if labels:
                                for label in labels[:3]:  # 최대 3개
                                    stats['labels'].add(label)
                                    f.write(f"INSERT INTO form_labels (label_code, label_name) ")
                                    f.write(f"VALUES ('{label}', 'Label_{label}') ON CONFLICT DO NOTHING;\n")

                stats['templates'] += 1

                # 10개마다 커밋
                if file_idx % 10 == 0:
                    f.write(f"\nCOMMIT;\nBEGIN;\n\n")
                    print(f"Progress: {file_idx}/{len(files)} | Articles: {stats['articles']} | Paragraphs: {stats['paragraphs']}")

            except Exception as e:
                print(f"Error at {filepath.name}: {str(e)[:100]}")

        f.write("COMMIT;\n")

    print(f"\n{'='*60}")
    print(f"SQL Generated: {OUTPUT_FILE}")
    print(f"Templates: {stats['templates']}")
    print(f"Articles: {stats['articles']}")
    print(f"Paragraphs: {stats['paragraphs']}")
    print(f"Unique Labels: {len(stats['labels'])}")
    print(f"{'='*60}")
    print(f"\nExecute with:")
    print(f"docker exec -i agentl2-postgres psql -U agentl2_app -d agentl2 < {OUTPUT_FILE.name}")

if __name__ == '__main__':
    main()
