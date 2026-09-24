#!/bin/bash
# Deploy quad nginx conf and recreate nginx only.
set -euo pipefail
PW="${DPU_SUDO_PW:-}"
CONF_SRC="${1:-/tmp/default.quad-gpu.conf}"
printf '%s\n' "$PW" | sudo -S -p '' -v
cd /opt/facescan-timeattendance
sudo -n cp "$CONF_SRC" docker/nginx/default.quad-gpu.conf
# Show upstream lines
grep -n 'max_fails\|fail_timeout\|server api' docker/nginx/default.quad-gpu.conf | head -20
sudo -n docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.gpu-x2.yml \
  up -d --force-recreate --no-deps nginx
sleep 3
sudo -n docker exec dpu-nginx nginx -t
sudo -n docker exec dpu-nginx grep -E 'max_fails|fail_timeout' /etc/nginx/conf.d/default.conf | head -10
curl -fsS http://127.0.0.1:8880/ready | head -c 220; echo
echo deploy_nginx_ok
