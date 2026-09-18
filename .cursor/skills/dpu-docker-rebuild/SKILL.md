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

Production adds `-f docker-compose.prod.yml` (no published Postgres port, resource limits).

## Before `up`

`SECRET_KEY` in `.env` must be a random string of at least 32 characters. With the placeholder, `dpu-api` exits during import (`AUTH_FAIL_FAST=true`) and nginx never becomes healthy. Rotating the secret invalidates existing tokens.

## Verify

```bash
docker ps --filter name=dpu-
curl -s -o NUL -w "%{http_code}\n" http://localhost/health      # 200
curl -s -o NUL -w "%{http_code}\n" http://localhost/ready       # 200 (DB + GPU queue)
curl -s -o NUL -w "%{http_code}\n" http://localhost/companys    # 401 (auth enforced)
curl -s -o NUL -w "%{http_code}\n" http://localhost/docs        # 404 (docs closed)
# with a token from POST /auth/login
curl -s -H "Authorization: Bearer $TOKEN" http://localhost/face/queue-stats
```

Expect `dpu-api` healthy, queue `"started": true`, `devices` listing every `FACE_DEVICES` entry. Stack services: `db`, `api`, `admin`, `nginx` (no mobile app).

API logs are JSON lines (`{"level": ..., "logger": ..., "message": ...}`); each response carries `x-request-id`.

After **admin** rebuild, also smoke SPA routes (expect `200`):

- `/`, `/admin/home`, `/company/dashboard`, `/company/timestamp-face`, `/admin/system-setting`

Kiosk fullscreen is CSS-only (`dpu-kiosk-mode`); no API rebuild required for shell/UI-only changes.

## 502 after API recreate

Nginx may hold a stale API IP. Rebuild/restart `dpu-nginx`; keep `resolver 127.0.0.11` + variable `proxy_pass` in `docker/nginx/default.conf`.

## Auth smoke (after security changes)

1. `POST /auth/login` → `accessToken`, `refreshToken`, `mustChangePassword`
2. `GET /companys` with a company-admin token → 403; with system admin → 200
3. `GET /employees/company/{otherCompanyId}` as company admin → 403
4. `POST /auth/refresh-token` with `refreshToken` → new pair; with the access token → 401
5. `GET /images/x.jpg` → 401; `?token=` → 404 (authorized, missing file)
6. Kiosk WS `session` without `token` → `{"type":"error"}`

## Do not

- Bind-mount expecting live Python/TS reload — images bake source
- `docker compose down -v` unless user wants DB wipe
- Rewrite `.env` secrets on the user's behalf; ask or pass `SECRET_KEY` in the shell for a one-off test
