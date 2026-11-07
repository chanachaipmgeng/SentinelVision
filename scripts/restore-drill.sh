#!/bin/sh
# DPU Attendance restore drill: prove a backup set is restorable WITHOUT touching production.
#
#   scripts/restore-drill.sh [STAMP|path/to/dpu-STAMP.dump]     (default: newest set in BACKUP_DIR)
#
# Steps (exit code 0 only when every check passes):
#   1. sha256 verification of the backup set
#   2. restore the dump into a scratch target
#        DRILL_TARGET=container (docker mode default)  throw-away pgvector container, random password
#        DRILL_TARGET=database  (direct mode default)   scratch database dpu_drill_<pid> on the same server
#   3. compare row counts of every table with the manifest
#   4. face match query on the restored data: top-1 nearest neighbour of a stored embedding must be
#      itself with cosine similarity >= 0.999 (checks pgvector + HNSW index survived the restore)
#   5. list the image archive and compare file counts with the manifest
#   6. drop the scratch target (also on failure; set DRILL_KEEP=1 to inspect it)
#
# Env: DRILL_PG_IMAGE (pgvector/pgvector:pg16 — match the production major), DRILL_KEEP, DRILL_TARGET,
# plus everything scripts/backup.sh reads (POSTGRES_*, DB_SCHEMA, BACKUP_DIR, BACKUP_MODE, PGHOST, PGPORT).
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/lib/backup-common.sh"

bk_load_env
bk_defaults

TARGET=${1:-}
if [ -z "$TARGET" ]; then
  TARGET=$(ls -1 "$BACKUP_DIR"/dpu-*.dump 2>/dev/null | sort | tail -n1 || true)
  [ -n "$TARGET" ] || bk_die "no dpu-*.dump in $BACKUP_DIR"
fi
case "$TARGET" in
  *.dump) DUMP=$TARGET; BACKUP_DIR=$(cd "$(dirname "$DUMP")" && pwd); STAMP=$(basename "$DUMP" .dump); STAMP=${STAMP#dpu-} ;;
  *) STAMP=$TARGET; DUMP="$BACKUP_DIR/dpu-$STAMP.dump" ;;
esac
IMAGES="$BACKUP_DIR/dpu-$STAMP-images.tar.gz"
MANIFEST="$BACKUP_DIR/dpu-$STAMP.manifest.json"
SUMS="$BACKUP_DIR/dpu-$STAMP.sha256"
for f in "$DUMP" "$IMAGES" "$MANIFEST"; do [ -r "$f" ] || bk_die "missing $f"; done

DRILL_PG_IMAGE=${DRILL_PG_IMAGE:-pgvector/pgvector:pg16}
if [ -z "${DRILL_TARGET:-}" ]; then
  [ "$BACKUP_MODE" = "docker" ] && DRILL_TARGET=container || DRILL_TARGET=database
fi
FAILED=0
fail() { bk_log "FAIL: $*"; FAILED=1; }
pass() { bk_log "ok:   $*"; }

bk_log "drill stamp=$STAMP mode=$BACKUP_MODE target=$DRILL_TARGET"

# 1. checksums
if [ -r "$SUMS" ]; then
  if (cd "$BACKUP_DIR" && sha256sum -c --quiet "$(basename "$SUMS")"); then pass "checksums"; else fail "checksum mismatch"; fi
else
  fail "no checksum file $SUMS"
fi

