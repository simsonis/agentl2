#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""JSON 데이터에서 SQL INSERT 문 생성"""

import json
import re
from pathlib import Path

DATA_DIR = Path(r'C:\Users\ppier\Projects\agentl2\1.데이터\extracted')
OUTPUT_FILE = Path(__file__).parent / 'bulk_insert.sql'

def escape_sql(text):
    """SQL 문자열 이스케이프"""
    if text is None:
        return 'NULL'
    return "'" + str(text).replace("'", "''") + "'"

def main():
    files = list(DATA_DIR.glob('*.json'))
    print(f"Found {len(files)} JSON files")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("-- Auto-generated SQL from JSON files\n")
        f.write("-- Total files: {}\n\n".format(len(files)))

        for i, file in enumerate(files, 1):
            try:
                data = json.load(open(file, 'r', encoding='utf-8'))
                doc = data['document']

                # 템플릿 코드
                match = re.search(r'_(\d+)\.json$', file.name)
                code = f"NDA_{match.group(1)}" if match else file.stem

                # INSERT 문 생성
                f.write(f"INSERT INTO form_templates (template_code, template_type, template_name, status, page_count, source_file)\n")
                f.write(f"VALUES ({escape_sql(code)}, {escape_sql(doc.get('doc_type', '1001'))}, ")
                f.write(f"{escape_sql(f'비밀유지계약서 ({code})')}, 'active', ")
                f.write(f"{doc.get('page_count', 'NULL')}, {escape_sql(file.name)})\n")
                f.write(f"ON CONFLICT (template_code) DO NOTHING;\n\n")

                if i % 1000 == 0:
                    print(f"Progress: {i}/{len(files)}")

            except Exception as e:
                print(f"Error at {file.name}: {e}")

    print(f"\nSQL file generated: {OUTPUT_FILE}")
    print(f"Execute with: docker exec -i agentl2-postgres psql -U agentl2_app -d agentl2 < {OUTPUT_FILE.name}")

if __name__ == '__main__':
    main()
