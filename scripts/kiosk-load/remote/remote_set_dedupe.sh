#!/bin/bash
# Temporarily set CHECK_IN_DEDUPE_SECONDS and recreate API stack (quad).
set -euo pipefail
VAL="${1:?0 or 300}"
PW="${DPU_SUDO_PW:-}"
sd() { echo "$PW" | sudo -S -p '' "$@"; }
ENVF=/opt/facescan-timeattendance/.env
cd /opt/facescan-timeattendance
if sd grep -q '^CHECK_IN_DEDUPE_SECONDS=' "$ENVF"; then
  sd sed -i "s/^CHECK_IN_DEDUPE_SECONDS=.*/CHECK_IN_DEDUPE_SECONDS=${VAL}/" "$ENVF"
else
  echo "CHECK_IN_DEDUPE_SECONDS=${VAL}" | sd tee -a "$ENVF" >/dev/null
fi
sd grep '^CHECK_IN_DEDUPE_SECONDS=' "$ENVF" || true
sd docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.gpu-x2.yml \
  up -d --force-recreate api api-gpu0b api-gpu1 api-gpu1b 2>&1 | tail -30
for i in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:8880/ready >/dev/null 2>&1; then
    echo ready_ok
    curl -fsS http://127.0.0.1:8880/ready | head -c 220; echo
    exit 0
  fi
  sleep 3
done
echo ready_timeout
exit 1
