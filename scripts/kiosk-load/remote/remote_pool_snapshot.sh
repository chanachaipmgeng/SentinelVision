#!/bin/bash
# Snapshot Postgres connection usage (for spike / soak pool monitoring).
set -euo pipefail
PW="${DPU_SUDO_PW:-}"
printf '%s\n' "$PW" | sudo -S -p '' -v
sudo_docker() { sudo -n docker "$@"; }

DB_CTR=dpu-db
URL=$(sudo_docker exec dpu-api printenv DATABASE_URL 2>/dev/null || true)
DB_USER=dpu; DB_NAME=dpu; DB_PASS=dpu_secret
if [ -n "$URL" ]; then
  DB_USER=$(echo "$URL" | sed -n 's|.*://\([^:]*\):.*|\1|p')
  DB_PASS=$(echo "$URL" | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
  DB_NAME=$(echo "$URL" | sed -n 's|.*/\([^/?]*\).*|\1|p')
fi
export PGPASSWORD="$DB_PASS"

sudo_docker exec -e PGPASSWORD="$PGPASSWORD" dpu-db psql -U "$DB_USER" -d "$DB_NAME" -tAc "
SELECT json_build_object(
  'active', (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'active'),
  'idle', (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'idle'),
  'idle_in_tx', (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND state = 'idle in transaction'),
  'total', (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()),
  'waiting', (SELECT count(*) FROM pg_stat_activity WHERE datname = current_database() AND wait_event_type IS NOT NULL AND state = 'active'),
  'max_conn', (SELECT setting::int FROM pg_settings WHERE name = 'max_connections'),
  'by_app', (
    SELECT coalesce(json_object_agg(coalesce(application_name, 'unknown'), c), '{}'::json)
    FROM (
      SELECT application_name, count(*) AS c
      FROM pg_stat_activity
      WHERE datname = current_database()
      GROUP BY application_name
    ) s
  )
);
"
