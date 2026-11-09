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
docker run --rm --volumes-from dpu-api alpine chown -R 10001:10001 /app/enrolled_images /app/uploaded_images /app/temp_images /app/import_jobs
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

## Multi-Replica Notification Outbox (D3)
- `drain_outbox` uses PostgreSQL `SELECT ... FOR UPDATE SKIP LOCKED`, making it safe to run multiple `worker` replicas concurrently without duplicate Email / LINE Messaging / Webhook deliveries.
- **LINE Messaging API** (`POST {LINE_MESSAGING_API_BASE}/message/push`) replaced LINE Notify. Needs a channel access token (`LINE_CHANNEL_ACCESS_TOKEN` or per-company setting) **and** a per-user `lineUserId` (stored in `notification_preference`).
- Secrets in outbox / notify settings (`lineToken`, `webhookSecret`, `lineChannelAccessToken`) are Fernet-sealed when `OUTBOX_ENCRYPTION_KEY` is set (url-safe Fernet key from env — never commit it). Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
- Daily missing-attendance cutoff state is stored in `system_setting` under `key = "cutoff_sent:{companyId}"`.
- Since B7 the dispatcher runs in the `worker` service, not in `dpu-api`. A row that fails `OUTBOX_MAX_ATTEMPTS` (5) deliveries is marked `failed` and stamped `deadLetteredAt`; retry from `/company/notification-center` (Dead letter tab) or `POST /notifications/company/{id}/dead-letter/{outboxId}/retry`.
- In-app notification center: `/company/notification-center` → Inbox / Dead letter / Preferences / Templates (i18n keys under `notify.*`).

## PDPA / Record of Processing (RoPA) — D4 brief
| Activity | Data | Purpose | Lawful basis | Retention (default / per-company) | Recipients |
|---|---|---|---|---|---|
| Face enrollment | Face image + 512-d embedding + consent version/text | Identify employee for attendance / access | Explicit consent (`biometric_consent_*` on `member`; version+text on kiosk/enroll) | `retention:{companyId}.biometricDays` (default `IMAGE_RETENTION_DAYS`) | GPU face workers (in-process / Face Core); no third-party AI SaaS |
| Punch photo | JPEG on punch (`employee_timestamp.photoTimestamp`) | Dispute / audit of check-in | Legitimate interest / employment | `punchPhotoDays` | Company admins; payroll export excludes raw images |
| Sentinel incident snapshot | Frame crop on watchlist/access hit | Security investigation | Legitimate interest / legal obligation | `incidentSnapshotDays` | Company security operators |
| Notification outbox | Event payload (+ sealed channel secrets) | Deliver LINE/email/webhook alerts | Legitimate interest | Purged after send / dead-letter review | LINE Messaging API, SMTP, customer webhook |
| Audit log | Actor, path, companyId | Accountability | Legal obligation | Backup retention (see B5) | System / company admins |

**DSAR:** `GET /hr/company/{companyId}/members/{memberId}/dsar-export` (JSON; embeddings flagged present, not exported raw). **Erasure:** `POST .../erasure` or revoke consent — deletes encodings, punch photos, incident snapshots and clears consent fields. Per-type retention is applied by the worker `retention` job via `company_retention_tick`.

## Background worker (B7)
- `worker` (same image as `api`, `python -m src.worker`, no GPU) runs four jobs: `outbox` (notification dispatcher + daily attendance cutoff, every `NOTIFY_POLL_SECONDS`), `retention` (temp / uploaded image purge, expired Sentinel identities, finished import payloads older than `IMPORT_JOB_RETENTION_DAYS`, orphaned import jobs; every `WORKER_RETENTION_INTERVAL_SECONDS`), `imports` (Excel + ZIP employee import, polled every `WORKER_IMPORT_POLL_SECONDS`), and `attendance_summary` (C1 nightly recompute of `attendance_daily` for yesterday Asia/Bangkok; every `WORKER_ATTENDANCE_SUMMARY_INTERVAL_SECONDS`, default 6h — punch/leave/holiday hooks also recompute same-day). Select with `WORKER_JOBS=outbox,retention,imports,attendance_summary`; scale with `docker compose up -d --scale worker=2` — every job claims rows with `FOR UPDATE SKIP LOCKED`.
- The API only accepts the upload: `POST /employees/company/{id}/import-jobs` stores the files under `IMPORT_JOB_DIR` (`/app/import_jobs`, volume `api_import_jobs` shared by `api`, `api-gpu1` and `worker`) and inserts an `import_job` row (`pending`). The worker claims it (`running`, `lockedBy`, `attempts`), updates `progress` (`processed/total/success/failed/facesEnrolled`) and finishes with `done` / `failed`; Web-Manage polls `GET .../import-jobs/{jobId}`. A `running` job whose `heartbeatAt` is older than `WORKER_IMPORT_LEASE_SECONDS` (900) is failed by the retention job (`importJobsOrphaned`) so the UI never spins forever; re-upload the file.
- Single-container dev: `RUN_BACKGROUND_JOBS_IN_API=true` runs the same job loops inside `dpu-api` (startup logs a warning). Default is `false`; a stack without a `worker` then accumulates `pending` outbox rows and import jobs (alert `DpuImportJobsStuck`, `DpuOutboxLag`).
- Cron / one-shot mode: `docker compose run --rm worker python -m src.worker --once [--jobs outbox,retention] [--worker-id cron-1]` runs each job once and exits 0 only when every job succeeded (`1` otherwise). Metrics port is disabled in `--once` mode; the long-running worker serves `:9108/metrics` (`WORKER_METRICS_PORT`) and this is also its healthcheck.
- Graceful shutdown: SIGTERM / SIGINT stop new iterations and wait up to `WORKER_SHUTDOWN_GRACE_SECONDS` (30; compose `stop_grace_period: 45s`) for the running import row to finish before cancelling. Import progress is persisted per row, so a cancelled job is re-claimed by the next worker (`attempts` + 1) after the lease expires.
- Health: `dpu_job_runs_total{job_name,result}`, `dpu_job_duration_seconds`, `dpu_job_last_success_timestamp_seconds`, `dpu_import_jobs_pending` / `_running`, `dpu_import_job_duration_seconds`, `dpu_import_rows_total{result}`; `docker compose logs -f worker` prints JSON lines with `"service": "worker"` and `"job"`.

