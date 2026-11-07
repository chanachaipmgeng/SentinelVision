#!/bin/sh
# Timer loop for the backup sidecar.
#   BACKUP_INTERVAL_SECONDS  seconds between runs (default 86400 = daily); 0 = run once and exit
#   BACKUP_RUN_AT_START      1 (default) runs a backup immediately, 0 waits one interval first
#   BACKUP_DRILL_EVERY       run restore-drill.sh after every N backups (0 = never, default 7)
# Any argument runs that command instead of the loop, e.g. `docker compose run --rm backup restore-drill.sh`.
set -eu
cd /opt/dpu

if [ $# -gt 0 ]; then
  case "$1" in
    backup.sh|restore.sh|restore-drill.sh) exec "/opt/dpu/scripts/$@" ;;
    *) exec "$@" ;;
  esac
fi

i=0
until pg_isready -q -h "${PGHOST:-db}" -p "${PGPORT:-5432}" -U "${POSTGRES_USER:-dpu}"; do
  i=$((i+1)); [ "$i" -le 120 ] || { echo "[backup] ${PGHOST:-db}:${PGPORT:-5432} not reachable after 10 min" >&2; exit 1; }
  sleep 5
done

INTERVAL=${BACKUP_INTERVAL_SECONDS:-86400}
RUN_AT_START=${BACKUP_RUN_AT_START:-1}
DRILL_EVERY=${BACKUP_DRILL_EVERY:-7}
n=0
[ "$RUN_AT_START" = 1 ] || sleep "$INTERVAL"
while :; do
  if /opt/dpu/scripts/backup.sh; then
    date +%s > /tmp/backup-ok
    n=$((n+1))
    if [ "$DRILL_EVERY" -gt 0 ] 2>/dev/null && [ $((n % DRILL_EVERY)) -eq 0 ]; then
      DRILL_TARGET=database /opt/dpu/scripts/restore-drill.sh || echo "[backup] restore drill FAILED" >&2
    fi
  else
    echo "[backup] backup FAILED" >&2
  fi
  [ "$INTERVAL" -gt 0 ] 2>/dev/null || break
  sleep "$INTERVAL"
done
