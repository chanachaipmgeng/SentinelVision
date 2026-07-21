# API reference (summary)

Base URL in Docker: same origin as the UI (nginx), e.g. `http://localhost`.

Interactive docs: http://localhost/docs

## Auth

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/auth/login` | — | Returns JWT |

## Members / org

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET/PUT/DELETE | `/members/{id}` | JWT (GET list/update/delete) | |
| POST | `/members/` | open | Create member |
| CRUD | `/companys/` | open | Companies |
| CRUD | `/company-locations/company/{companyId}` | open | Geofence sites |
| CRUD | `/departments/`, `/positions/` | open | |
| CRUD | `/employees/company/{companyId}` | open | |

## Face

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/face/members/{memberId}/add-face` | open | multipart `file` enroll |
| POST | `/face/members/check-face-emp` | open | multipart `files` + liveness → match payload |
| POST | `/face/members/identify` | open | single frame → name/confidence (no timestamp) |
| POST | `/face/members/check-in` | open | secure: liveness + photo + timestamp |
| POST | `/face/members/check-in-walkby` | open | 1–2 frames, no motion liveness + timestamp |
| WS | `/face/ws/kiosk` | open | stream: session → identify / checkin via GPU queue |
| GET | `/face/queue-stats` | open | GPU queue health |
| GET | `/face/members/{memberId}/encodings` | open | gallery metadata |
| DELETE | `/face/encodings/{faceEncodingId}` | open | |

## Attendance

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| CRUD | `/timestamp/company/{companyId}` | open | create validates GPS server-side |
| GET | `/timestamp/search/company/{companyId}` | open | |
| GET | `/dashboard/stats/{companyId}` | open | aggregates |

## System / files

| Method | Path | Notes |
|--------|------|-------|
| POST | `/system/rebuild-index` | no-op stub (pgvector is live) |
| POST | `/api/upload-image/` | store punch photo |
| GET | `/images/...`, `/enrolled_images/...` | static |

**Security note:** most mutating routes are still unauthenticated. Do not expose this stack publicly without locking JWT first.