## Observability & alerts
- `GET /metrics` (api) and `http://worker:9108/metrics` (worker) expose Prometheus text via `prometheus_client`. Key series: `dpu_http_requests_total{method,route,status}`, `dpu_http_request_duration_seconds`, `dpu_face_gpu_queue_pending{kind}` / `_capacity` / `_wait_seconds` / `dpu_face_gpu_processing_seconds`, `dpu_face_match_duration_seconds{source}`, `dpu_ws_kiosk_connections`, `dpu_outbox_pending` / `dpu_outbox_oldest_pending_age_seconds` / `dpu_outbox_deliveries_total{channel,result}`, `dpu_import_jobs_*`, `dpu_job_runs_total{job_name,result}` / `dpu_job_last_success_timestamp_seconds`, `dpu_db_pool_*`, `dpu_ready_status{component}`. `/metrics` is unauthenticated inside the stack (Prometheus scrapes `api:8000` / `worker:9108` directly on the compose network); at the gateway nginx only answers `/metrics` to `INTERNAL_ALLOW_CIDRS` (B4).
- Dashboards as code: `docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d` starts Prometheus (`:9090`, scrape config `docker/observability/prometheus/prometheus.yml`, rules `alerts.yml`), Grafana (`:3000`, requires `GRAFANA_ADMIN_PASSWORD`, dashboard "DPU Attendance — API, Face queue, Kiosk, Outbox" provisioned from `docker/observability/grafana/`) and an OTel Collector (debug exporter; swap in Tempo/Jaeger in `docker/observability/otel-collector.yml`).
- **Loki log Explore (6E):** add `-f docker-compose.loki.yml` with the observability overlay. Promtail scrapes Docker `json-file` logs for `dpu-*` containers via the host `docker.sock` and pushes to Loki (`:3100`, override with `LOKI_PORT`). Grafana already provisions a **Loki** datasource (`docker/observability/grafana/provisioning/datasources/loki.yml`). In Explore try `{container="dpu-api"} |= "error"` or `{service="worker"}`. Retention default 7d (filesystem volume `loki_data`) — not a SIEM. No extra secrets beyond the existing `GRAFANA_ADMIN_PASSWORD`.
- Tracing: off by default. Set `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g. `http://otel-collector:4318`) to enable FastAPI + SQLAlchemy + httpx spans; `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_PROTOCOL` (`http/protobuf` default, `grpc` needs `opentelemetry-exporter-otlp-proto-grpc`), `OTEL_TRACES_SAMPLER` / `OTEL_TRACES_SAMPLER_ARG` tune it. Unset the endpoint to return to a no-op (the SDK is not even imported). Note: `opentelemetry-instrumentation-sqlalchemy` skips SQLAlchemy ≥ 2.1 with a warning; HTTP spans still work.
- Logs are JSON (`LOG_JSON=true`): `time`, `level`, `logger`, `service` (`api` / `worker`), `message`, `requestId`, `traceId` / `spanId` (OTel ids when tracing is on, else the W3C `traceparent` echoed in the response), `companyId` (bound by `AuthzMiddleware`), `job` (worker). `extra={...}` fields are emitted under `extra` with `password|secret|token|authorization|apiKey|embedding|cookie|signature` keys redacted. Correlate a user report with `X-Request-Id` from the response headers. With Loki up, the same `requestId` / `service` fields are promoted as labels where Promtail can parse them.
- Alerts to configure (rules shipped in `docker/observability/prometheus/alerts.yml`, wire Alertmanager to your on-call tool):
  | Alert | Expression (summary) | Why |
  |---|---|---|
  | `DpuReadyFailing` / `DpuApiDown` | `dpu_ready_status == 0` for 2m, `up{job="dpu-api"} == 0` | DB, GPU queue or Face Core down → kiosks stop |
  | `DpuHigh5xxRate` | 5xx / total > 5 % for 5m | regression or dependency outage |
  | `DpuFaceQueueSaturated` / `DpuFaceQueueWaitHigh` | pending / capacity > 80 % for 3m; check-in queue wait p95 > 1 s | add GPU worker / second API (`docker-compose.gpu.yml`) |
  | `DpuOutboxLag` / `DpuOutboxBacklog` / `DpuOutboxDeliveryFailures` | oldest pending > 5 min; pending > 500; failed deliveries in 30m | worker down or SMTP / LINE / webhook endpoint failing |
  | `DpuWorkerDown` / `DpuImportJobsStuck` / `DpuJobNotSucceeding` | `up{job="dpu-worker"} == 0`; imports pending without a worker; a job has not succeeded for 2 h | background jobs stalled |
  | `DpuDbPoolExhausted` | pool + overflow fully checked out | raise `DB_POOL_SIZE` / find leaking sessions |

