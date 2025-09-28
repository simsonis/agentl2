#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

ENV_FILE="${PROJECT_ROOT}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${ENV_FILE}"
  set +a
fi

COMPOSE_COMMAND="${COMPOSE_CMD:-docker compose}"

DEFAULT_COLLECTION_ID="laws-$(date -u +%Y%m%d%H%M%S)"
DEFAULT_ARGS=(
  --page "${COLLECT_LAWS_START_PAGE:-1}"
  --pages "${COLLECT_LAWS_TOTAL_PAGES:-1}"
  --page-size "${COLLECT_LAWS_PAGE_SIZE:-100}"
  --collection-id "${COLLECT_LAWS_COLLECTION_ID:-${DEFAULT_COLLECTION_ID}}"
)

if [[ -n "${COLLECT_LAWS_QUERY:-}" ]]; then
  DEFAULT_ARGS=(--query "${COLLECT_LAWS_QUERY}" "${DEFAULT_ARGS[@]}")
fi

if [[ $# -eq 0 ]]; then
  set -- "${DEFAULT_ARGS[@]}"
fi

echo "[collect_laws] Executing agentl2-collect-laws $*"
${COMPOSE_COMMAND} exec collector poetry run agentl2-collect-laws "$@"
