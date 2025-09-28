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

DEFAULT_COLLECTION_ID="precedents-$(date -u +%Y%m%d%H%M%S)"
DEFAULT_ARGS=(
  --page "${COLLECT_PREC_START_PAGE:-1}"
  --pages "${COLLECT_PREC_TOTAL_PAGES:-1}"
  --page-size "${COLLECT_PREC_PAGE_SIZE:-100}"
  --collection-id "${COLLECT_PREC_COLLECTION_ID:-${DEFAULT_COLLECTION_ID}}"
)

if [[ -n "${COLLECT_PREC_KEYWORDS:-}" ]]; then
  DEFAULT_ARGS=(--keywords "${COLLECT_PREC_KEYWORDS}" "${DEFAULT_ARGS[@]}")
fi
if [[ -n "${COLLECT_PREC_DATE_RANGE:-}" ]]; then
  DEFAULT_ARGS=(--date-range "${COLLECT_PREC_DATE_RANGE}" "${DEFAULT_ARGS[@]}")
fi

if [[ $# -eq 0 ]]; then
  set -- "${DEFAULT_ARGS[@]}"
fi

echo "[collect_prec] Executing agentl2-collect-prec $*"
${COMPOSE_COMMAND} exec collector poetry run agentl2-collect-prec "$@"
