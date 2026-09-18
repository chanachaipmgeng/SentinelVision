# Architecture

## Overview

DPU Attendance is a face-recognition check-in system for companies:

1. Admin enrolls employee faces and manages orgs/locations in Web-Manage
2. Employees check in at the **admin face kiosk** (`/company/timestamp-face`)
3. API matches InsightFace embeddings in Postgres (pgvector), applies dedupe/geofence, and writes timestamps

## Runtime topology (Docker)

### Standalone (legacy local InsightFace)

```
Browser
  │
  ▼
nginx :80
  ├─ /              → admin (Web-Manage static)
  └─ /auth,/face,…  → api (FastAPI :8000)
                        │
                        ▼
                   Postgres + pgvector :5432
```

Start with `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`.

### Face Core BFF (recommended for production GPU)

When `FACE_CORE_ENABLED=true`, DPU keeps `/face/*` URLs and Web-Manage unchanged; vision + gallery run in sibling repo **face-core**; check-in, GPS, dedupe, and HR stay in DPU.

```
Browser → nginx → dpu-api (BFF)
                    ├─ check-in / timestamps / geofence (DPU DB)
                    └─ httpx → face-core-api :8000 (identify, enroll, verify, detect)
```

**Mapping:** `companyId` → `companyCode=str(companyId)`, `memberId` → `subjectId`, `faceEncodingId` ↔ `faceId`.

**Linked startup:**

```bash
docker network create face-net

# Terminal 1 — Face Core
cd ../face-core
docker compose -f docker-compose.yml -f docker-compose.gpu.yml -f docker-compose.face-net.yml up -d

# Terminal 2 — DPU (CPU api, no local GPU queue)
cd dpu-project
docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.face-core.yml up -d --build api
```

Env on `dpu-api`: `FACE_CORE_ENABLED`, `FACE_CORE_URL`, `FACE_CORE_API_KEY`. Set `FACE_CORE_ENABLED=false` to fall back to local InsightFace + pgvector.

**Migration:** after BFF is live, run `API-Fast/scripts/migrate_faces_to_face_core.py` (does not delete local `face_encoding` rows).


## Components

| Component | Path | Role |
|-----------|------|------|
| Gateway | `docker/nginx/` | Reverse proxy (`client_max_body_size 500m`; import timeout 1h). Host TLS nginx must match or uploads return 413 — see `host-upload-limit.conf`. |
| API | `API-Fast/` | Auth, CRUD, face, timestamps, dashboard, system TTS settings |
| Admin UI | `Web-Manage/` | Angular 17 company/admin console + face kiosk |
| Database | `pgvector/pgvector:pg16` | Relational data + `vector(512)` embeddings |

## Face pipeline

When **`FACE_CORE_ENABLED=false`** (default):

1. **Enroll** `POST /face/members/{id}/add-face` → InsightFace `buffalo_l` → store `embedding vector(512)` + image under `enrolled_images/`
2. **Admin kiosk** — local GPU queue + pgvector NN
3. **Identify / tools** — multi-frame liveness + pgvector

When **`FACE_CORE_ENABLED=true`** (BFF):

1. **Enroll / identify / verify / gallery** → proxied to Face Core (`src/clients/face_core_client.py`)
2. **Check-in** → Face Core identify (walkby/secure) then DPU `_finalize_check_in` (GPS, dedupe, timestamp)
3. **WS kiosk** (`/face/ws/kiosk`) → same BFF split; session `companyId` maps to Face Core `companyCode`
4. Local InsightFace GPU queue is **not** started (`main.py`)

**Admin kiosk** (`/company/timestamp-face`): multi-person track, WS identify + walk-by check-in, dedupe (`CHECK_IN_DEDUPE_SECONDS`), geofenced timestamp, optional browser TTS from `/system/tts-settings`.

Legacy stacks removed from the repo: Express `API/`, abandoned `Web-Frontend/`, `Webview-Mobile/`, FAISS / OpenCV pickle artifacts.

## Admin UI (Web-Manage)

- Brand tokens + shell: `Web-Manage/src/assets/css/dpu-theme.css`
- Shared list kit: `Web-Manage/src/app/shared/components/` (`page-toolbar`, `pill-search`, `stat-chip`, `simple-pager`, `empty-state`, `location-map`, `checkin-map`)
- List helpers: `Web-Manage/src/app/shared/styles/dpu-list-page.css`
- Shell layout: `shared/layouts/content-layout/` + header/sidebar
- Menus: `shared/services/nav.service.ts` (`getCommonMenu` / `getCompanyMenu`)
- Dashboard (`/company/dashboard`): charts + Leaflet check-in map + polled realtime feed via `GET /dashboard/stats/{companyId}` (`mapPoints`, `recentActivity`)
- Global TTS: `/admin/system-setting` → `system_setting` table (`key=tts`)

## Key source paths

- API entry: `API-Fast/src/main.py`
- Face engine / GPU queue: `API-Fast/src/utils/face_engine.py`, `face_gpu_queue.py`
- Face HTTP / WS: `API-Fast/src/controllers/face_controller.py`, `face_ws_controller.py`
- Face Core client (BFF): `API-Fast/src/clients/face_core_client.py`
- Embeddings model: `API-Fast/src/models/face_encoding.py`
- Timestamp + geo: `API-Fast/src/controllers/employee_timestamp_controller.py`
- System TTS: `API-Fast/src/controllers/system_controller.py`, `models/system_setting.py`
- Admin kiosk: `Web-Manage/src/app/DPU/company-management/enroll-face/`
- Agent rules/skills: [CURSOR-AGENT.md](CURSOR-AGENT.md)

## Enterprise controls

- JWT secrets and token TTL live in `API-Fast/src/config/settings.py`. Startup fails if `SECRET_KEY` is still the placeholder (`AUTH_FAIL_FAST`).
- `AuthzMiddleware` requires a token and binds `companyId` in the URL to the caller.
- Audit rows are written on successful writes. The company UI is `/company/audit-log`.
- Notifications use `notification_outbox` plus SMTP / LINE. Per-company settings are `system_setting` key `notify:{companyId}`.
- GPU workers bind to `FACE_DEVICES`. Match queries set `hnsw.ef_search` and join `company_employee`.
- Ops: [RUNBOOK.md](RUNBOOK.md), `scripts/backup.sh`, `docker-compose.prod.yml` (no published Postgres port).