## Database migrations (Alembic is the single schema source)
Since Phase B1 the API **never** creates or alters tables itself (`create_all` and `utils/schema_migrate.py` are gone). The schema comes only from `API-Fast/alembic/versions/` (`0001_baseline` = full schema, `0002`–`0008` idempotent history, `0009_import_job_worker` = import_job worker hand-off columns (B7), `0010_schema_drift` = NOT NULL / index / FK drift of legacy databases, `0011_attendance_daily_shift_rules` = C1 `attendance_daily` + C2 WorkShift rounding/break/OT columns; also widens `alembic_version.version_num` to VARCHAR(64)). `alembic/env.py` uses the ORM metadata (`src/config/schema.py`) as `target_metadata`, so `alembic check` and `alembic revision --autogenerate` work. All commands run from `API-Fast/` with `DATABASE_URL` exported (asyncpg URLs are rewritten to psycopg); in Docker: `docker compose exec api alembic <cmd>` or `docker compose run --rm api alembic <cmd>` before the stack is up.

| Situation | Commands |
|-----------|----------|
| Fresh database | `alembic upgrade head` then start `api` |
| Upgrade after a deploy | `alembic upgrade head` (expand/contract: run **before** restarting replicas) |
| Database created by the old startup path (pre-B1, no `alembic_version` table) | `alembic stamp 0008_revocation_kiosk_pairing && alembic upgrade head` — the stamp records what `create_all` + `schema_migrate` already applied; `0009` adds the import_job worker columns and `0010` tightens the nullable columns, adds the `face_encoding` HNSW index / `company_employee` unique indexes / `approved_by` FK when missing |
| Database stamped at `0001_baseline` or `0002_schema_migrate` earlier | `alembic upgrade head` (all later revisions are idempotent) |
| Verify | `alembic current` shows `0017_face_assurance (head)` after Phase D (through placeholder 0014–0016 + face assurance); `alembic check` prints `No new upgrade operations detected.` |
| Roll back the last revision | `alembic downgrade -1` (only `0007`, `0009`, `0010` and `0011` have real `downgrade()`; `0002`–`0006`/`0008` are history markers and cannot be reverted automatically) |
| New schema change | edit the model → `alembic revision --autogenerate -m "..."` → review the file (revision ids ≤ 32 chars) → `alembic upgrade head` → `alembic check` — the test suite (`tests/test_alembic_schema.py`) fails on any model/DB drift |

Readiness gate: at startup the API compares `alembic_version` with the code's head revision. While they differ, `GET /ready` returns `503 {"code": "schema_out_of_date", "schema": {"status": "behind"|"unmanaged", ...}}` and the log shows the exact remediation command; the probe recovers on its own once `alembic upgrade head` finished (no restart). `REQUIRE_SCHEMA_HEAD=false` downgrades this to a log warning. `MIGRATE_ON_STARTUP=true` makes the `api` process run `alembic upgrade head` itself before serving — acceptable for a single-node Docker Compose install, **not** for the dual-GPU overlay or any multi-replica deployment (two processes would race), and it cannot stamp a legacy database for you.

Never run `alembic stamp` on a database you are not sure about: stamping records that a revision was applied without applying it. When in doubt take a backup (`scripts/backup.sh`), restore it to a scratch database and try the upgrade there first.

