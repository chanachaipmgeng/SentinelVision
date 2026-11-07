#!/bin/sh
# DPU Attendance backup: PostgreSQL (pg_dump custom format) + face image volumes + manifest.
#
#   scripts/backup.sh [BACKUP_DIR]
#
# Reads credentials from the environment or <repo>/.env (POSTGRES_USER/PASSWORD/DB, DB_SCHEMA).
# Env knobs (all optional): BACKUP_DIR (./backups), BACKUP_KEEP_DAYS (14), BACKUP_MODE
# (auto|docker|direct), BACKUP_DB_CONTAINER (dpu-db), BACKUP_API_CONTAINER (dpu-api),
# BACKUP_IMAGES_ROOT (/data, direct mode), BACKUP_RCLONE_REMOTE (remote:bucket/path),
# BACKUP_S3_URI (s3://bucket/prefix, aws CLI), SERVICE_NOTIFY_TOKEN (+ NOTIFY_URL).
#
# Output per run (STAMP = UTC yyyymmdd-HHMMSS):
#   dpu-STAMP.dump            pg_dump -Fc (restore with pg_restore; schema-scoped when DB_SCHEMA != public)
#   dpu-STAMP-images.tar.gz   uploaded_images + enrolled_images
#   dpu-STAMP.manifest.json   row counts per table, file counts, sha256 + sizes (used by restore-drill.sh)
#   dpu-STAMP.sha256          checksums for `sha256sum -c`
# RPO = run interval (24 h with the daily sidecar/cron). See docs/RUNBOOK.md for RTO + drill.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/lib/backup-common.sh"

