#!/bin/sh
# Daily backup. RPO: 24h if cron is daily. RTO: restore time of pg_restore + volume copy.
set -eu
OUT="${1:-./backups}"
mkdir -p "$OUT"
STAMP=$(date +%Y%m%d-%H%M%S)
docker exec dpu-db pg_dump -U "${POSTGRES_USER:-dpu}" "${POSTGRES_DB:-dpu}" > "$OUT/dpu-$STAMP.sql"
echo "wrote $OUT/dpu-$STAMP.sql"
echo "restore: docker exec -i dpu-db psql -U dpu dpu < $OUT/dpu-$STAMP.sql"
