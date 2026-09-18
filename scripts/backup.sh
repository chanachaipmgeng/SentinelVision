#!/bin/sh
# Daily backup. RPO: 24h if cron is daily. RTO: restore time of pg_restore + volume copy.
set -eu
OUT="${1:-./backups}"
mkdir -p "$OUT"
STAMP=$(date +%Y%m%d-%H%M%S)
docker exec dpu-db pg_dump -U "${POSTGRES_USER:-dpu}" "${POSTGRES_DB:-dpu}" > "$OUT/dpu-$STAMP.sql"
echo "wrote $OUT/dpu-$STAMP.sql"
if docker ps --format '{{.Names}}' | grep -q '^face-core-db$'; then
  docker exec face-core-db pg_dump -U "${FACE_POSTGRES_USER:-facecore}" "${FACE_POSTGRES_DB:-facecore}" > "$OUT/face-core-$STAMP.sql"
  echo "wrote $OUT/face-core-$STAMP.sql"
fi
if [ -n "${SERVICE_NOTIFY_TOKEN:-}" ]; then
  curl -sf -X POST http://127.0.0.1/notifications/system \
    -H "X-Service-Token: $SERVICE_NOTIFY_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"event":"backup.ok","body":"backup finished"}' || \
  curl -sf -X POST http://127.0.0.1/notifications/system \
    -H "X-Service-Token: $SERVICE_NOTIFY_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"event":"backup.fail","body":"backup notify failed"}' || true
fi
echo "restore: docker exec -i dpu-db psql -U dpu dpu < $OUT/dpu-$STAMP.sql"
