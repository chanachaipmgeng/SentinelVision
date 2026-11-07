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
- Since B7 the dispatcher runs in the `worker` service, not in `dpu-api`. A row that fails `OUTBOX_MAX_ATTEMPTS` (5) deliveries is marked `failed` (`dpu_outbox_deliveries_total{result="failed"}`); fix the channel (SMTP / LINE / webhook) then reset it with `UPDATE notification_outbox SET status='pending', attempts=0 WHERE id=...`.

## Background worker (B7)
- `worker` (same image as `api`, `python -m src.worker`, no GPU) runs three jobs: `outbox` (notification dispatcher + daily attendance cutoff, every `NOTIFY_POLL_SECONDS`), `retention` (temp / uploaded image purge, expired Sentinel identities, finished import payloads older than `IMPORT_JOB_RETENTION_DAYS`, orphaned import jobs; every `WORKER_RETENTION_INTERVAL_SECONDS`) and `imports` (Excel + ZIP employee import, polled every `WORKER_IMPORT_POLL_SECONDS`). Select with `WORKER_JOBS=outbox,retention,imports`; scale with `docker compose up -d --scale worker=2` — every job claims rows with `FOR UPDATE SKIP LOCKED`.
- The API only accepts the upload: `POST /employees/company/{id}/import-jobs` stores the files under `IMPORT_JOB_DIR` (`/app/import_jobs`, volume `api_import_jobs` shared by `api`, `api-gpu1` and `worker`) and inserts an `import_job` row (`pending`). The worker claims it (`running`, `lockedBy`, `attempts`), updates `progress` (`processed/total/success/failed/facesEnrolled`) and finishes with `done` / `failed`; Web-Manage polls `GET .../import-jobs/{jobId}`. A `running` job whose `heartbeatAt` is older than `WORKER_IMPORT_LEASE_SECONDS` (900) is failed by the retention job (`importJobsOrphaned`) so the UI never spins forever; re-upload the file.
- Single-container dev: `RUN_BACKGROUND_JOBS_IN_API=true` runs the same job loops inside `dpu-api` (startup logs a warning). Default is `false`; a stack without a `worker` then accumulates `pending` outbox rows and import jobs (alert `DpuImportJobsStuck`, `DpuOutboxLag`).
- Cron / one-shot mode: `docker compose run --rm worker python -m src.worker --once [--jobs outbox,retention] [--worker-id cron-1]` runs each job once and exits 0 only when every job succeeded (`1` otherwise). Metrics port is disabled in `--once` mode; the long-running worker serves `:9108/metrics` (`WORKER_METRICS_PORT`) and this is also its healthcheck.
- Graceful shutdown: SIGTERM / SIGINT stop new iterations and wait up to `WORKER_SHUTDOWN_GRACE_SECONDS` (30; compose `stop_grace_period: 45s`) for the running import row to finish before cancelling. Import progress is persisted per row, so a cancelled job is re-claimed by the next worker (`attempts` + 1) after the lease expires.
- Health: `dpu_job_runs_total{job_name,result}`, `dpu_job_duration_seconds`, `dpu_job_last_success_timestamp_seconds`, `dpu_import_jobs_pending` / `_running`, `dpu_import_job_duration_seconds`, `dpu_import_rows_total{result}`; `docker compose logs -f worker` prints JSON lines with `"service": "worker"` and `"job"`.

