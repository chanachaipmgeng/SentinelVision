# Setup

สำหรับติดตั้งบนเซิร์ฟเวอร์จริง (clone จาก GitLab + seed mock) ดูคู่มือเต็มที่ [DEPLOY-SERVER.md](DEPLOY-SERVER.md)

## Requirements

- Docker Desktop (Compose v2)
- Optional for local Angular only: Node 18+ / 20+

## First run

```bash
cp .env.example .env
docker compose up --build
```

| URL | Service |
|-----|---------|
| http://localhost/ | Admin |
| http://localhost/company/timestamp-face | Face kiosk |
| http://localhost/docs | OpenAPI |
| localhost:5432 | PostgreSQL |

Default DB credentials are in `.env.example` (`dpu` / `dpu_secret`). Change them before any shared deployment.

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `HTTP_PORT` | `80` | nginx host port |
| `POSTGRES_*` | see `.env.example` | database |
| `FACE_RECOGNITION_THRESHOLD` | `0.40` | cosine **distance** cutoff (lower = stricter; local mode) |
| `SECRET_KEY` | change-me… | rotate for real use |
| `FACE_CORE_ENABLED` | `false` | when `true`, `/face/*` BFF proxies vision to Face Core |
| `FACE_CORE_URL` | `http://host.docker.internal:8081` | Face Core base URL |
| `FACE_CORE_API_KEY` | (empty) | Bearer key for Face Core tenant |

Frontends in Docker use `baseUrl: ''` (same origin through nginx).

## Face Core BFF (optional)

Keep Web-Manage URLs (`/face/*`, `/face/ws/kiosk`). Vision + gallery run in sibling **face-core**; check-in / GPS / HR stay in DPU.

```bash
docker network create face-net   # one-time

# Terminal 1 — Face Core (CPU + Redis scale stack, on face-net)
cd ../face-core
docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.scale.yml up -d --build

# Terminal 2 — DPU API (CPU image, BFF → face-core-api:8000)
cd ../dpu-project
docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.face-core.yml up -d --build api
```

Overlay sets `FACE_CORE_ENABLED=true` and `FACE_CORE_URL=http://face-core-api:8000` (Docker DNS on `face-net` — not host port 8081). Set `FACE_CORE_ENABLED=false` to fall back to local InsightFace + pgvector.

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
