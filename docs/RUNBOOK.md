# Runbook

## RPO / RTO
- RPO: 24 hours when `scripts/backup.sh` runs once a day.
- RTO: time to `psql` restore the dump plus copy `api_uploaded` / `api_enrolled` volumes.

## 502 after recreate
`docker compose up -d --build nginx` so the gateway re-resolves `api`. Check `GET /ready`.

## GPU driver mismatch
If `nvidia-smi` says driver/library mismatch, reboot the host so the kernel module matches the userspace libraries. Do not start `dpu-api` until `nvidia-smi` succeeds.

## 413 on import
Host TLS nginx must set `client_max_body_size 500m`. See `docker/nginx/tls-edge.example.conf`.

## Weak SECRET_KEY
The API refuses to start when `AUTH_FAIL_FAST=true` and `SECRET_KEY` is shorter than 32 characters or still `change-me-in-production`. Set a new secret and restart `api`. Existing tokens become invalid.

## Biometric data
Face vectors in `face_encoding` are required for matching when DPU runs InsightFace itself. In BFF mode Face Core owns embeddings; DPU keeps timestamps and punch photos. `temp_images` can be deleted; the retention loop removes them after `TEMP_RETENTION_HOURS`.

## Face Core down
`/ready` returns 503 `face_core_down` when `FACE_CORE_URL/v1/health` fails. The kiosk shows scan errors and the API opens a 15 second circuit instead of retrying every frame. Restart `face-core-api` on `face-net`, then `dpu-api`.

## Rotate Face Core key
Create a key with `POST /v1/api-keys` on face-core, put it in DPU `.env` as `FACE_CORE_API_KEY`, recreate `dpu-api`, then revoke the old key.

## One GPU down
Stop `face-core-gpu1`. `face-api` on `cuda:0` keeps serving the Redis queue. Start `face-core-gpu1` again when the second card is back.

## Work Shifts & Attendance Export
- Default company shift is `09:00` – `18:00` (`Asia/Bangkok`) with `15` minutes grace period. Update per company via `PUT /timestamp/company/{companyId}/shift-settings`.
- Attendance exports (`GET /timestamp/export/company/{companyId}?format=xlsx|csv`) stream up to 5,000 rows per request.

## Multi-Replica Notification Outbox
- `drain_outbox` uses PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`, making it safe to run multiple `dpu-api` replicas concurrently without duplicate Email / LINE / Webhook deliveries.
- Daily missing-attendance cutoff state is stored in `system_setting` under `key = "cutoff_sent:{companyId}"`.

## Alembic Migrations
Existing databases apply idempotent DDL via `src/utils/schema_migrate.py` at startup. After pulling the latest revisions, run `alembic stamp 0003_enterprise_shifts_and_indexes` inside `dpu-api` (needs `DATABASE_URL`). Fresh databases can run `alembic upgrade head` after `create_all`.
