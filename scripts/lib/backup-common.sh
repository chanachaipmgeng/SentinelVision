#!/bin/sh
# Shared helpers for scripts/backup.sh, restore.sh and restore-drill.sh (POSIX sh).
#
# Credentials come from the environment or the repo .env only (never hard-coded):
#   POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB   (same values the stack uses)
#   DB_SCHEMA            schema holding the DPU tables (default public; "dpu" on the shared dev-postgres)
#   ENV_FILE             alternative .env path (default <repo>/.env)
#
# Two execution modes (BACKUP_MODE=auto|docker|direct):
#   docker  (host with the docker CLI)   pg_dump/psql run inside BACKUP_DB_CONTAINER (dpu-db) and the
#                                        image volumes are read through --volumes-from BACKUP_API_CONTAINER (dpu-api)
#   direct  (backup sidecar / any host)  pg_dump/psql talk to PGHOST:PGPORT over TCP and the image
#                                        directories are read from BACKUP_IMAGES_ROOT (default /data)

bk_log() { printf '[%s] %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >&2; }
bk_die() { bk_log "ERROR: $*"; exit 1; }

bk_repo_root() {
  CDPATH= cd -- "$(dirname -- "$0")/.." && pwd
}

# Export KEY=VALUE pairs from .env that are not already set in the environment
# (shell env wins so `POSTGRES_PASSWORD=... scripts/backup.sh` works for one-offs).
bk_load_env() {
  _env_file="${ENV_FILE:-$(bk_repo_root)/.env}"
  [ -r "$_env_file" ] || return 0
  while IFS= read -r _line || [ -n "$_line" ]; do
    _line=$(printf '%s' "$_line" | sed 's/\r$//')
    case "$_line" in ''|'#'*) continue ;; esac
    case "$_line" in *=*) ;; *) continue ;; esac
    _key=${_line%%=*}
    _val=${_line#*=}
    case "$_key" in *[!A-Za-z0-9_]*) continue ;; esac
    # strip one layer of matching quotes
    case "$_val" in
      \"*\") _val=${_val#\"}; _val=${_val%\"} ;;
      \'*\') _val=${_val#\'}; _val=${_val%\'} ;;
    esac
    eval "_cur=\${$_key-__unset__}"
    if [ "$_cur" = "__unset__" ]; then
      export "$_key=$_val"
    fi
  done < "$_env_file"
}

bk_defaults() {
  POSTGRES_USER=${POSTGRES_USER:-dpu}
  POSTGRES_DB=${POSTGRES_DB:-dpu}
  DB_SCHEMA=${DB_SCHEMA:-public}
  BACKUP_DIR=${BACKUP_DIR:-$(bk_repo_root)/backups}
  BACKUP_KEEP_DAYS=${BACKUP_KEEP_DAYS:-14}
  BACKUP_DB_CONTAINER=${BACKUP_DB_CONTAINER:-dpu-db}
  BACKUP_API_CONTAINER=${BACKUP_API_CONTAINER:-dpu-api}
  BACKUP_IMAGES_ROOT=${BACKUP_IMAGES_ROOT:-/data}
  BACKUP_HELPER_IMAGE=${BACKUP_HELPER_IMAGE:-alpine:3.21}
  PGHOST=${PGHOST:-db}
  PGPORT=${PGPORT:-5432}
  export POSTGRES_USER POSTGRES_DB DB_SCHEMA BACKUP_DIR BACKUP_KEEP_DAYS
  export BACKUP_DB_CONTAINER BACKUP_API_CONTAINER BACKUP_IMAGES_ROOT BACKUP_HELPER_IMAGE PGHOST PGPORT

  if [ -z "${BACKUP_MODE:-}" ] || [ "$BACKUP_MODE" = "auto" ]; then
    if command -v docker >/dev/null 2>&1 && [ ! -f /.dockerenv ]; then
      BACKUP_MODE=docker
    else
      BACKUP_MODE=direct
    fi
  fi
  export BACKUP_MODE
  [ -n "${POSTGRES_PASSWORD:-}" ] || bk_die "POSTGRES_PASSWORD is not set (export it or put it in .env)"
}

# --- database access -------------------------------------------------------------------------

