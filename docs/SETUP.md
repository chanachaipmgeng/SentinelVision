# Setup

สำหรับติดตั้งบนเซิร์ฟเวอร์จริง (clone จาก GitLab + seed mock) ดูคู่มือเต็มที่ [DEPLOY-SERVER.md](DEPLOY-SERVER.md)

**คู่มือความจุคีออส (สรุปผลเทสทุกวิธี + สเป็คที่ควรใช้):** [KIOSK-CAPACITY-GUIDE.md](KIOSK-CAPACITY-GUIDE.md)

**คู่มือ HTML (dev stack + integration test):** [BFF-DEV-GUIDE.html](BFF-DEV-GUIDE.html)

## Requirements

- Docker Desktop (Compose v2)
- Optional for local Angular only: Node 18+ / 20+

## First run

```bash
cp .env.example .env
# set SECRET_KEY to a random string of at least 32 characters, e.g.
#   python -c "import secrets; print(secrets.token_urlsafe(48))"
# set POSTGRES_PASSWORD (compose has no default any more) — .env.example ships dpu_secret
# together with APP_ENV=development so a laptop still starts; servers use a real password
# and APP_ENV=production (the default when the variable is absent).
docker compose up --build
```

The API refuses to start while `SECRET_KEY` is the placeholder (`AUTH_FAIL_FAST=true`), and in
production mode (`APP_ENV` unset or `production`) also when the database password is one of the
example values (`dpu_secret`, `postgres`, …). `docker compose` itself aborts when
`POSTGRES_PASSWORD` or `SECRET_KEY` is missing from `.env`.

| URL | Service |
|-----|---------|
| http://localhost:8880/ | Admin (when `HTTP_PORT=8880` in `.env`) |
| http://localhost:8880/company/timestamp-face | Face kiosk |
| http://localhost:8880/health, /ready | liveness / readiness |
| http://localhost:8880/docs | OpenAPI — 404 unless `EXPOSE_API_DOCS=true` (read by the API **and** nginx); even then only from `INTERNAL_ALLOW_CIDRS` |
| http://localhost:8880/metrics | Prometheus text — only from `INTERNAL_ALLOW_CIDRS` (default loopback + RFC1918) |
| 127.0.0.1:5434 | PostgreSQL (BFF dev alongside face-core) — bound to loopback only; `docker-compose.prod.yml` publishes nothing |

Default DB credentials are in `.env.example` (`dpu` / `dpu_secret`). Change them before any shared deployment — production mode refuses `dpu_secret`.

**Standalone** (no Face Core on same host): use `POSTGRES_PORT=5432` and `HTTP_PORT=80` in `.env`.

### Shared local Postgres (`dev-postgres`)

Local DPU can use the sibling shared instance (schema `dpu` in DB `localdev`) instead of builtin `dpu-db`:

```bash
docker network create dev-net   # once
cd ../dev-postgres && docker compose up -d
# first-time data move: .\scripts\migrate-from-dpu.ps1  (needs old dpu-db running)
cd ../dpu-project
docker compose -f docker-compose.yml -f docker-compose.gpu.yml \
  -f docker-compose.external-db.yml up -d --build
```

Host URL: `postgresql+asyncpg://localdev:localdev_secret@localhost:54320/localdev` with `DB_SCHEMA=dpu`.

## Environment

