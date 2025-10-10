#!/usr/bin/env python3
"""
Minimal loader: ingest .data JSONL datasets into a single staging table.

Features
- Creates table if missing: ml_raw_samples
- Walks `.data/<dataset>/*.jsonl` and loads line-by-line JSON into JSONB
- Derives `dataset` from folder name and `split` from filename (train|valid|test|test2)
- Idempotent: unique(dataset, split, path, line_no) ON CONFLICT DO NOTHING
- Batched inserts via psycopg2.extras.execute_values

Usage
  python -m llm.scripts.load_ml_data --root .data [--dataset summarization] [--split train] [--batch-size 2000]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_values


# ---------- DB helpers ----------

def _dsn_from_env() -> str:
    """Build a psycopg2 DSN string from environment variables.

    Honors DATABASE_URL but strips "+psycopg2" scheme suffix if present.
    Falls back to POSTGRES_* envs or sane defaults.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        # Normalize possible sqlalchemy-style url
        url = url.replace("postgresql+psycopg2://", "postgresql://")
        url = url.replace("postgres+psycopg2://", "postgresql://")
        return url

    host = os.getenv("POSTGRES_HOST", os.getenv("PGHOST", "localhost"))
    port = os.getenv("POSTGRES_PORT", os.getenv("PGPORT", "5432"))
    user = os.getenv("POSTGRES_USER", os.getenv("PGUSER", "agentl2_app"))
    password = os.getenv("POSTGRES_PASSWORD", os.getenv("PGPASSWORD", "change_me"))
    db = os.getenv("POSTGRES_DB", os.getenv("PGDATABASE", "agentl2"))
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _ensure_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ml_raw_samples (
              id          BIGSERIAL PRIMARY KEY,
              dataset     TEXT NOT NULL,
              split       TEXT NOT NULL,
              path        TEXT NOT NULL,
              line_no     INTEGER NOT NULL,
              payload     JSONB NOT NULL,
              sha256      CHAR(64) NOT NULL,
              loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
              UNIQUE(dataset, split, path, line_no)
            );

            CREATE INDEX IF NOT EXISTS ix_ml_raw_samples_ds_split
              ON ml_raw_samples (dataset, split);

            CREATE INDEX IF NOT EXISTS ix_ml_raw_samples_payload
              ON ml_raw_samples USING gin (payload jsonb_path_ops);
            """
        )
    conn.commit()


# ---------- FS helpers ----------

SPLIT_NAMES = {"train", "valid", "test", "test2"}


@dataclass
class FileMeta:
    dataset: str
    split: str
    path: Path


def discover_jsonl(root: Path, dataset_filter: Optional[str], split_filter: Optional[str]) -> Iterable[FileMeta]:
    if not root.exists():
        return []

    for dataset_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        dataset = dataset_dir.name
        if dataset_filter and dataset != dataset_filter:
            continue
        for fp in sorted(dataset_dir.glob("*.jsonl")):
            split = fp.stem.lower()
            split = split if split in SPLIT_NAMES else "unknown"
            if split_filter and split != split_filter:
                continue
            yield FileMeta(dataset=dataset, split=split, path=fp)


# ---------- Load logic ----------

def _json_dumps_deterministic(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_file(conn, root: Path, meta: FileMeta, batch_size: int, dry_run: bool = False) -> Tuple[int, int]:
    inserted, skipped = 0, 0
    rel_path = meta.path.relative_to(root).as_posix()

    def _iter_rows() -> Iterable[Tuple[str, str, str, int, str, str]]:
        with meta.path.open("r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed lines but keep progressing
                    continue
                payload_text = _json_dumps_deterministic(obj)
                yield (
                    meta.dataset,
                    meta.split,
                    rel_path,
                    i,
                    payload_text,
                    _sha256(payload_text),
                )

    rows_buffer: List[Tuple[str, str, str, int, str, str]] = []
    with conn.cursor() as cur:
        for row in _iter_rows():
            rows_buffer.append(row)
            if len(rows_buffer) >= batch_size:
                if not dry_run:
                    inserted += _flush(cur, rows_buffer)
                rows_buffer.clear()
        if rows_buffer:
            if not dry_run:
                inserted += _flush(cur, rows_buffer)
            rows_buffer.clear()
    if not dry_run:
        conn.commit()
    else:
        skipped = inserted
        inserted = 0
    return inserted, skipped


def _flush(cur, rows: List[Tuple[str, str, str, int, str, str]]) -> int:
    # rows: (dataset, split, path, line_no, payload_text, sha256)
    sql = (
        "INSERT INTO ml_raw_samples (dataset, split, path, line_no, payload, sha256) "
        "VALUES %s ON CONFLICT (dataset, split, path, line_no) DO NOTHING"
    )
    # Cast payload text -> jsonb server-side for speed
    template = "(%s, %s, %s, %s, %s::jsonb, %s)"
    execute_values(cur, sql, rows, template=template)
    return cur.rowcount or 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Load .data JSONL into ml_raw_samples")
    ap.add_argument("--root", default=".data", help="Root folder containing datasets")
    ap.add_argument("--dataset", default=None, help="Filter by dataset folder name")
    ap.add_argument("--split", default=None, choices=list(SPLIT_NAMES), help="Filter by split filename")
    ap.add_argument("--batch-size", type=int, default=2000, help="Batch size for inserts")
    ap.add_argument("--dry-run", action="store_true", help="Parse only; do not write to DB")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    files = list(discover_jsonl(root, args.dataset, args.split))
    print(f"[INFO] Discovered {len(files)} jsonl files under {root}")
    if not files:
        return

    dsn = _dsn_from_env()
    conn = psycopg2.connect(dsn)
    try:
        _ensure_schema(conn)
        total_inserted = 0
        for meta in files:
            print(f"[LOAD] dataset={meta.dataset} split={meta.split} file={meta.path}")
            ins, _ = load_file(conn, root, meta, batch_size=args.batch_size, dry_run=args.dry_run)
            total_inserted += ins
        if args.dry_run:
            print("[DONE] Dry-run complete. No rows inserted.")
        else:
            print(f"[DONE] Inserted rows: {total_inserted}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

