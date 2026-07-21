# Setup

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
| http://localhost/mobile/ | Mobile |
| http://localhost/docs | OpenAPI |
| localhost:5432 | PostgreSQL |

Default DB credentials are in `.env.example` (`dpu` / `dpu_secret`). Change them before any shared deployment.

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `HTTP_PORT` | `80` | nginx host port |
| `POSTGRES_*` | see `.env.example` | database |
| `FACE_RECOGNITION_THRESHOLD` | `0.40` | cosine **distance** cutoff (lower = stricter) |
| `SECRET_KEY` | change-me… | rotate for real use |

Frontends in Docker use `baseUrl: ''` (same origin through nginx).

## After upgrade from old face_recognition

Old 128-d JSON encodings are incompatible. Re-enroll faces from Admin after first migrate.

## Local Angular against Docker API

Publish API temporarily (add under `api:` in compose):

```yaml
ports:
  - "8000:8000"
```

Then `ng serve` with `environment.ts` → `http://localhost:8000`.

## Useful compose commands

```bash
docker compose logs -f api
docker compose ps
docker compose down
docker compose down -v   # also wipe DB volume
```