| Variable | Default | Meaning |
|----------|---------|---------|
| `HTTP_PORT` | `8880` (BFF dev) / `80` standalone | nginx host port |
| `POSTGRES_PORT` | `5434` (BFF dev) / `5432` standalone | database host port |
| `FACE_RECOGNITION_THRESHOLD` | `0.40` | cosine **distance** cutoff (lower = stricter; local mode) |
| `IMAGE_BLUR_THRESHOLD` | `20.0` | reject blurry kiosk / add-face enroll |
| `IMAGE_BLUR_THRESHOLD_IMPORT` | `0` | Excel+ZIP import blur gate; `0` = do not reject blurry photos (face still required) |
| `POSTGRES_PASSWORD` | **required** | compose aborts without it; example values are refused in production mode |
| `APP_ENV` | `production` | `development` downgrades the weak-DB-password check to a warning (laptops only) |
| `SECRET_KEY` | (placeholder) | **required**, ≥ 32 chars; startup fails otherwise |
| `AUTH_FAIL_FAST` | `true` | set `false` only for throwaway local runs / unit tests (disables every secret check, logged loudly) |
| `INTERNAL_ALLOW_CIDRS` | loopback + RFC1918 | nginx allowlist for `/metrics` and `/docs`; narrow it to the Prometheus scraper in production |
| `HTTPS_PORT` / `TLS_CERT_DIR` | `443` / `./certs` | used by `docker-compose.tls.yml` |
| `HSTS_MAX_AGE` | auto | `Strict-Transport-Security` max-age; auto = on when the TLS overlay is active |
| `CSP_SCRIPT_EXTRA` / `CSP_CONNECT_EXTRA` / `CSP_FRAME_EXTRA` | (empty) | extra Content-Security-Policy sources for the admin SPA (IdP origin, extra CDN, `'unsafe-eval'` if a library needs it) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | `60` / `14` | JWT lifetimes |
| `OIDC_ENABLED` | `false` | enterprise SSO (OpenID Connect, Authorization Code + PKCE). When `true`, startup fails unless the variables below are valid |
| `OIDC_ISSUER` | (empty) | IdP issuer URL, must serve `<issuer>/.well-known/openid-configuration` and match the `issuer` inside it (`https://`; plain `http://` only for `localhost`) |
| `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` | (empty) | RP client registered at the IdP. Secret optional for public clients (PKCE is always used) |
| `OIDC_REDIRECT_URI` | (empty) | absolute URL of the SPA callback: `https://<host>/auth/sso/callback` — register the exact value at the IdP |
| `OIDC_SCOPES` | `openid profile email` | space-separated; must include `openid` |
| `OIDC_JWKS_CACHE_SECONDS` / `OIDC_LOGIN_TXN_TTL_SECONDS` / `OIDC_CLOCK_SKEW_SECONDS` / `OIDC_HTTP_TIMEOUT_SECONDS` | `3600` / `600` / `60` / `10` | JWKS + discovery cache TTL, how long a started login stays valid, `exp`/`iat` leeway, IdP HTTP timeout |
| `FACE_ROUTES_REQUIRE_JWT` | `true` | face HTTP + kiosk WS need a token |
| `FACE_DEVICES` | `cuda:0` | comma list; one GPU worker per device |
| `EXPOSE_API_DOCS` | `false` | Swagger/ReDoc — must be `true` on the API *and* nginx (same `.env` value); gateway still restricts to `INTERNAL_ALLOW_CIDRS` |
| `SMTP_*`, `LINE_CHANNEL_ACCESS_TOKEN` | (empty) | notification channels; empty = skipped |
| `IMAGE_RETENTION_DAYS` | `90` | punch-photo retention |
| `FACE_CORE_ENABLED` | `false` | when `true`, `/face/*` BFF proxies vision to Face Core |
| `FACE_CORE_URL` | `http://host.docker.internal:8081` | Face Core base URL |
| `FACE_CORE_API_KEY` | (empty) | Bearer key for Face Core tenant |
| `GOOGLE_MAPS_API_KEY` | (empty) | Web-Manage Google Maps JS key; written to `assets/config.json` by the `admin` container entrypoint. Empty = OSM fallback |
| `GOOGLE_MAPS_MAP_ID` | `DEMO_MAP_ID` | Map ID for AdvancedMarkerElement |

Frontends in Docker use `baseUrl: ''` (same origin through nginx).

## Hardened containers (B4)

- **Non-root everywhere:** `api` / `api-gpu1` run as `app` (uid 10001), `admin` and `nginx` as `nginx` (uid 101, `nginxinc/nginx-unprivileged`, listening on **8080** inside the network), `db` as `postgres` in the prod overlay. `docker exec dpu-api id` must show `uid=10001`.
- **Multi-stage, digest-pinned images:** `API-Fast/Dockerfile` (CUDA), `Dockerfile.cpu`, `Dockerfile.bff`, `Web-Manage/Dockerfile`, `docker/nginx/Dockerfile`. Build stages compile wheels; runtime stages carry only the venv, the warmed `buffalo_l` model (`/home/app/.insightface`, read-only) and the source. Every image has a `HEALTHCHECK`. Runtime images carry no `pip` (immutable venv); for ad-hoc debugging run `docker exec -u 0 dpu-api python -m ensurepip` in a throw-away container, never in production.
- **Upgrading an existing deployment:** named volumes `api_enrolled` / `api_uploaded` / `api_temp` were created by root containers. Chown them once or the API refuses to start with a clear error:

  ```bash
  docker compose ... up -d --build            # pulls new images
  docker run --rm --volumes-from dpu-api alpine chown -R 10001:10001 /app/enrolled_images /app/uploaded_images /app/temp_images
  docker compose ... restart api api-gpu1
  ```