# 2. scratch target
SCRATCH_CONTAINER="dpu-restore-drill-$$"
SCRATCH_DB="dpu_drill_$(date -u +%Y%m%d%H%M%S)_$$"
cleanup() {
  if [ "${DRILL_KEEP:-0}" = 1 ]; then bk_log "DRILL_KEEP=1 — leaving scratch target ($SCRATCH_CONTAINER / $SCRATCH_DB)"; return; fi
  if [ "$DRILL_TARGET" = container ]; then
    docker rm -f -v "$SCRATCH_CONTAINER" >/dev/null 2>&1 || true
  else
    bk_psql postgres -c "DROP DATABASE IF EXISTS \"$SCRATCH_DB\" WITH (FORCE)" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

# scratch_psql <db> [args] / scratch_restore <dump>
if [ "$DRILL_TARGET" = container ]; then
  SCRATCH_PW=$(head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n')
  docker run -d --name "$SCRATCH_CONTAINER" -e POSTGRES_USER="$POSTGRES_USER" -e POSTGRES_PASSWORD="$SCRATCH_PW" \
    -e POSTGRES_DB="$POSTGRES_DB" "$DRILL_PG_IMAGE" >/dev/null
  i=0
  until docker exec "$SCRATCH_CONTAINER" pg_isready -q -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1 && [ "$i" -gt 2 ]; do
    i=$((i+1)); [ "$i" -gt 60 ] && bk_die "scratch postgres did not start"; sleep 1
  done
  TARGET_DB=$POSTGRES_DB
  scratch_psql() { _db=$1; shift; docker exec -i -e PGPASSWORD="$SCRATCH_PW" "$SCRATCH_CONTAINER" psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$_db" -Atq "$@"; }
  scratch_restore() { docker exec -i -e PGPASSWORD="$SCRATCH_PW" "$SCRATCH_CONTAINER" pg_restore --no-owner --no-privileges --exit-on-error -U "$POSTGRES_USER" -d "$TARGET_DB" < "$1"; }
  pass "scratch container $SCRATCH_CONTAINER ($DRILL_PG_IMAGE)"
else
  bk_psql postgres -c "CREATE DATABASE \"$SCRATCH_DB\"" >/dev/null
  TARGET_DB=$SCRATCH_DB
  scratch_psql() { bk_psql "$@"; }
  scratch_restore() {
    if [ "$BACKUP_MODE" = docker ]; then
      docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" "$BACKUP_DB_CONTAINER" pg_restore --no-owner --no-privileges --exit-on-error -U "$POSTGRES_USER" -d "$TARGET_DB" < "$1"
    else
      PGPASSWORD="$POSTGRES_PASSWORD" pg_restore --no-owner --no-privileges --exit-on-error -h "$PGHOST" -p "$PGPORT" -U "$POSTGRES_USER" -d "$TARGET_DB" < "$1"
    fi
  }
  pass "scratch database $SCRATCH_DB"
fi

# A schema-scoped dump (DB_SCHEMA != public) does not carry CREATE EXTENSION; a full dump does.
if [ "$DB_SCHEMA" != "public" ]; then
  scratch_psql "$TARGET_DB" -c "CREATE EXTENSION IF NOT EXISTS vector" >/dev/null
fi
if scratch_restore "$DUMP"; then pass "pg_restore"; else fail "pg_restore returned errors"; fi

# 3. row counts
EXPECTED=$(sed -n 's/^ *"\([a-z_]*\)": \([0-9]*\),\{0,1\}$/\1 \2/p' "$MANIFEST")
TABLES=$(printf '%s\n' "$EXPECTED" | wc -l | tr -d ' ')
MISMATCH=0
for t in $(printf '%s\n' "$EXPECTED" | cut -d' ' -f1); do
  want=$(printf '%s\n' "$EXPECTED" | awk -v t="$t" '$1==t{print $2}')
  got=$(scratch_psql "$TARGET_DB" -c "SELECT count(*) FROM \"$DB_SCHEMA\".\"$t\"" 2>/dev/null || echo missing)
  [ "$want" = "$got" ] || { bk_log "  $t: manifest=$want restored=$got"; MISMATCH=1; }
done
[ "$MISMATCH" = 0 ] && pass "row counts match manifest ($TABLES tables)" || fail "row counts differ from manifest"

# 4. face match query
FE="\"$DB_SCHEMA\".face_encoding"
N_FACES=$(scratch_psql "$TARGET_DB" -c "SELECT count(*) FROM $FE" 2>/dev/null || echo 0)
if [ "$N_FACES" -gt 0 ] 2>/dev/null; then
  PROBE=$(scratch_psql "$TARGET_DB" -c "SELECT \"faceEncodingId\" FROM $FE ORDER BY \"createdAt\" DESC LIMIT 1")
  MATCH=$(scratch_psql "$TARGET_DB" -c "SELECT \"faceEncodingId\" || '|' || round((1 - (embedding <=> (SELECT embedding FROM $FE WHERE \"faceEncodingId\"='$PROBE')))::numeric, 4) FROM $FE ORDER BY embedding <=> (SELECT embedding FROM $FE WHERE \"faceEncodingId\"='$PROBE') LIMIT 1")
  MATCH_ID=${MATCH%%|*}; MATCH_SIM=${MATCH##*|}
  HNSW=$(scratch_psql "$TARGET_DB" -c "SELECT count(*) FROM pg_indexes WHERE schemaname='$DB_SCHEMA' AND tablename='face_encoding' AND indexdef ILIKE '%hnsw%'")
  if [ "$MATCH_ID" = "$PROBE" ] && awk -v s="$MATCH_SIM" 'BEGIN{exit !(s>=0.999)}'; then
    pass "face match: probe $PROBE is its own top-1 (similarity $MATCH_SIM, $N_FACES embeddings, hnsw indexes=$HNSW)"
  else
    fail "face match: expected $PROBE got $MATCH_ID (similarity $MATCH_SIM)"
  fi
  [ "$HNSW" -ge 1 ] 2>/dev/null || fail "HNSW index on face_encoding.embedding missing after restore"
else
  bk_log "warn: face_encoding is empty — face match query skipped"
fi

# 5. image archive
WANT_FILES=$(( $(sed -n 's/.*"uploadedFiles": \([0-9]*\).*/\1/p' "$MANIFEST") + $(sed -n 's/.*"enrolledFiles": \([0-9]*\).*/\1/p' "$MANIFEST") ))
if GOT_FILES=$(tar tzf "$IMAGES" | grep -vc '/$'); then :; else GOT_FILES=0; fi
[ "$WANT_FILES" = "$GOT_FILES" ] && pass "image archive lists $GOT_FILES files (manifest $WANT_FILES)" || fail "image archive files=$GOT_FILES manifest=$WANT_FILES"

if [ "$FAILED" = 0 ]; then
  bk_log "DRILL PASSED for $STAMP"
  bk_notify backup.drill.ok "restore drill $STAMP passed ($TABLES tables, $N_FACES embeddings, $GOT_FILES images)"
else
  bk_log "DRILL FAILED for $STAMP"
  bk_notify backup.drill.fail "restore drill $STAMP FAILED on $(hostname)"
  exit 1
fi
