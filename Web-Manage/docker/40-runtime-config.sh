#!/bin/sh
# Runs from /docker-entrypoint.d/ on every container start (nginx official image).
# Writes the SPA runtime config from environment variables. The Maps browser key is
# always written empty so a key in the environment cannot reach the public bundle.
#
# The container runs as the unprivileged nginx user, so the file lives under /tmp
# (tmpfs when the root fs is read-only) and nginx aliases it at /assets/config.json.
set -eu

RUNTIME_DIR="${RUNTIME_DIR:-/tmp/dpu-runtime}"
TARGET="$RUNTIME_DIR/config.json"

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

MAP_ID="$(json_escape "${GOOGLE_MAPS_MAP_ID:-DEMO_MAP_ID}")"

mkdir -p "$RUNTIME_DIR"
cat > "$TARGET" <<EOF
{
  "googleMapsApiKey": "",
  "googleMapsMapId": "${MAP_ID}"
}
EOF

echo "[runtime-config] wrote $TARGET (Google Maps key omitted, OSM fallback)." >&2