- **Read-only root fs:** `docker-compose.prod.yml` makes `admin` and `nginx` read-only (tmpfs on `/tmp`); `docker-compose.api-readonly.yml` does the same for `api` (verified on CPU; test on your GPU host before adopting because the NVIDIA runtime writes the loader cache at start).
- **Gateway** (`docker/nginx/snippets/gateway.conf`, shared by all four variants — rebuild `nginx` after editing anything under `docker/nginx/`):
  - `limit_req` per client IP: `/auth/login` 20 r/min (burst 10), `/auth/refresh*` + `/auth/kiosk/refresh` 60 r/min (burst 20), `/auth/kiosk/pair` 10 r/min (burst 5), everything else 100 r/s (burst 200). Excess → `429`. Zones live in `docker/nginx/00-dpu-http.conf`.
  - `/metrics`, `/docs`, `/redoc`, `/openapi.json` are internal-only (`INTERNAL_ALLOW_CIDRS`); docs additionally need `EXPOSE_API_DOCS=true`.
  - Security headers on every response: `X-Content-Type-Options`, `X-Frame-Options SAMEORIGIN`, `Referrer-Policy`, `Cross-Origin-Opener-Policy`, `Permissions-Policy` and a CSP. The SPA document CSP uses a per-request nonce (`$request_id`, injected into `index.html` via `sub_filter`; Angular picks it up through `ngCspNonce`, the Google Maps loader through `window.__dpuCspNonce`) with no `'unsafe-inline'` / `'unsafe-eval'` for scripts, and allows Google Maps, Google Fonts, OpenStreetMap tiles/embeds and same-origin WebSockets. API responses get `default-src 'none'`. `Permissions-Policy` grants `camera=(self)` only to SPA documents (the kiosk, `/kiosk/pair` and the face-enrollment dialog share the one Angular document, so it cannot be scoped to a single route) and denies it on API/image responses.
  - `client_max_body_size` is 32m by default and 500m only for `/employees/*/import`.
- **TLS in the stack:** add `-f docker-compose.tls.yml` with `fullchain.pem` / `privkey.pem` in `TLS_CERT_DIR` (readable by uid 101). nginx listens on `HTTPS_PORT` (TLS 1.2/1.3, HSTS) and redirects HTTP → HTTPS except the loopback healthcheck. Renewal = replace files + `docker compose ... exec nginx nginx -s reload`. Keep `docker/nginx/tls-edge.example.conf` when a host nginx terminates TLS instead.
- **Local dev ergonomics:** nothing changes in the commands — `.env.example` carries `APP_ENV=development` and the example DB password; Postgres stays reachable from the host on `127.0.0.1:${POSTGRES_PORT}`; `EXPOSE_API_DOCS=true` in `.env` enables Swagger from the LAN.

## Backups (B5)

Add `-f docker-compose.backup.yml` to run the `backup` sidecar (daily `pg_dump -Fc` + image-volume archive + manifest into `BACKUP_DIR`, weekly restore drill, optional rclone/S3 copy). Set `BACKUP_UID`/`BACKUP_GID` to the owner of `BACKUP_DIR` on the host. From a host with the docker CLI, `scripts/backup.sh` and `scripts/restore-drill.sh` do the same without the sidecar. Procedures, RPO/RTO targets and the real-restore command are in `docs/RUNBOOK.md` → "Backup, restore & drill".

### Web-Manage runtime config (no keys in the bundle)

The SPA reads `assets/config.json` at startup (`src/app/shared/runtime-config.ts`) and injects the Google Maps SDK `<script>` from it. The file is git-ignored; `assets/config.example.json` is the template.

- **Docker:** nothing to do — `Web-Manage/docker/40-runtime-config.sh` writes the file from `GOOGLE_MAPS_API_KEY` / `GOOGLE_MAPS_MAP_ID` on each start.
- **Local `ng serve`:** `cp Web-Manage/src/assets/config.example.json Web-Manage/src/assets/config.json` and fill in your own key. Never commit it.
- `src/environments/environment*.ts` must not contain real keys (Firebase block is an unused placeholder). See `docs/SECRETS-REMEDIATION.md`.

## Enterprise SSO (OIDC, optional)

