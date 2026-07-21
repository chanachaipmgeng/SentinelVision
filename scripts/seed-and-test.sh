#!/usr/bin/env bash
# Seed demo data + run API smoke tests (requires docker compose stack up)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
RESET_FLAG=()
if [[ "${1:-}" == "--reset" ]]; then
  RESET_FLAG=(--reset)
fi

echo "==> Seed demo data"
docker compose run --rm \
  -v "$ROOT/API-Fast:/app" \
  --entrypoint python \
  api scripts/seed_demo_data.py "${RESET_FLAG[@]}"

echo "==> Smoke test API via compose network"
docker compose run --rm \
  -v "$ROOT/API-Fast:/app" \
  --entrypoint python \
  api scripts/smoke_test_api.py --base-url http://api:8000

echo
echo "Accounts: sysadmin / admin / boss / emp1 / emp2"
echo "Password: Password123!"
