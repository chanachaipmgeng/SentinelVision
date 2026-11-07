#!/bin/sh
# Runs from /docker-entrypoint.d/ on every container start (nginx official image).
# Writes the SPA runtime config from environment variables so the same image can be
# deployed to any environment without baking the Google Maps key into the bundle.
#
# The container runs as the unprivileged nginx user, so the file lives under /tmp
# (tmpfs when the root fs is read-only) and nginx aliases it at /assets/config.json.
set -eu

RUNTIME_DIR="${RUNTIME_DIR:-/tmp/dpu-runtime}"
TARGET="$RUNTIME_DIR/config.json"

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

MAPS_KEY="$(json_escape "${GOOGLE_MAPS_API_KEY:-}")"
MAP_ID="$(json_escape "${GOOGLE_MAPS_MAP_ID:-DEMO_MAP_ID}")"

mkdir -p "$RUNTIME_DIR"
cat > "$TARGET" <<EOF
{
  "googleMapsApiKey": "${MAPS_KEY}",
  "googleMapsMapId": "${MAP_ID}"
}
EOF

if [ -z "${GOOGLE_MAPS_API_KEY:-}" ]; then
  echo "[runtime-config] GOOGLE_MAPS_API_KEY not set — Google Maps disabled, OSM fallback will be used." >&2
else
  echo "[runtime-config] wrote $TARGET (Google Maps enabled)." >&2
fi
