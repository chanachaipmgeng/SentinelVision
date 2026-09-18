# API reference (summary)

Base URL in Docker: same origin as the UI (nginx), e.g. `http://localhost`.

Interactive docs are off unless `EXPOSE_API_DOCS=true`. Liveness: `GET /health`. Readiness: `GET /ready`. Counters: `GET /metrics`.

## Auth

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/auth/login` | — | Access + refresh token. Lockout after repeated failures. |
| POST | `/auth/refresh` and `/auth/refresh-token` | refresh token | |
| POST | `/auth/change-password` | JWT | Required when `mustChangePassword` is set |

Every other route needs a Bearer token. Company paths are limited to that company's admin or a system admin. Kiosk WebSocket `session` must include `token`.

## Members / org

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET/PUT/DELETE | `/members/{id}` | JWT (GET list/update/delete) | |
| POST | `/members/` | JWT | Create member |
| CRUD | `/companys/` | JWT | Companies |
| CRUD | `/company-locations/company/{companyId}` | JWT | Geofence sites |
| CRUD | `/departments/`, `/positions/` | JWT | |
| CRUD | `/employees/company/{companyId}` | JWT | |
| GET | `/employees/company/{companyId}/import-template` | JWT | Excel template |
| POST | `/employees/company/{companyId}/import` | JWT | multipart `file` (.xlsx) + optional `photos` (.zip). Duplicate email in the same company → error, other rows continue. Import blur uses `IMAGE_BLUR_THRESHOLD_IMPORT` (`0` = allow blurry HR photos). |
| POST | `/employees/company/{companyId}/import-jobs` | JWT | Same files, runs in the background. Poll `GET .../import-jobs/{jobId}`. |
| GET | `/companys/{companyId}/audit-logs` | JWT | Usage history. |
| GET/PUT | `/notifications/company/{companyId}/settings` | JWT | Email / LINE token for that company. |

## Face

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/face/members/{memberId}/add-face` | JWT | multipart `file` enroll |
| POST | `/face/members/check-face-emp` | JWT | multipart `files` + liveness → match payload |
| POST | `/face/members/identify` | JWT | single frame → name/confidence (no timestamp) |
| POST | `/face/members/check-in` | JWT | secure: liveness + photo + timestamp |
| POST | `/face/members/check-in-walkby` | JWT | 1–2 frames, no motion liveness + timestamp |
| WS | `/face/ws/kiosk` | JWT in session | stream: session (`token`, `companyId`) → identify / checkin via GPU queue |
| GET | `/images/...`, `/enrolled_images/...` | JWT or `?token=` | not public |
| GET | `/face/queue-stats` | JWT | GPU queue health |
| GET | `/face/members/{memberId}/encodings` | JWT | gallery metadata |
| DELETE | `/face/encodings/{faceEncodingId}` | JWT | |

## Attendance

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| CRUD | `/timestamp/company/{companyId}` | JWT | create validates GPS server-side |
| GET | `/timestamp/search/company/{companyId}` | JWT | |
| GET | `/dashboard/stats/{companyId}` | JWT | aggregates |

## System / files

| Method | Path | Notes |
|--------|------|-------|
| POST | `/system/rebuild-index` | no-op stub (pgvector is live) |
| POST | `/api/upload-image/` | store punch photo |
| GET | `/images/...`, `/enrolled_images/...` | JWT or `?token=` |

New employees get a random temporary password (`mustChangePassword`), not `1234`.
