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

## Database migrations (Alembic is the single schema source)
Since Phase B1 the API **never** creates or alters tables itself (`create_all` and `utils/schema_migrate.py` are gone). The schema comes only from `API-Fast/alembic/versions/` (`0001_baseline` = full schema, `0002`–`0008` idempotent history, `0009_import_job_worker` = import_job worker hand-off columns (B7), `0010_schema_drift` = NOT NULL / index / FK drift of legacy databases). `alembic/env.py` uses the ORM metadata (`src/config/schema.py`) as `target_metadata`, so `alembic check` and `alembic revision --autogenerate` work. All commands run from `API-Fast/` with `DATABASE_URL` exported (asyncpg URLs are rewritten to psycopg); in Docker: `docker compose exec api alembic <cmd>` or `docker compose run --rm api alembic <cmd>` before the stack is up.

| Situation | Commands |
|-----------|----------|
| Fresh database | `alembic upgrade head` then start `api` |
| Upgrade after a deploy | `alembic upgrade head` (expand/contract: run **before** restarting replicas) |
| Database created by the old startup path (pre-B1, no `alembic_version` table) | `alembic stamp 0008_revocation_kiosk_pairing && alembic upgrade head` — the stamp records what `create_all` + `schema_migrate` already applied; `0009` adds the import_job worker columns and `0010` tightens the nullable columns, adds the `face_encoding` HNSW index / `company_employee` unique indexes / `approved_by` FK when missing |
| Database stamped at `0001_baseline` or `0002_schema_migrate` earlier | `alembic upgrade head` (all later revisions are idempotent) |
| Verify | `alembic current` shows `0010_schema_drift (head)`; `alembic check` prints `No new upgrade operations detected.` |
| Roll back the last revision | `alembic downgrade -1` (only `0007`, `0009` and `0010` have real `downgrade()`; `0002`–`0006`/`0008` are history markers and cannot be reverted automatically) |
| New schema change | edit the model → `alembic revision --autogenerate -m "..."` → review the file (revision ids ≤ 32 chars) → `alembic upgrade head` → `alembic check` — the test suite (`tests/test_alembic_schema.py`) fails on any model/DB drift |

Readiness gate: at startup the API compares `alembic_version` with the code's head revision. While they differ, `GET /ready` returns `503 {"code": "schema_out_of_date", "schema": {"status": "behind"|"unmanaged", ...}}` and the log shows the exact remediation command; the probe recovers on its own once `alembic upgrade head` finished (no restart). `REQUIRE_SCHEMA_HEAD=false` downgrades this to a log warning. `MIGRATE_ON_STARTUP=true` makes the `api` process run `alembic upgrade head` itself before serving — acceptable for a single-node Docker Compose install, **not** for the dual-GPU overlay or any multi-replica deployment (two processes would race), and it cannot stamp a legacy database for you.

Never run `alembic stamp` on a database you are not sure about: stamping records that a revision was applied without applying it. When in doubt take a backup (`scripts/backup.sh`), restore it to a scratch database and try the upgrade there first.

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
| trivy | `.trivyignore.yaml` (+ `trivy.yaml` for severity/skip paths) | Angular 17 EOL CVEs and `swiper` SCSS CVE (`expired_at` 2027-03-31), `CVE-2025-47273` scoped to `pkg:pypi/setuptools@70.3.0` (pip's vendored `pkg_resources` SBOM entry in the API images), `DS-0002` non-root `USER` (`expired_at` 2027-01-31, fixed by B4) | every entry needs a `statement` and an `expired_at`; CI fails automatically when the date passes, so upgrade or renew consciously |

To add an allow-list entry: `trivy fs --config trivy.yaml .` prints the finding id; append it to `.trivyignore.yaml` with a one-line justification and a date no more than ~6 months out. Never add `--exit-code 0`, `--severity CRITICAL` only, or `ignore-unfixed` changes to make a run pass.
