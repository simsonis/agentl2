#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

COMPOSE_COMMAND="${COMPOSE_CMD:-docker compose}"

echo "[init_db] Ensuring postgres container is up..."
${COMPOSE_COMMAND} up -d postgres

echo "[init_db] Applying db/001_init_raw_tables.sql..."
${COMPOSE_COMMAND} exec postgres bash -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "/docker-entrypoint-initdb.d/001_init_raw_tables.sql"'

echo "[init_db] Done."
