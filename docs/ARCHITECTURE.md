# Architecture

## Overview

DPU Attendance is a face-recognition check-in system for companies:

1. Admin enrolls employee faces and manages orgs/locations
2. Employee checks in from mobile by capturing multiple camera frames
3. API verifies liveness, matches InsightFace embeddings in Postgres (pgvector), then mobile creates a geo-validated timestamp

## Runtime topology (Docker)

```
Browser
  │
  ▼
nginx :80
  ├─ /              → admin (Web-Manage static)
  ├─ /mobile/       → mobile (Webview-Mobile static)
  └─ /auth,/face,…  → api (FastAPI :8000)
                        │
                        ▼
                   Postgres + pgvector :5432
```

Start everything with `docker compose up --build`.

## Components

| Component | Path | Role |
|-----------|------|------|
| Gateway | `docker/nginx/` | Reverse proxy |
| API | `API-Fast/` | Auth, CRUD, face, timestamps, dashboard |
| Admin UI | `Web-Manage/` | Angular 17 company/admin console |
| Mobile UI | `Webview-Mobile/` | Angular 15 employee check-in |
| Database | `pgvector/pgvector:pg16` | Relational data + `vector(512)` embeddings |

## Face pipeline

1. **Enroll** `POST /face/members/{id}/add-face` → InsightFace `buffalo_l` → store `embedding vector(512)` + image under `enrolled_images/`
2. **Check-in** `POST /face/members/check-face-emp` (N frames) → multi-frame liveness → cosine nearest-neighbor in pgvector → `{ memberId }`
3. Mobile then uploads a photo and `POST /timestamp/company/{id}` with GPS; server overwrites in/out-of-area status via Haversine

Legacy stacks removed from the repo: Express `API/`, abandoned `Web-Frontend/`, FAISS / OpenCV pickle artifacts.

## Key source paths

- API entry: `API-Fast/src/main.py`
- Face engine: `API-Fast/src/utils/face_engine.py`
- Embeddings model: `API-Fast/src/models/face_encoding.py`
- Timestamp + geo: `API-Fast/src/controllers/employee_timestamp_controller.py`
- Admin DPU UI: `Web-Manage/src/app/DPU/`
- Mobile check-in: `Webview-Mobile/src/app/company/face-scan/`