# bk_psql <db> [psql args...]  — non-interactive, tuples-only
bk_psql() {
  _db=$1; shift
  if [ "$BACKUP_MODE" = "docker" ]; then
    # -i is needed only when a caller pipes SQL in; otherwise detach stdin so loops reading
    # from a pipe are not drained by docker exec
    if [ -t 0 ] || [ "${BK_PSQL_STDIN:-0}" = 1 ]; then _i=-i; else _i=; fi
    docker exec $_i -e PGPASSWORD="$POSTGRES_PASSWORD" "$BACKUP_DB_CONTAINER" \
      psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$_db" -Atq "$@"
  else
    PGPASSWORD="$POSTGRES_PASSWORD" psql -v ON_ERROR_STOP=1 -h "$PGHOST" -p "$PGPORT" \
      -U "$POSTGRES_USER" -d "$_db" -Atq "$@"
  fi
}

# bk_pg_dump <outfile>  — custom format, schema-scoped when DB_SCHEMA != public
bk_pg_dump() {
  _out=$1
  _schema_arg=""
  [ "$DB_SCHEMA" != "public" ] && _schema_arg="--schema=$DB_SCHEMA"
  if [ "$BACKUP_MODE" = "docker" ]; then
    # shellcheck disable=SC2086
    docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" "$BACKUP_DB_CONTAINER" \
      pg_dump -Fc --no-owner --no-privileges $_schema_arg -U "$POSTGRES_USER" "$POSTGRES_DB" > "$_out"
  else
    # shellcheck disable=SC2086
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -Fc --no-owner --no-privileges $_schema_arg \
      -h "$PGHOST" -p "$PGPORT" -U "$POSTGRES_USER" "$POSTGRES_DB" > "$_out"
  fi
}

# bk_table_counts <db> <schema>  → lines "table<TAB>count"
bk_table_counts() {
  _db=$1; _schema=$2
  # one round trip: count(*) per table via a dynamic query (exact, unlike pg_class.reltuples)
  bk_psql "$_db" -c "
    SELECT string_agg(format('SELECT %L AS t, count(*) AS n FROM %I.%I', table_name, table_schema, table_name), ' UNION ALL ' ORDER BY table_name)
    FROM information_schema.tables WHERE table_schema='$_schema' AND table_type='BASE TABLE'" </dev/null \
    | { IFS= read -r _sql; [ -n "$_sql" ] && bk_psql "$_db" -F "$(printf '\t')" -c "$_sql ORDER BY 1" </dev/null; }
}

# --- image volumes ---------------------------------------------------------------------------

# bk_images_tar <outfile>  — uploaded_images + enrolled_images (temp_images is scratch)
bk_images_tar() {
  _out=$1
  _abs_out=$(cd "$(dirname "$_out")" && pwd)/$(basename "$_out")
  if [ "$BACKUP_MODE" = "docker" ]; then
    # run as the invoking user so the archive in BACKUP_DIR is not root-owned
    docker run --rm --user "$(id -u):$(id -g)" --volumes-from "$BACKUP_API_CONTAINER":ro \
      -v "$(dirname "$_abs_out")":/backup "$BACKUP_HELPER_IMAGE" \
      sh -c "cd /app && tar czf /backup/$(basename "$_abs_out") uploaded_images enrolled_images"
  else
    (cd "$BACKUP_IMAGES_ROOT" && tar czf "$_abs_out" uploaded_images enrolled_images)
  fi
}

# bk_images_count → "uploaded<TAB>enrolled"
bk_images_count() {
  if [ "$BACKUP_MODE" = "docker" ]; then
    docker exec "$BACKUP_API_CONTAINER" sh -c \
      'printf "%s\t%s\n" "$(find uploaded_images -type f | wc -l)" "$(find enrolled_images -type f | wc -l)"'
  else
    (cd "$BACKUP_IMAGES_ROOT" && printf '%s\t%s\n' "$(find uploaded_images -type f | wc -l)" "$(find enrolled_images -type f | wc -l)")
  fi
}

bk_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

bk_file_size() {
  wc -c < "$1" | tr -d ' '
}

# --- notifications (optional) ----------------------------------------------------------------

# bk_notify <event> <body>  — POST /notifications/system when SERVICE_NOTIFY_TOKEN is set
bk_notify() {
  [ -n "${SERVICE_NOTIFY_TOKEN:-}" ] || return 0
  _url=${NOTIFY_URL:-http://127.0.0.1:${HTTP_PORT:-80}/notifications/system}
  _body=$(printf '%s' "$2" | sed 's/\\/\\\\/g; s/"/\\"/g')
  curl -sf -X POST "$_url" -H "X-Service-Token: $SERVICE_NOTIFY_TOKEN" \
    -H "Content-Type: application/json" -d "{\"event\":\"$1\",\"body\":\"$_body\"}" >/dev/null 2>&1 || \
    bk_log "notify $1 failed (ignored)"
}
