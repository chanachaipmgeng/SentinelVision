#!/bin/sh
# DPU Attendance restore into the LIVE stack (destructive — replaces current data).
#
#   scripts/restore.sh <STAMP|path/to/dpu-STAMP.dump> --yes [--stop-api] [--db-only|--images-only]
#
#   --yes         required; the script refuses to run without it
#   --stop-api    docker mode: stop dpu-api / dpu-api-gpu1 before pg_restore and start them afterwards
#                 (otherwise the script aborts while the API holds connections to the database)
#   --db-only / --images-only  restore one half only
#
# Credentials come from env / <repo>/.env (POSTGRES_USER/PASSWORD/DB, DB_SCHEMA). BACKUP_DIR locates
# the files when a bare STAMP is given. Rehearse with scripts/restore-drill.sh first — it restores
# the same files into a scratch database and never touches production.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/lib/backup-common.sh"

usage() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

TARGET=""; YES=0; STOP_API=0; DO_DB=1; DO_IMAGES=1
for arg in "$@"; do
  case "$arg" in
    --yes) YES=1 ;;
    --stop-api) STOP_API=1 ;;
    --db-only) DO_IMAGES=0 ;;
    --images-only) DO_DB=0 ;;
    -h|--help) usage ;;
    -*) bk_die "unknown option $arg" ;;
    *) TARGET=$arg ;;
  esac
done
[ -n "$TARGET" ] || usage
[ "$YES" = 1 ] || bk_die "refusing to overwrite the live database without --yes (try scripts/restore-drill.sh $TARGET first)"

bk_load_env
bk_defaults

# Resolve STAMP + files.
case "$TARGET" in
  *.dump) DUMP=$TARGET; BACKUP_DIR=$(cd "$(dirname "$DUMP")" && pwd); STAMP=$(basename "$DUMP" .dump); STAMP=${STAMP#dpu-} ;;
  *) STAMP=$TARGET; DUMP="$BACKUP_DIR/dpu-$STAMP.dump" ;;
esac
IMAGES="$BACKUP_DIR/dpu-$STAMP-images.tar.gz"
MANIFEST="$BACKUP_DIR/dpu-$STAMP.manifest.json"
SUMS="$BACKUP_DIR/dpu-$STAMP.sha256"
[ -r "$DUMP" ] || bk_die "dump not found: $DUMP"
[ "$DO_IMAGES" = 0 ] || [ -r "$IMAGES" ] || bk_die "image archive not found: $IMAGES"

if [ -r "$SUMS" ]; then
  (cd "$BACKUP_DIR" && sha256sum -c --quiet "$(basename "$SUMS")") || bk_die "checksum mismatch — backup set $STAMP is corrupt"
  bk_log "checksums ok"
else
  bk_log "WARNING: no $SUMS, skipping checksum verification"
fi

bk_log "mode=$BACKUP_MODE target db=$POSTGRES_DB schema=$DB_SCHEMA stamp=$STAMP db=$DO_DB images=$DO_IMAGES"

API_CONTAINERS=""
if [ "$DO_DB" = 1 ] && [ "$BACKUP_MODE" = "docker" ]; then
  API_CONTAINERS=$(docker ps --format '{{.Names}}' | grep -E '^dpu-api(-gpu[0-9]+)?$' || true)
  if [ -n "$API_CONTAINERS" ]; then
    if [ "$STOP_API" = 1 ]; then
      # shellcheck disable=SC2086
      docker stop $API_CONTAINERS >/dev/null && bk_log "stopped: $(printf '%s ' $API_CONTAINERS)"
    else
      bk_die "API containers are running ($(printf '%s ' $API_CONTAINERS)); stop them or pass --stop-api"
    fi
  fi
fi

restart_api() {
  if [ -n "$API_CONTAINERS" ]; then
    # shellcheck disable=SC2086
    docker start $API_CONTAINERS >/dev/null && bk_log "started: $(printf '%s ' $API_CONTAINERS)"
  fi
}
trap restart_api EXIT

if [ "$DO_DB" = 1 ]; then
  # Terminate leftover sessions so --clean can drop objects.
  bk_psql postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='$POSTGRES_DB' AND pid <> pg_backend_pid()" >/dev/null
  SCHEMA_ARG=""
  [ "$DB_SCHEMA" != "public" ] && SCHEMA_ARG="--schema=$DB_SCHEMA"
  if [ "$BACKUP_MODE" = "docker" ]; then
    # shellcheck disable=SC2086
    docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" "$BACKUP_DB_CONTAINER" \
      pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error $SCHEMA_ARG \
      -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$DUMP"
  else
    # shellcheck disable=SC2086
    PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --clean --if-exists --no-owner --no-privileges --exit-on-error $SCHEMA_ARG \
      -h "$PGHOST" -p "$PGPORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$DUMP"
  fi
  bk_log "database restored from $DUMP"
  if [ -r "$MANIFEST" ]; then
    EXPECTED=$(sed -n 's/^ *"\([a-z_]*\)": \([0-9]*\),\{0,1\}$/\1 \2/p' "$MANIFEST")
    MISMATCH=0
    for t in $(printf '%s\n' "$EXPECTED" | cut -d' ' -f1); do
      want=$(printf '%s\n' "$EXPECTED" | awk -v t="$t" '$1==t{print $2}')
      got=$(bk_psql "$POSTGRES_DB" -c "SELECT count(*) FROM \"$DB_SCHEMA\".\"$t\"")
      [ "$want" = "$got" ] || { bk_log "row count mismatch $t: manifest=$want restored=$got"; MISMATCH=1; }
    done
    [ "$MISMATCH" = 0 ] && bk_log "row counts match manifest" || bk_die "row counts differ from manifest"
  fi
fi

if [ "$DO_IMAGES" = 1 ]; then
  ABS_IMAGES=$(cd "$(dirname "$IMAGES")" && pwd)/$(basename "$IMAGES")
  if [ "$BACKUP_MODE" = "docker" ]; then
    docker run --rm --volumes-from "$BACKUP_API_CONTAINER" -v "$(dirname "$ABS_IMAGES")":/backup:ro "$BACKUP_HELPER_IMAGE" \
      sh -c "cd /app && tar xzf /backup/$(basename "$ABS_IMAGES") && chown -R ${APP_UID:-10001}:${APP_GID:-10001} uploaded_images enrolled_images"
  else
    (cd "$BACKUP_IMAGES_ROOT" && tar xzf "$ABS_IMAGES")
  fi
  bk_log "images restored from $IMAGES"
fi

bk_log "restore $STAMP complete — check /ready, then run an enrol + check-in smoke test (docs/RUNBOOK.md)"
