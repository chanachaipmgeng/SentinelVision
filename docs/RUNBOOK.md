# Runbook

## Backup, restore & drill (B5)

### Targets
| | Target | How it is met |
|---|---|---|
| RPO | **24 h** (1 h possible) | `docker-compose.backup.yml` sidecar runs `scripts/backup.sh` every `BACKUP_INTERVAL_SECONDS` (default 86400; set 3600 for hourly). Punch photos are also written to `uploaded_images` on the volume, so a lost day = one day of punches/enrolments. |
| RTO | **≤ 30 min** on the same host, **≤ 2 h** on a fresh host | `scripts/restore.sh STAMP --yes --stop-api` (pg_restore + untar; minutes for a DB of thousands of members), plus `docker compose up` on a new host and pulling the backup set from the offsite copy. |
| Retention | 14 days local (`BACKUP_KEEP_DAYS`), offsite per bucket lifecycle | `find -mtime` rotation in `backup.sh`; offsite copy via `BACKUP_RCLONE_REMOTE` / `BACKUP_S3_URI`. |
| Drill | weekly, automated | sidecar runs `restore-drill.sh` after every `BACKUP_DRILL_EVERY` (7) backups; a failed drill logs `DRILL FAILED` and posts `backup.drill.fail` to `/notifications/system` when `SERVICE_NOTIFY_TOKEN` is set. |

### What a backup set contains
`BACKUP_DIR/dpu-<STAMP>.dump` (pg_dump custom format, `--no-owner`, whole `public` schema or `--schema=$DB_SCHEMA`), `dpu-<STAMP>-images.tar.gz` (`uploaded_images` + `enrolled_images`; `temp_images` is scratch), `dpu-<STAMP>.manifest.json` (row count of every table, file counts, sha256) and `dpu-<STAMP>.sha256`. `face-core-<STAMP>.dump` is added when a `face-core-db` container is running on the same host. All credentials come from `.env` / the environment — after rotating `POSTGRES_PASSWORD` nothing else needs to change.

### Run it
```bash
# sidecar (daily + weekly drill); BACKUP_DIR must be writable by BACKUP_UID:BACKUP_GID
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.backup.yml up -d --build backup
docker compose ... run --rm backup backup.sh          # one-off backup
docker compose ... run --rm backup restore-drill.sh   # one-off drill into a scratch DB on dpu-db
# or from the host with the docker CLI (reads .env; runs pg_dump inside dpu-db)
scripts/backup.sh                 # → ./backups
scripts/restore-drill.sh          # newest set, scratch pgvector container
```
Offsite: set `BACKUP_RCLONE_REMOTE=backup:bucket/dpu` and `RCLONE_CONFIG_BACKUP_*` in `.env` (S3-compatible, including MinIO via `RCLONE_CONFIG_BACKUP_ENDPOINT`). Host cron alternative: `0 2 * * * cd /opt/SentinelVision && scripts/backup.sh >> /var/log/dpu-backup.log 2>&1`.

### Drill procedure (what `restore-drill.sh` proves)
1. `sha256sum -c` on the set.
2. Restore into a scratch target: a throw-away `pgvector/pgvector:pg16` container with a random password (`DRILL_TARGET=container`, host default) or `dpu_drill_<ts>` on the live server (`DRILL_TARGET=database`, sidecar default). Production data is never touched.
3. Every table's `count(*)` must equal the manifest.
4. Face match query: the newest `face_encoding` row must be its own top-1 under `ORDER BY embedding <=> …` with cosine similarity ≥ 0.999 and the HNSW index must exist — proves pgvector and the index restored.
5. `tar tzf` file count must equal `uploadedFiles + enrolledFiles` from the manifest.
6. Scratch target dropped (keep it with `DRILL_KEEP=1`). Exit 0 only if every step passed.

Record each manual drill (date, stamp, duration, result) in the ops log; the sidecar's automated runs are in `docker logs dpu-backup`.

### Real restore
```bash
scripts/restore-drill.sh 20260107-020000            # rehearse first
scripts/restore.sh 20260107-020000 --yes --stop-api # stops dpu-api/dpu-api-gpu1, pg_restore --clean, untar, chown 10001, starts API
curl -s localhost/ready && docker logs --tail 50 dpu-api
```
Then enrol one face and perform one check-in. `--db-only` / `--images-only` restore one half; on a fresh host start `db` first (`docker compose up -d db api`) so the volumes exist, then restore. Restoring to a different `DB_SCHEMA` requires `CREATE EXTENSION vector` first (the drill does this automatically).

## 502 after recreate
`docker compose up -d --build nginx` so the gateway re-resolves `api`. Check `GET /ready`.

## GPU driver mismatch
If `nvidia-smi` says driver/library mismatch, reboot the host so the kernel module matches the userspace libraries. Do not start `dpu-api` until `nvidia-smi` succeeds.

## 413 on import
Host TLS nginx must set `client_max_body_size 500m`. See `docker/nginx/tls-edge.example.conf`.

## Weak SECRET_KEY / example database password
The API refuses to start when `AUTH_FAIL_FAST=true` and `SECRET_KEY` is shorter than 32 characters or still `change-me-in-production`. Set a new secret and restart `api`. Existing tokens become invalid.

In production mode (`APP_ENV` unset or `production`) it also refuses an example database password (`dpu_secret`, `postgres`, `password`, …) in `DATABASE_URL` with `POSTGRES_PASSWORD / DATABASE_URL still uses an example password`. Fix: set a real `POSTGRES_PASSWORD` in `.env`, rotate the role (`ALTER ROLE dpu PASSWORD '...'` on the running `dpu-db`, or let a fresh volume initialise with it) and recreate `api` / `api-gpu1`. `docker compose` itself aborts with `required variable POSTGRES_PASSWORD is missing` when the variable is absent. `APP_ENV=development` turns the password check into a warning for laptops only.