1. Register a confidential (or public) OIDC client at your IdP (Entra ID, Keycloak, Okta, Google Workspace, …) with redirect URI `https://<host>/auth/sso/callback` and the Authorization Code grant with PKCE (S256). ID tokens must be signed with `RS256` or `ES256`; `HS256` is refused.
2. Set in `.env`: `OIDC_ENABLED=true`, `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` (if confidential), `OIDC_REDIRECT_URI`, optionally `OIDC_SCOPES`. Rebuild `api` (and `api-gpu1`) and `nginx` — `docker/nginx/*.conf` route `GET /auth/sso/callback` to the SPA so the IdP redirect lands on the Angular page.
3. Verify: `curl http://localhost/auth/sso/oidc/status` → `{"enabled": true, ...}`. The Login page now shows **เข้าสู่ระบบด้วย SSO องค์กร**.
4. Mapping is by verified e-mail → `member.email`. Unknown users are rejected unless a company admin enables JIT provisioning for that company via `PUT /auth/sso/policy/{companyId}` (`jitProvisioning=true`, `defaultDepartmentId`, `defaultPositionId`, optional `allowedEmailDomains`). JIT is off by default.
5. Misconfiguration (missing issuer/client/redirect, non-https issuer, scopes without `openid`) aborts startup with `OIDC_ENABLED=true but misconfigured: ...`.

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

**Local DPU → remote Face Core (dev):** Face Core รันบนเซิร์ฟเวอร์ (`10.50.0.117:8081`) ส่วน DPU รันบนเครื่อง local:

```bash
# .env: FACE_CORE_ENABLED=true
#       FACE_CORE_URL=http://10.50.0.117:8081
#       FACE_CORE_API_KEY=<same as server BOOTSTRAP_API_KEY>
docker compose -f docker-compose.yml -f docker-compose.face-core-remote.yml up -d --build
```

Expect Face Core `GET http://127.0.0.1:8081/v1/health` to show `device` `cuda:0` (or `cpu`). DPU `GET /ready` on the nginx port must show the same device and `service: face-core`. `GET /face/queue-stats` with a DPU JWT returns `source: face-core`. Set `FACE_CORE_ENABLED=false` and drop the face-core overlay to fall back to local InsightFace.

**Local BFF verified (24 ก.ย. 2026):** Face Core CPU + DPU `docker-compose.face-core.yml` บน Docker Desktop — `/v1/health` `device=cpu` · `/ready` `service: face-core` · `/face/queue-stats` `source: face-core` · `scripts/smoke_face_core_bff.py` ผ่าน (enroll / identify / check-in-walkby / verify). Smoke ต้อง login JWT (`admin` / seed password) เพราะ `FACE_ROUTES_REQUIRE_JWT=true`:

```bash
docker compose -f docker-compose.yml -f docker-compose.face-core.yml \
  run --rm -v ./API-Fast:/app --entrypoint python api scripts/smoke_face_core_bff.py
```

**Server `10.50.0.117` (24 ก.ย. 2026):**

| รอบ | ผล |
|-----|-----|
| §6.6 co-locate DPU BFF | smoke ผ่าน · identify ×1@16 `face_core_down` ถล่ม → **rollback** attendance เป็น **quad w3 monolith** |
| §6.7 A+1 (local BFF → FC `:8081`) | จูน Face Core: workers=3/GPU · queue/pending=128 · rate=6000 · **hard-pin GPU0/GPU1** · session นิ่งถึง ×1@32 แต่ SLO p95≤550 ผ่านแค่ ~gated ×1@2 — รายละเอียด [FACE-CORE-IDENTIFY-CAPACITY.md](FACE-CORE-IDENTIFY-CAPACITY.md) §6.6–§6.7 |
| §6.8 co-locate BFF + Whisper off | ยืนยันเพดาน Face Core จริงบนเซิร์ฟเวอร์ ≈ **≤2 จอ gated** · W2≈W3 · **ไม่เพิ่ม workers/process** · คืน quad แล้ว — §6.8 |

Attendance production บนเซิร์ฟเวอร์ยัง monolith · Face Core เปิด `:8081` สำหรับ dev remote BFF ได้ (อย่า cutover DPU BFF ทั้งเครื่องจนกว่า latency จะใกล้ monolith)

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

Then `ng serve` with `environment.ts` → `http://localhost:8000`. For Google Maps locally, create `src/assets/config.json` from `config.example.json` (git-ignored).

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