bk_load_env
[ $# -ge 1 ] && BACKUP_DIR=$1
bk_defaults

mkdir -p "$BACKUP_DIR"
STAMP=$(date -u +%Y%m%d-%H%M%S)
PREFIX="$BACKUP_DIR/dpu-$STAMP"
DUMP="$PREFIX.dump"
IMAGES="$PREFIX-images.tar.gz"
MANIFEST="$PREFIX.manifest.json"
SUMS="$PREFIX.sha256"

cleanup_partial() {
  bk_log "backup failed — removing partial files for $STAMP"
  rm -f "$DUMP" "$IMAGES" "$MANIFEST" "$SUMS"
  bk_notify backup.fail "backup $STAMP failed on $(hostname)"
}
trap 'rc=$?; trap - EXIT; [ "$rc" -eq 0 ] || cleanup_partial; exit $rc' EXIT INT TERM

bk_log "mode=$BACKUP_MODE db=$POSTGRES_DB schema=$DB_SCHEMA out=$BACKUP_DIR"

# 1. Row counts first so the manifest matches the dump as closely as possible.
PG_VERSION=$(bk_psql "$POSTGRES_DB" -c "SHOW server_version")
COUNTS=$(bk_table_counts "$POSTGRES_DB" "$DB_SCHEMA")
TABLE_TOTAL=$(printf '%s\n' "$COUNTS" | grep -c . || true)
bk_log "tables=$TABLE_TOTAL postgres=$PG_VERSION"

# 2. Database dump (custom format, compressed by pg_dump itself).
bk_pg_dump "$DUMP"
bk_log "wrote $DUMP ($(bk_file_size "$DUMP") bytes)"

# 3. Image volumes.
IMG_COUNTS=$(bk_images_count)
UPLOADED_N=$(printf '%s' "$IMG_COUNTS" | cut -f1)
ENROLLED_N=$(printf '%s' "$IMG_COUNTS" | cut -f2)
bk_images_tar "$IMAGES"
bk_log "wrote $IMAGES ($(bk_file_size "$IMAGES") bytes, uploaded=$UPLOADED_N enrolled=$ENROLLED_N files)"

# 4. Optional sibling Face Core database (docker mode only; same host).
FACE_CORE_DUMP=""
if [ "$BACKUP_MODE" = "docker" ] && docker ps --format '{{.Names}}' | grep -q '^face-core-db$'; then
  FACE_CORE_DUMP="$BACKUP_DIR/face-core-$STAMP.dump"
  docker exec -e PGPASSWORD="${FACE_POSTGRES_PASSWORD:-}" face-core-db \
    pg_dump -Fc --no-owner --no-privileges -U "${FACE_POSTGRES_USER:-facecore}" "${FACE_POSTGRES_DB:-facecore}" > "$FACE_CORE_DUMP"
  bk_log "wrote $FACE_CORE_DUMP"
fi

# 5. Manifest + checksums.
DUMP_SHA=$(bk_sha256 "$DUMP")
IMAGES_SHA=$(bk_sha256 "$IMAGES")
{
  printf '{\n'
  printf '  "stamp": "%s",\n' "$STAMP"
  printf '  "createdAt": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '  "host": "%s",\n' "$(hostname)"
  printf '  "mode": "%s",\n' "$BACKUP_MODE"
  printf '  "database": "%s",\n' "$POSTGRES_DB"
  printf '  "schema": "%s",\n' "$DB_SCHEMA"
  printf '  "postgresVersion": "%s",\n' "$PG_VERSION"
  printf '  "dump": {"file": "%s", "sha256": "%s", "bytes": %s},\n' "$(basename "$DUMP")" "$DUMP_SHA" "$(bk_file_size "$DUMP")"
  printf '  "images": {"file": "%s", "sha256": "%s", "bytes": %s, "uploadedFiles": %s, "enrolledFiles": %s},\n' \
    "$(basename "$IMAGES")" "$IMAGES_SHA" "$(bk_file_size "$IMAGES")" "$UPLOADED_N" "$ENROLLED_N"
  if [ -n "$FACE_CORE_DUMP" ]; then
    printf '  "faceCoreDump": "%s",\n' "$(basename "$FACE_CORE_DUMP")"
  fi
  printf '  "rowCounts": {'
  _first=1
  printf '%s\n' "$COUNTS" | while IFS="$(printf '\t')" read -r _t _n; do
    [ -n "$_t" ] || continue
    if [ "$_first" = 1 ]; then _first=0; else printf ','; fi
    printf '\n    "%s": %s' "$_t" "$_n"
  done
  printf '\n  }\n}\n'
} > "$MANIFEST"
{
  printf '%s  %s\n' "$DUMP_SHA" "$(basename "$DUMP")"
  printf '%s  %s\n' "$IMAGES_SHA" "$(basename "$IMAGES")"
  printf '%s  %s\n' "$(bk_sha256 "$MANIFEST")" "$(basename "$MANIFEST")"
} > "$SUMS"
bk_log "wrote $MANIFEST"

# 6. Rotation (local).
if [ "${BACKUP_KEEP_DAYS}" -gt 0 ] 2>/dev/null; then
  find "$BACKUP_DIR" -maxdepth 1 -type f \( -name 'dpu-*' -o -name 'face-core-*' \) -mtime +"$BACKUP_KEEP_DAYS" -print -delete \
    | sed 's/^/rotated: /' >&2 || true
fi

# 7. Optional offsite copy.
if [ -n "${BACKUP_RCLONE_REMOTE:-}" ]; then
  command -v rclone >/dev/null 2>&1 || bk_die "BACKUP_RCLONE_REMOTE set but rclone is not installed"
  rclone copy --include "dpu-$STAMP*" --include "face-core-$STAMP*" "$BACKUP_DIR" "$BACKUP_RCLONE_REMOTE"
  bk_log "copied to $BACKUP_RCLONE_REMOTE"
elif [ -n "${BACKUP_S3_URI:-}" ]; then
  command -v aws >/dev/null 2>&1 || bk_die "BACKUP_S3_URI set but the aws CLI is not installed"
  for f in "$DUMP" "$IMAGES" "$MANIFEST" "$SUMS" ${FACE_CORE_DUMP:+"$FACE_CORE_DUMP"}; do
    aws s3 cp "$f" "${BACKUP_S3_URI%/}/$(basename "$f")" >/dev/null
  done
  bk_log "copied to $BACKUP_S3_URI"
fi

bk_notify backup.ok "backup $STAMP ok: $TABLE_TOTAL tables, $UPLOADED_N+$ENROLLED_N images"
bk_log "done: $STAMP"
echo "restore: scripts/restore.sh $STAMP --yes   (drill: scripts/restore-drill.sh $STAMP)"
