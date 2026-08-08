# Architecture

## Overview

DPU Attendance is a face-recognition check-in system for companies:

1. Admin enrolls employee faces and manages orgs/locations in Web-Manage
2. Employees check in at the **admin face kiosk** (`/company/timestamp-face`)
3. API matches InsightFace embeddings in Postgres (pgvector), applies dedupe/geofence, and writes timestamps

## Runtime topology (Docker)

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

## Components

| Component | Path | Role |
|-----------|------|------|
| Gateway | `docker/nginx/` | Reverse proxy |
| API | `API-Fast/` | Auth, CRUD, face, timestamps, dashboard, system TTS settings |
| Admin UI | `Web-Manage/` | Angular 17 company/admin console + face kiosk |
| Database | `pgvector/pgvector:pg16` | Relational data + `vector(512)` embeddings |

## Face pipeline

1. **Enroll** `POST /face/members/{id}/add-face` → InsightFace `buffalo_l` → store `embedding vector(512)` + image under `enrolled_images/`
2. **Admin kiosk** (`/company/timestamp-face`):
   - Multi-person track + face crops
   - Prefer `WS /face/ws/kiosk` (identify + walk-by check-in via GPU queue)
   - Fallback `POST /face/members/check-in-walkby` (or secure `/check-in`)
   - Server dedupe (`CHECK_IN_DEDUPE_SECONDS`) + geofenced timestamp
   - UI: fullscreen chrome via `html.dpu-kiosk-mode` (hides admin header/sidebar)
   - Optional speech via browser TTS; templates from `GET/PUT /system/tts-settings` (admin page `/admin/system-setting`)
3. **Identify / tools** `POST /face/members/check-face-emp` → multi-frame liveness → pgvector NN → member payload

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
- Embeddings model: `API-Fast/src/models/face_encoding.py`
- Timestamp + geo: `API-Fast/src/controllers/employee_timestamp_controller.py`
- System TTS: `API-Fast/src/controllers/system_controller.py`, `models/system_setting.py`
- Admin kiosk: `Web-Manage/src/app/DPU/company-management/enroll-face/`
- Agent rules/skills: [CURSOR-AGENT.md](CURSOR-AGENT.md)
