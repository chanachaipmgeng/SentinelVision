---
name: dpu-docker-rebuild
description: >-
  Rebuilds and verifies the DPU Docker stack (api, api-gpu1, admin, nginx, GPU
  overlay, optional loadgen). Use when deploying code changes, fixing 502 after
  container recreate, checking face GPU queue / dual-GPU pin, or service health.
---

# DPU Docker rebuild

## Commands

From repo root:

```bash
# Dual-GPU local InsightFace (api + api-gpu1 + nginx dual upstream)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

# Rebuild APIs only (both processes share the API image build context)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build api api-gpu1

# Admin UI
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build admin

# Nginx (WS / dual upstream — recreate with APIs so IPs stay fresh)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --force-recreate nginx

# Common trio after face/kiosk work
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build api api-gpu1 admin nginx
```

Production adds `-f docker-compose.prod.yml` (no published Postgres port, resource limits).

BFF (Face Core holds the GPUs): `-f docker-compose.face-core.yml` after `docker network create face-net` (same host), or `-f docker-compose.face-core-remote.yml` with `FACE_CORE_URL` for a remote `:8081`. Prefer **dual-API** for single-host saturation; Face Core when scaling across hosts. `scripts/deploy-stack.sh` starts face-core first, waits for `/v1/ready`, then DPU, then smokes `/health` `/ready` `/docs` `/companys`.

Loadgen on the same network:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml \
  -f docker-compose.loadtest.yml --profile loadtest run --rm \
  -e KIOSK_LOAD_USER=... -e KIOSK_LOAD_PASSWORD=... \
  loadgen --profile idle --kiosks 1,4 --hold 20 --jsonl /results/idle.jsonl
```

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

Expect:

- `dpu-api` **and** `dpu-api-gpu1` healthy (dual-GPU overlay)
- each queue `"started": true`, `devices=['cuda:0']`, `workers` = `FACE_GPU_WORKERS`
- after first inference: `nvidia-smi --query-compute-apps` shows a python process on **GPU0 and GPU1**

Stack services: `db`, `api`, `api-gpu1`, `admin`, `nginx` (no mobile app).

API logs are JSON lines (`{"level": ..., "logger": ..., "message": ...}`); each response carries `x-request-id`. Look for `provider_options` / `Face GPU queue started` on both APIs.

After **admin** rebuild, also smoke SPA routes (expect `200`):

- `/`, `/admin/home`, `/company/dashboard`, `/company/timestamp-face`, `/admin/system-setting`

Kiosk fullscreen is CSS-only (`dpu-kiosk-mode`); no API rebuild required for shell/UI-only changes.

## 502 after API recreate

Dual-GPU nginx uses a static upstream list — recreate `dpu-nginx` whenever `api` / `api-gpu1` are recreated. Single-upstream `default.conf` uses `resolver 127.0.0.11` + variable `proxy_pass`.

## Auth smoke (after security changes)

1. `POST /auth/login` → `accessToken`, `refreshToken`, `mustChangePassword`
2. `GET /companys` with a company-admin token → 403; with system admin → 200
3. `GET /employees/company/{otherCompanyId}` as company admin → 403
4. `POST /auth/refresh-token` with `refreshToken` → new pair; with the access token → 401
5. `GET /images/x.jpg` → 401; `?token=` → 404 (authorized, missing file)
6. Kiosk WS `session` without `token` → `{"type":"error"}`

## Capacity / loadtest

- Monolith dual/hexa: [docs/KIOSK-LOADTEST-SATURATION.md](../../docs/KIOSK-LOADTEST-SATURATION.md)
- Face Core identify (local or remote BFF): [docs/FACE-CORE-IDENTIFY-CAPACITY.md](../../docs/FACE-CORE-IDENTIFY-CAPACITY.md) §6.6–§6.7
- Frames: `--frame-width 1280 --jpeg-quality 70` · profile `identify` / `rush`

Remote A+1 tip: raise Face Core `FACE_GPU_WORKERS` (2–3), `FACE_GPU_QUEUE_SIZE` + `FACE_GPU_MAX_PENDING_PER_COMPANY` (128), `RATE_LIMIT_*`, and hard-pin GPUs with `device_ids` — otherwise WS detect storms → 429 → DPU `face_core_down` circuit.

## Next tests (BFF, not required for single-host GPU saturation)

Run on a host that has both checkouts and `face-net`, or local DPU + remote `:8081`. Do not migrate production faces until 1–4 pass.

1. Face Core `GET /v1/ready` 200 with `BOOTSTRAP_API_KEY` set (placeholder must fail startup). Dual-GPU: both GPU UUIDs show Face Core in `nvidia-smi`.
2. DPU with `docker-compose.face-core.yml` or `face-core-remote.yml`: `GET /ready` 200 and body includes Face Core health. Stop `face-core-api` → `/ready` 503 `face_core_down`, then recover.
3. `GET /face/queue-stats` with a DPU JWT returns `source: face-core`. Kiosk WS `session` with token → `session_ok`; without token → error. Leave the socket open past the warning window → `token_expiring` then a new `session`.
4. Company admin of company A: face `identify` / `POST /departments` for company B → 403.
5. `scripts/migrate-faces.sh` dry-run, then real, on a copy of the DB. Face count on Face Core equals `face_encoding` per company. Spot-check 20 `POST /v1/verify`. Rollback = drop the BFF overlay; local rows stay.
6. Stop `face-core-gpu1` only. Identify still succeeds on GPU0.
7. Soft-delete an employee → gone from `GET /employees/company/{id}`; row still in Postgres with `deleted_at`.
8. Excel import via UI polls `import-jobs` until `done`.

## Do not

- Bind-mount expecting live Python/TS reload — images bake source
- `docker compose down -v` unless user wants DB wipe
- Rewrite `.env` secrets on the user's behalf; ask or pass `SECRET_KEY` in the shell for a one-off test
- Put both physical GPUs in one API process without verifying `nvidia-smi` compute-apps per UUID
