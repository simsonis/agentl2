#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON 데이터를 대량으로 PostgreSQL에 이행하는 스크립트 (로컬 실행)
"""

import json
import re
from pathlib import Path
from typing import Dict, List
import psycopg2
from psycopg2.extras import execute_batch
import sys

# DB 연결 설정 (로컬에서 Docker PostgreSQL 접속)
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'agentl2',
    'user': 'agentl2_app',
    'password': 'change_me'
}

# 데이터 디렉토리
DATA_DIR = Path(r'C:\Users\ppier\Projects\agentl2\1.데이터\extracted')

def get_db_connection():
    """DB 연결 생성"""
    return psycopg2.connect(**DB_CONFIG)

def extract_template_code(filename: str) -> str:
    """파일명에서 템플릿 코드 추출"""
    match = re.search(r'_(\d+)\.json$', filename)
    if match:
        return f"NDA_{match.group(1)}"
    return filename.replace('.json', '')

def migrate_batch(json_files: List[Path], conn, batch_size=100):
    """배치로 데이터 이행"""
    cursor = conn.cursor()
    success_count = 0
    fail_count = 0

    for i, json_file in enumerate(json_files, 1):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            doc = data['document']
            template_code = extract_template_code(json_file.name)

            # 1. 템플릿 삽입
            cursor.execute("""
                INSERT INTO form_templates (
                    template_code, template_type, template_name, status,
                    page_count, source_file
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (template_code) DO NOTHING
                RETURNING id
            """, (
                template_code,
                doc.get('doc_type', '1001'),
                f"비밀유지계약서 ({template_code})",
                'active',
                doc.get('page_count'),
                json_file.name
            ))

            result = cursor.fetchone()
            if result:
                template_id = result[0]
                success_count += 1
            else:
                # 이미 존재하는 경우 ID 가져오기
                cursor.execute("SELECT id FROM form_templates WHERE template_code = %s", (template_code,))
                template_id = cursor.fetchone()[0]

            # 배치마다 커밋
            if i % batch_size == 0:
                conn.commit()
                print(f"Progress: {i}/{len(json_files)} ({success_count} success, {fail_count} failed)")

        except Exception as e:
            fail_count += 1
            if fail_count % 10 == 0:
                print(f"Error at {json_file.name}: {str(e)[:100]}")
            continue

    conn.commit()
    return success_count, fail_count

def main():
    """메인 실행 함수"""
    print("=" * 70)
    print("JSON -> PostgreSQL 대량 데이터 이행")
    print("=" * 70)

    # JSON 파일 목록
    json_files = list(DATA_DIR.glob('*.json'))
    print(f"\n발견된 JSON 파일: {len(json_files)}개")

    if not json_files:
        print(f"WARNING: {DATA_DIR} 에 JSON 파일이 없습니다.")
        return

    # 사용자 확인
    response = input(f"\n{len(json_files)}개 파일을 이행하시겠습니까? (y/n): ")
    if response.lower() != 'y':
        print("취소되었습니다.")
        return

    # DB 연결
    try:
        conn = get_db_connection()
        print(f"DB 연결 성공: {DB_CONFIG['database']}")
    except Exception as e:
        print(f"DB 연결 실패: {e}")
        return

    # 이행 실행
    print("\n이행 시작...")
    success, failed = migrate_batch(json_files, conn, batch_size=100)

    conn.close()

    # 결과 출력
    print("\n" + "=" * 70)
    print(f"완료: {success}개")
    print(f"실패: {failed}개")
    print(f"성공률: {success * 100 / len(json_files):.1f}%")
    print("=" * 70)

    # DB 상태 확인
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM form_templates;")
    count = cursor.fetchone()[0]
    print(f"\n현재 DB에 저장된 템플릿 수: {count}개")
    conn.close()

if __name__ == '__main__':
    main()
