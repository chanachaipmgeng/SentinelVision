---
name: dpu-docker-rebuild
description: >-
  Rebuilds and verifies the DPU Docker stack (api, admin, nginx, GPU overlay).
  Use when deploying code changes, fixing 502 after container recreate, or
  checking face GPU queue / service health.
---

# DPU Docker rebuild

## Commands

From repo root:

```bash
# API + GPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build api

# Admin UI
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build admin

# Nginx (WS / proxy config)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build nginx

# Common trio after face/kiosk work
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build api admin nginx
```

## Verify

```bash
docker ps --filter name=dpu-
curl -s http://localhost/face/queue-stats
curl -s -o NUL -w "%{http_code}" http://localhost/docs
```

Expect `dpu-api` healthy, queue `"started": true`. Stack services: `db`, `api`, `admin`, `nginx` (no mobile app).

After **admin** rebuild, also smoke SPA routes (expect `200`):

- `/`, `/admin/home`, `/company/dashboard`, `/company/timestamp-face`, `/admin/system-setting`

Kiosk fullscreen is CSS-only (`dpu-kiosk-mode`); no API rebuild required for shell/UI-only changes.

## 502 after API recreate

Nginx may hold a stale API IP. Rebuild/restart `dpu-nginx`; keep `resolver 127.0.0.11` + variable `proxy_pass` in `docker/nginx/default.conf`.

## Do not

- Bind-mount expecting live Python/TS reload — images bake source
- `docker compose down -v` unless user wants DB wipe
