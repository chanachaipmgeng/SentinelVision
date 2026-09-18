#!/bin/sh
# Migrate local face_encoding rows into Face Core, then leave rollback possible.
# Run on the DPU host BEFORE switching docker-compose.face-core.yml on.
# Does not delete local rows.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
OUT=${1:-$ROOT/backups}
mkdir -p "$OUT"
echo "dry-run"
docker exec -e FACE_CORE_URL="${FACE_CORE_URL:-http://face-core-api:8000}" \
  -e FACE_CORE_API_KEY="${FACE_CORE_API_KEY:?set FACE_CORE_API_KEY}" \
  dpu-api python scripts/migrate_faces_to_face_core.py --dry-run
echo "migrate"
docker exec -e FACE_CORE_URL="${FACE_CORE_URL:-http://face-core-api:8000}" \
  -e FACE_CORE_API_KEY="$FACE_CORE_API_KEY" \
  dpu-api python scripts/migrate_faces_to_face_core.py --mapping-out /tmp/migration_mapping.json
docker cp dpu-api:/tmp/migration_mapping.json "$OUT/migration_mapping.json"
echo "mapping saved to $OUT/migration_mapping.json"
echo "rollback: remove docker-compose.face-core.yml from the DPU compose command; local face_encoding rows are still there"
echo "verify: compare face_encoding count with GET /v1/companies/{companyId} on face-core"
