# Setup

สำหรับติดตั้งบนเซิร์ฟเวอร์จริง (clone จาก GitLab + seed mock) ดูคู่มือเต็มที่ [DEPLOY-SERVER.md](DEPLOY-SERVER.md)

**คู่มือ HTML (dev stack + integration test):** [BFF-DEV-GUIDE.html](BFF-DEV-GUIDE.html)

## Requirements

- Docker Desktop (Compose v2)
- Optional for local Angular only: Node 18+ / 20+

## First run

```bash
cp .env.example .env
# set SECRET_KEY to a random string of at least 32 characters, e.g.
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose up --build
```

The API refuses to start while `SECRET_KEY` is the placeholder (`AUTH_FAIL_FAST=true`).

| URL | Service |
|-----|---------|
| http://localhost:8880/ | Admin (when `HTTP_PORT=8880` in `.env`) |
| http://localhost:8880/company/timestamp-face | Face kiosk |
| http://localhost:8880/health, /ready | liveness / readiness |
| http://localhost:8880/docs | OpenAPI — 404 unless `EXPOSE_API_DOCS=true` and the nginx `/docs` block is re-enabled |
| localhost:5434 | PostgreSQL (BFF dev alongside face-core) |

Default DB credentials are in `.env.example` (`dpu` / `dpu_secret`). Change them before any shared deployment.

**Standalone** (no Face Core on same host): use `POSTGRES_PORT=5432` and `HTTP_PORT=80` in `.env`.

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `HTTP_PORT` | `8880` (BFF dev) / `80` standalone | nginx host port |
| `POSTGRES_PORT` | `5434` (BFF dev) / `5432` standalone | database host port |
| `FACE_RECOGNITION_THRESHOLD` | `0.40` | cosine **distance** cutoff (lower = stricter; local mode) |
| `IMAGE_BLUR_THRESHOLD` | `20.0` | reject blurry kiosk / add-face enroll |
| `IMAGE_BLUR_THRESHOLD_IMPORT` | `0` | Excel+ZIP import blur gate; `0` = do not reject blurry photos (face still required) |
| `SECRET_KEY` | (placeholder) | **required**, ≥ 32 chars; startup fails otherwise |
| `AUTH_FAIL_FAST` | `true` | set `false` only for throwaway local runs |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | `60` / `14` | JWT lifetimes |
| `FACE_ROUTES_REQUIRE_JWT` | `true` | face HTTP + kiosk WS need a token |
| `FACE_DEVICES` | `cuda:0` | comma list; one GPU worker per device |
| `EXPOSE_API_DOCS` | `false` | Swagger/ReDoc |
| `SMTP_*`, `LINE_CHANNEL_ACCESS_TOKEN` | (empty) | notification channels; empty = skipped |
| `IMAGE_RETENTION_DAYS` | `90` | punch-photo retention |
| `FACE_CORE_ENABLED` | `false` | when `true`, `/face/*` BFF proxies vision to Face Core |
| `FACE_CORE_URL` | `http://host.docker.internal:8081` | Face Core base URL |
| `FACE_CORE_API_KEY` | (empty) | Bearer key for Face Core tenant |

Frontends in Docker use `baseUrl: ''` (same origin through nginx).

## Face Core BFF (optional)

Keep Web-Manage URLs (`/face/*`, `/face/ws/kiosk`). Vision + gallery run in sibling **face-core**; check-in / GPS / HR stay in DPU.

**Ports:** copy `.env.example` → `.env` (defaults `POSTGRES_PORT=5434`, `HTTP_PORT=8880` so Postgres does not clash with face-core on `5435`).

Set `FACE_CORE_ENABLED=true` and `FACE_CORE_API_KEY` in DPU `.env`. Set the same string as `BOOTSTRAP_API_KEY` in the face-core `.env`. Both keys must be at least 16 characters and must not be `dev-face-core-key-change-me`. DPU `SECRET_KEY` must be at least 32 characters. The overlay forces `FACE_CORE_URL=http://face-core-api:8000` and keeps the DPU API on CPU (`Dockerfile.bff`). Face Core holds the GPU.

```bash
docker network create face-net   # one-time

# One GPU (verified): Face Core on cuda:0, DPU is the BFF
cd ../face-core
# .env: FACE_DEVICE=cuda:0
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.face-net.yml up -d --build

cd ../dpu-project
docker compose -f docker-compose.yml -f docker-compose.face-core.yml up -d --build
```

No NVIDIA device: swap the Face Core line for `docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.face-net.yml up -d --build` and set `FACE_DEVICE=cpu`. Two GPUs on a Linux server: use `scripts/deploy-stack.sh` (see [DEPLOY-SERVER.md](DEPLOY-SERVER.md) section 10). Do not add `docker-compose.gpu.yml` to the DPU command — that gives the GPU to DPU and leaves Face Core without it.

Expect Face Core `GET http://127.0.0.1:8081/v1/health` to show `device` `cuda:0` (or `cpu`). DPU `GET /ready` on the nginx port must show the same device and `service: face-core`. `GET /face/queue-stats` with a DPU JWT returns `source: face-core`. Set `FACE_CORE_ENABLED=false` and drop the face-core overlay to fall back to local InsightFace.

**Migrate existing enrollments** (does not delete local `face_encoding`):

```bash
cd API-Fast
# DATABASE_URL + FACE_CORE_URL + FACE_CORE_API_KEY must be set
python scripts/migrate_faces_to_face_core.py --dry-run
python scripts/migrate_faces_to_face_core.py
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for ID mapping (`companyId`→`companyCode`, `memberId`→`subjectId`).

## After upgrade from old face_recognition

Old 128-d JSON encodings are incompatible. Re-enroll faces from Admin after first migrate.

## Local Angular against Docker API

Publish API temporarily (add under `api:` in compose):

```yaml
ports:
  - "8000:8000"
```

Then `ng serve` with `environment.ts` → `http://localhost:8000`.

## Demo seed + smoke tests

With the stack up (`docker compose up -d`):

```powershell
.\scripts\seed-and-test.ps1 -Reset
```

Or separately:

```bash
docker compose run --rm -v ./API-Fast:/app --entrypoint python api scripts/seed_demo_data.py --reset
docker compose run --rm -v ./API-Fast:/app --entrypoint python api scripts/smoke_test_api.py --base-url http://api:8000
```

Seed fills all 8 tables. Default password for seeded users: `Password123!`
(accounts: `sysadmin`, `admin`, `boss`, `emp1`, `emp2`).

```bash
docker compose logs -f api
docker compose ps
docker compose down
docker compose down -v   # also wipe DB volume
```
