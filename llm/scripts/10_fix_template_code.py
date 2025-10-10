#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""고유한 template_code를 생성하는 수정된 SQL 생성기"""

import json
import re
import hashlib
from pathlib import Path

DATA_DIR = Path(r'C:\Users\ppier\Projects\agentl2\1.데이터\extracted')
OUTPUT_FILE = Path(__file__).parent / 'bulk_insert_fixed.sql'

def escape_sql(text):
    """SQL 문자열 이스케이프"""
    if text is None:
        return 'NULL'
    return "'" + str(text).replace("'", "''") + "'"

def generate_template_code(filename: str) -> str:
    """파일명에서 고유한 template_code 생성 (파일명 전체 해시)"""
    # 파일명 전체의 해시값 생성 (충돌 방지)
    hash_value = hashlib.md5(filename.encode('utf-8')).hexdigest()[:12].upper()
    return f"DOC_{hash_value}"

def main():
    files = list(DATA_DIR.glob('*.json'))
    print(f"Found {len(files)} JSON files")

    # 중복 체크
    codes = {}
    for file in files:
        code = generate_template_code(file.name)
        if code in codes:
            print(f"DUPLICATE: {code} -> {file.name} AND {codes[code]}")
        codes[code] = file.name

    print(f"Unique codes: {len(codes)}/{len(files)}")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("-- Fixed SQL with unique template codes\n")
        f.write(f"-- Total files: {len(files)}\n\n")

        for i, file in enumerate(files, 1):
            try:
                data = json.load(open(file, 'r', encoding='utf-8'))
                doc = data['document']

                # 고유한 템플릿 코드 생성
                code = generate_template_code(file.name)

                # INSERT 문 생성
                f.write(f"INSERT INTO form_templates (template_code, template_type, template_name, status, page_count, source_file)\n")
                f.write(f"VALUES ({escape_sql(code)}, {escape_sql(doc.get('doc_type', '1001'))}, ")
                f.write(f"{escape_sql(code)}, 'active', ")
                f.write(f"{doc.get('page_count', 'NULL')}, {escape_sql(file.name)})\n")
                f.write(f"ON CONFLICT (template_code) DO UPDATE SET page_count = EXCLUDED.page_count;\n\n")

                if i % 1000 == 0:
                    print(f"Progress: {i}/{len(files)}")

            except Exception as e:
                print(f"Error at {file.name}: {e}")

    print(f"\nSQL file generated: {OUTPUT_FILE}")
    print(f"Lines: {sum(1 for _ in open(OUTPUT_FILE, 'r', encoding='utf-8'))}")
    print(f"\nExecute with:")
    print(f"docker exec -i agentl2-postgres psql -U agentl2_app -d agentl2 < {OUTPUT_FILE.name}")

if __name__ == '__main__':
    main()