## Playwright smoke (6E)
Against a running gateway (default `HTTP_PORT=8880`):

```bash
cd Web-Manage
npx playwright install chromium
DPU_BASE_URL=http://localhost:8880 npm run test:e2e:smoke
```

Checks `GET /health` and that `/auth/login` shows the username/password form. For a real sign-in, set `DPU_E2E_USER` and `DPU_E2E_PASSWORD` in the shell only — never commit them or put them in compose/docs. Not wired as a CI gate (needs the stack); npm script only until promoted.

## CI gates and lint baselines (Phase B3)
`.github/workflows/ci.yml` (GitHub) and `.gitlab-ci.yml` (GitLab mirror, same commands) run on every push to `main`, `integration/**`, `phase-*/**` and on pull requests. Every job is blocking — there is no `|| true`, `continue-on-error` or `allow_failure`.

| Job | What it runs | Fails when |
|-----|--------------|------------|
| `backend` | `ruff check .`, `mypy`, `alembic upgrade head && alembic check && alembic downgrade -1 && alembic upgrade head`, `pytest` against a `pgvector/pgvector:pg16` service (`TEST_DATABASE_URL`) | lint/type error, model↔migration drift, a migration without a working `downgrade()`, any failing or skipped-by-error test |
| `frontend` | `npm ci`, `npm run lint`, `npm run test:ci` (Karma + ChromeHeadless, coverage artifact), `npm run build:prod` | eslint error, failing spec, production build error |
| `security` | `trivy fs --config trivy.yaml --scanners vuln,secret,misconfig .` | HIGH/CRITICAL vulnerability with a fix available, leaked secret, Dockerfile misconfiguration not allow-listed |
| `images` | `docker build` of `API-Fast/Dockerfile.cpu`, `Web-Manage/Dockerfile`, `docker/nginx/Dockerfile` + `trivy image` on each; `docker compose ... config -q` for the base/cpu/gpu/prod overlays | build failure, HIGH/CRITICAL in the image, invalid compose file |

The face stack (`insightface`, `onnxruntime*`, `onnx`) and `pgserver` are filtered out of the CI `pip install` — tests stub them (`tests/conftest.py`) and use the Postgres service instead of the embedded server. Reproduce locally with `cd API-Fast && ruff check . && mypy && python -m pytest -q` (embedded Postgres via `pgserver`) and `cd Web-Manage && npm run lint && npm run test:ci && npm run build:prod`.

**Baselines — pre-existing debt silenced explicitly, never by disabling a gate.** Each baseline lists what is ignored and where; new code must be clean, and shrinking a baseline is always welcome (tracked in `docs/BACKLOG.md`).

| Tool | Where | What is baselined | How to shrink |
|------|-------|-------------------|---------------|
| ruff | `API-Fast/pyproject.toml` `[tool.ruff.lint]` | `B008` (FastAPI `Depends()` defaults — intentional), `B904` (40 `raise` without `from`), `B017` (3 blind `pytest.raises`), `E402` per-file for modules that must set up `sys.path`/stubs before importing, `F401` per-file for re-export modules | delete the rule / path from `ignore` or `per-file-ignores`, run `ruff check .`, fix what appears |
| mypy | `API-Fast/pyproject.toml` `[[tool.mypy.overrides]]` | 31 modules with `ignore_errors = true` (160 errors at baseline time); `check_untyped_defs = false` | remove a module from the list when `mypy src/<module>.py` passes; new modules are **not** in the list and are checked fully |
| eslint | `Web-Manage/.eslintrc.json` (rules set to `"off"` at the end of the `*.ts` block, template `eqeqeq`) | `no-explicit-any`, `no-non-null-asserted-optional-chain`, `no-unused-vars`, `use-lifecycle-interface`, `ban-types`, `no-empty-lifecycle-method`, `no-unsafe-declaration-merging` | flip one rule to `"warn"`, fix, then `"error"` |
| trivy | `.trivyignore.yaml` (+ `trivy.yaml` for severity/skip paths) | Angular 17 EOL CVEs and `swiper` SCSS CVE (`expired_at` 2027-03-31), `CVE-2025-47273` scoped to `pkg:pypi/setuptools@70.3.0` (pip's vendored `pkg_resources` SBOM entry in the API images), `DS-0002` non-root `USER` only for `scripts/kiosk-load/Dockerfile` (loadtest-profile tool writing to bind mounts; every product image is non-root since B4) | every entry needs a `statement` and an `expired_at`; CI fails automatically when the date passes, so upgrade or renew consciously |

To add an allow-list entry: `trivy fs --config trivy.yaml .` prints the finding id; append it to `.trivyignore.yaml` with a one-line justification and a date no more than ~6 months out. Never add `--exit-code 0`, `--severity CRITICAL` only, or `ignore-unfixed` changes to make a run pass.
