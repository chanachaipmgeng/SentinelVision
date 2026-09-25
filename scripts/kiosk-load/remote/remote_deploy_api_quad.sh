#!/usr/bin/env bash
# Pull latest and rebuild quad API containers (nginx untouched).
set -euo pipefail
PW="${DPU_SUDO_PW:-}"
sd() { printf '%s\n' "$PW" | sudo -S -p '' "$@"; }
cd /opt/facescan-timeattendance
sd -u "$(whoami)" git pull --ff-only || sd git pull --ff-only
sd docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.gpu-x2.yml \
  up -d --build --no-deps api api-gpu1 api-gpu0b api-gpu1b
sd docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.gpu-x2.yml ps
curl -sS -m 20 http://127.0.0.1:8880/ready | head -c 400
echo
echo deploy_api_ok