## Upgrade to non-root containers (B4)
Images built from this release run the API as uid 10001 (`app`) and admin/nginx as uid 101. Named volumes created by older root containers stay root-owned, and the API now aborts at startup with `image directories are not writable by uid 10001` instead of failing on the first upload. One-time fix per host:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.prod.yml up -d --build
docker run --rm --volumes-from dpu-api alpine chown -R 10001:10001 /app/enrolled_images /app/uploaded_images /app/temp_images
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.prod.yml restart api api-gpu1
docker exec dpu-api id        # uid=10001(app)
```

Other changes to apply on upgrade: `admin` and `nginx` listen on **8080** inside the network (`HTTP_PORT` on the host is unchanged); Postgres is published on `127.0.0.1:${POSTGRES_PORT}` only (none with the prod overlay); `/metrics` and `/docs` answer only to `INTERNAL_ALLOW_CIDRS`; `/auth/login` is rate limited (20/min per IP, burst 10) — raise the zones in `docker/nginx/00-dpu-http.conf` if a NAT hides many admins behind one address.

## Leaked secrets / PII in git
`API-Fast/.env`, 811 face images, a scratch `.xlsx` and a load-test dump were tracked until roadmap A2. They are untracked now but still in history. Follow `docs/SECRETS-REMEDIATION.md` for the `git filter-repo` purge, the key-rotation checklist (`SECRET_KEY`, `POSTGRES_PASSWORD`, Google Maps, Firebase) and the re-clone notice. The Google Maps key is injected at runtime via `GOOGLE_MAPS_API_KEY` → `assets/config.json`; change it with `docker compose up -d admin`, no rebuild.

## Kiosk pairing (provision a tablet)
Kiosk tablets no longer receive a token in a URL. Each device is paired once with a short-lived code:

1. Admin: `/company/hr-schedule` → tab **ความปลอดภัย** → enter a device name → **สร้างอุปกรณ์และรหัสจับคู่**. The UI shows an 8-character `pairingCode` (`ABCD-EFGH`) **once**; it expires after `KIOSK_PAIRING_CODE_TTL_MINUTES` (default 10). Equivalent API: `POST /hr/company/{companyId}/kiosk-devices {"name": "..."}`.
2. Tablet: open `https://<host>/kiosk/pair`, type the code, tap **จับคู่อุปกรณ์**. The tablet calls `POST /auth/kiosk/pair`, stores the device token pair in `sessionStorage` for that tab only, and is redirected to `/company/timestamp-face`. The kiosk refreshes its own token via `/auth/kiosk/refresh` (rotation) when the WebSocket reports `token_expiring`.
3. Verify in the admin table: status changes from **รอจับคู่** to **จับคู่แล้ว** and `lastSeenAt` updates.

Operations:
- **Code expired / typo**: click **ออกรหัสใหม่** on the device row (`POST .../kiosk-devices/{deviceId}/pairing-code`). This also revokes any token the device already holds, so use it to force a re-pair after a tablet is lost.
- **Decommission**: **เพิกถอนสิทธิ์** (`DELETE .../kiosk-devices/{deviceId}`). The device token family is denied within `AUTH_REVOCATION_CACHE_SECONDS` (default 30 s) on every replica; the tablet is sent back to `/kiosk/pair` on its next request. Revoked devices cannot be re-paired — register a new device.
- **Tablet closed the tab / cleared storage**: re-issue a code (step above) and pair again.
- **Legacy `?kioskToken=` URLs** (pre-A5, 365-day tokens) still validate until they expire or the device is revoked, but can no longer be issued. Revoke those devices and re-pair them.
- Tuning: `KIOSK_TOKEN_EXPIRE_HOURS` (device token, default 12), `KIOSK_REFRESH_EXPIRE_DAYS` (default 30), `KIOSK_PAIR_MAX_ATTEMPTS_PER_MINUTE` (per-IP brute-force limit at `/auth/kiosk/pair`, default 10).

## Logout, token revocation & refresh rotation
- `POST /auth/logout` (UI: header → Log Out) revokes the access token, the refresh token and their session family (`fam`). The row lives in `revoked_token` until the token would have expired; `revocation_purge_loop` deletes expired rows every `AUTH_REVOCATION_PURGE_SECONDS`.
- Refresh tokens are single use. If a user is unexpectedly logged out with `Refresh token reuse detected`, a refresh token was replayed (stolen copy or two tabs racing on stale storage): the whole session was revoked on purpose. Log in again; investigate if it repeats for the same account.
- To revoke every session of one account without a DB script, reset the password and ask the user to log in again (new family). Existing tokens issued before this release carry no `jti` and expire naturally (access ≤ `ACCESS_TOKEN_EXPIRE_MINUTES`, refresh ≤ `REFRESH_TOKEN_EXPIRE_DAYS`).
- `?token=` in URLs is rejected. If an old integration still depends on it, set `AUTH_ALLOW_QUERY_TOKEN=true` temporarily; every use is logged as `deprecated ?token= used` so you can find and fix the caller.

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
Existing databases apply idempotent DDL via `src/utils/schema_migrate.py` at startup. After pulling the latest revisions, run `alembic stamp 0008_revocation_kiosk_pairing` inside `dpu-api` (needs `DATABASE_URL`). Fresh databases can run `alembic upgrade head` after `create_all`. Revision `0007_face_encoding_company_id` adds `face_encoding."companyId"` (backfilled) and revision `0008_revocation_kiosk_pairing` adds `revoked_token` and the kiosk pairing columns on `kiosk_device` (`token_hash` becomes nullable).