## Observability & alerts
- `GET /metrics` (api) and `http://worker:9108/metrics` (worker) expose Prometheus text via `prometheus_client`. Key series: `dpu_http_requests_total{method,route,status}`, `dpu_http_request_duration_seconds`, `dpu_face_gpu_queue_pending{kind}` / `_capacity` / `_wait_seconds` / `dpu_face_gpu_processing_seconds`, `dpu_face_match_duration_seconds{source}`, `dpu_ws_kiosk_connections`, `dpu_outbox_pending` / `dpu_outbox_oldest_pending_age_seconds` / `dpu_outbox_deliveries_total{channel,result}`, `dpu_import_jobs_*`, `dpu_job_runs_total{job_name,result}` / `dpu_job_last_success_timestamp_seconds`, `dpu_db_pool_*`, `dpu_ready_status{component}`. `/metrics` is unauthenticated inside the stack; restrict it at nginx (hardening B4) before exposing the gateway publicly.
- Dashboards as code: `docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d` starts Prometheus (`:9090`, scrape config `docker/observability/prometheus/prometheus.yml`, rules `alerts.yml`), Grafana (`:3000`, requires `GRAFANA_ADMIN_PASSWORD`, dashboard "DPU Attendance — API, Face queue, Kiosk, Outbox" provisioned from `docker/observability/grafana/`) and an OTel Collector (debug exporter; swap in Tempo/Jaeger in `docker/observability/otel-collector.yml`).
- Tracing: off by default. Set `OTEL_EXPORTER_OTLP_ENDPOINT` (e.g. `http://otel-collector:4318`) to enable FastAPI + SQLAlchemy + httpx spans; `OTEL_SERVICE_NAME`, `OTEL_EXPORTER_OTLP_PROTOCOL` (`http/protobuf` default, `grpc` needs `opentelemetry-exporter-otlp-proto-grpc`), `OTEL_TRACES_SAMPLER` / `OTEL_TRACES_SAMPLER_ARG` tune it. Unset the endpoint to return to a no-op (the SDK is not even imported). Note: `opentelemetry-instrumentation-sqlalchemy` skips SQLAlchemy ≥ 2.1 with a warning; HTTP spans still work.
- Logs are JSON (`LOG_JSON=true`): `time`, `level`, `logger`, `service` (`api` / `worker`), `message`, `requestId`, `traceId` / `spanId` (OTel ids when tracing is on, else the W3C `traceparent` echoed in the response), `companyId` (bound by `AuthzMiddleware`), `job` (worker). `extra={...}` fields are emitted under `extra` with `password|secret|token|authorization|apiKey|embedding|cookie|signature` keys redacted. Correlate a user report with `X-Request-Id` from the response headers.
- Alerts to configure (rules shipped in `docker/observability/prometheus/alerts.yml`, wire Alertmanager to your on-call tool):
  | Alert | Expression (summary) | Why |
  |---|---|---|
  | `DpuReadyFailing` / `DpuApiDown` | `dpu_ready_status == 0` for 2m, `up{job="dpu-api"} == 0` | DB, GPU queue or Face Core down → kiosks stop |
  | `DpuHigh5xxRate` | 5xx / total > 5 % for 5m | regression or dependency outage |
  | `DpuFaceQueueSaturated` / `DpuFaceQueueWaitHigh` | pending / capacity > 80 % for 3m; check-in queue wait p95 > 1 s | add GPU worker / second API (`docker-compose.gpu.yml`) |
  | `DpuOutboxLag` / `DpuOutboxBacklog` / `DpuOutboxDeliveryFailures` | oldest pending > 5 min; pending > 500; failed deliveries in 30m | worker down or SMTP / LINE / webhook endpoint failing |
  | `DpuWorkerDown` / `DpuImportJobsStuck` / `DpuJobNotSucceeding` | `up{job="dpu-worker"} == 0`; imports pending without a worker; a job has not succeeded for 2 h | background jobs stalled |
  | `DpuDbPoolExhausted` | pool + overflow fully checked out | raise `DB_POOL_SIZE` / find leaking sessions |

## Alembic Migrations
Existing databases apply idempotent DDL via `src/utils/schema_migrate.py` at startup. After pulling the latest revisions, run `alembic stamp 0009_import_job_worker` inside `dpu-api` (needs `DATABASE_URL`). Fresh databases can run `alembic upgrade head` after `create_all`. Revision `0007_face_encoding_company_id` adds `face_encoding."companyId"` (backfilled), revision `0008_revocation_kiosk_pairing` adds `revoked_token` and the kiosk pairing columns on `kiosk_device` (`token_hash` becomes nullable) and revision `0009_import_job_worker` adds the worker hand-off columns on `import_job` (`requestedBy`, `fileName`, `photosFileName`, `payloadDir`, `progress`, `attempts`, `lockedBy`, `startedAt`, `heartbeatAt`) plus `import_job_status_created_idx`.
