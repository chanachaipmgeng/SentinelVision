#!/bin/sh
# Bring up Face Core then DPU BFF on one host. Idempotent.
# Expects sibling checkouts:
#   /opt/face-core
#   /opt/facescan-timeattendance   (this repo)
# Override with FACE_CORE_DIR and DPU_DIR.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
DPU_DIR=${DPU_DIR:-$ROOT}
FACE_CORE_DIR=${FACE_CORE_DIR:-$(dirname "$DPU_DIR")/face-core}

reject_default() {
  file=$1
  key=$2
  bad=$3
  val=$(grep -E "^${key}=" "$file" | head -1 | cut -d= -f2- || true)
  if [ -z "$val" ] || [ "$val" = "$bad" ] || [ ${#val} -lt 16 ]; then
    echo "$file: $key must be set (>=16 chars, not '$bad')" >&2
    exit 1
  fi
}

reject_default "$DPU_DIR/.env" SECRET_KEY change-me-in-production
reject_default "$DPU_DIR/.env" FACE_CORE_API_KEY dev-face-core-key-change-me
reject_default "$FACE_CORE_DIR/.env" BOOTSTRAP_API_KEY dev-face-core-key-change-me

docker network create face-net >/dev/null 2>&1 || true

echo "starting face-core"
(
  cd "$FACE_CORE_DIR"
  docker compose -f docker-compose.yml -f docker-compose.gpu.yml \
    -f docker-compose.scale.yml -f docker-compose.dual-gpu.yml \
    -f docker-compose.face-net.yml -f docker-compose.prod.yml up -d --build
)
python - <<'PY'
import time, urllib.request
for _ in range(60):
    try:
        urllib.request.urlopen("http://127.0.0.1:8081/v1/ready", timeout=3)
        print("face-core ready")
        break
    except Exception:
        time.sleep(5)
else:
    raise SystemExit("face-core /v1/ready did not become ready")
PY

echo "starting dpu bff"
(
  cd "$DPU_DIR"
  docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    -f docker-compose.face-core.yml up -d --build
)
python - <<'PY'
import time, urllib.request
base = "http://127.0.0.1"
for _ in range(40):
    try:
        urllib.request.urlopen(base + "/ready", timeout=3)
        print("dpu ready")
        break
    except Exception:
        time.sleep(5)
else:
    raise SystemExit("dpu /ready did not become ready")
PY

echo "smoke"
python - <<'PY'
import urllib.request
base = "http://127.0.0.1"
checks = {
    "/health": 200,
    "/ready": 200,
    "/docs": 404,
    "/companys": 401,
}
for path, expect in checks.items():
    try:
        urllib.request.urlopen(base + path, timeout=5)
        code = 200
    except Exception as exc:
        code = getattr(getattr(exc, "code", None), "real", None) or getattr(exc, "code", 0)
    print(path, code)
    if code != expect:
        raise SystemExit(f"{path} expected {expect} got {code}")
print("smoke ok")
PY
