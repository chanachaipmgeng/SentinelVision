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
| GET | `/face/queue-stats` | JWT | Queue health. BFF adds `source: face-core`. |
| GET | `/face/enrolled-images/{faceEncodingId}?companyId=` | JWT | Proxies the Face Core gated image. The browser never sees the Face Core key. |
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

## Face Core calls (BFF)

The browser talks only to DPU (`/face/*`, `/face/ws/kiosk`) with a DPU JWT. `dpu-api` calls Face Core. Face Core docs stay off unless `EXPOSE_API_DOCS=true`.

Inside Docker the base URL is `http://face-core-api:8000` on network `face-net` (`FACE_CORE_URL`). From the host, probes use `http://127.0.0.1:8081`. Every authenticated call sends `Authorization: Bearer <FACE_CORE_API_KEY>`. That value is Face Core `BOOTSTRAP_API_KEY`, or a key from `POST /v1/api-keys`. It must be at least 16 characters and must not be `dev-face-core-key-change-me`. Startup exits if `FACE_CORE_ENABLED=true` and the key is missing or weak.

### ID mapping

| DPU | Face Core |
|-----|-----------|
| `companyId` | `companyCode` = `str(companyId)` |
| `memberId` | `subjectId` = `str(memberId)` |
| `faceEncodingId` | `faceId` |

### What DPU sends

| DPU | Face Core | Notes |
|-----|-----------|-------|
| enroll | `PUT /v1/companies/{companyCode}` then `POST /v1/companies/{companyCode}/subjects/{subjectId}/faces` | multipart `file` |
| `POST /face/members/identify`, `check-face-emp` | `POST /v1/identify` | form `companyCode`, `mode=fast`, `files` |
| `POST /face/members/check-in` | `POST /v1/identify` | `mode=secure`, then DPU writes the timestamp |
| `POST /face/members/check-in-walkby`, kiosk walk-by | `POST /v1/identify` | `mode=walkby` |
| kiosk WS `identify` | `POST /v1/identify` | `mode=fast` |
| kiosk WS `detect` | `POST /v1/detect` | boxes only |
| gallery | `GET /v1/companies/{companyCode}/subjects/{subjectId}/faces` | |
| image proxy | `GET /v1/companies/{companyCode}/faces/{faceId}/image` | |
| delete one face | `DELETE /v1/faces/{faceId}` | |
| `GET /face/queue-stats` | `GET /v1/queue-stats` | response `source` is `face-core` |

Identify modes on Face Core are only `fast`, `walkby`, and `secure`. A blank `companyCode` is 400. Matches stay inside that company.

### Probes and failure

| Call | Auth | Used by |
|------|------|---------|
| `GET /v1/health` | none | DPU `GET /ready` (3s). Body includes `service`, `device` (`cuda:0` or `cpu`), `queue`. |
| `GET /v1/ready` | none | Face Core compose health: database, model, and queue started. |

Three Face Core failures open a 15 second circuit. While it is open, face routes and the kiosk return HTTP 503 with detail `face_core_down`. If `/v1/health` itself fails, DPU `/ready` is 503 with `code: face_core_down`. Idempotent SDK calls are retried once before that.
