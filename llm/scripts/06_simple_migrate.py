#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""간단한 JSON -> PostgreSQL 이행 (템플릿만)"""

import json
import re
import sys
from pathlib import Path
import psycopg2

DATA_DIR = Path(r'C:\Users\ppier\Projects\agentl2\1.데이터\extracted')

def main():
    # DB 연결
    conn = psycopg2.connect(
        host='localhost', port=5432, database='agentl2',
        user='agentl2_app', password='change_me'
    )
    cursor = conn.cursor()

    # JSON 파일 처리
    files = list(DATA_DIR.glob('*.json'))
    print(f"Found {len(files)} files")

    success = 0
    for i, file in enumerate(files, 1):
        try:
            data = json.load(open(file, 'r', encoding='utf-8'))
            doc = data['document']

            # 템플릿 코드 추출
            match = re.search(r'_(\d+)\.json$', file.name)
            code = f"NDA_{match.group(1)}" if match else file.stem

            # 삽입
            cursor.execute("""
                INSERT INTO form_templates (template_code, template_type, template_name, status, source_file)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (template_code) DO NOTHING
            """, (code, doc.get('doc_type', '1001'), f"비밀유지계약서 ({code})", 'active', file.name))

            success += 1
            if i % 100 == 0:
                conn.commit()
                print(f"Progress: {i}/{len(files)} ({success} inserted)")

        except Exception as e:
            if i % 100 == 0:
                print(f"Error at file {i}: {str(e)[:50]}")

    conn.commit()
    conn.close()
    print(f"\nDone: {success}/{len(files)} inserted")

if __name__ == '__main__':
    main()
