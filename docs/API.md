# API Reference (Summary)

Base URL in Docker: same origin as the UI (nginx), e.g. `http://localhost`.

Interactive docs are off unless `EXPOSE_API_DOCS=true`. Liveness: `GET /health`. Readiness: `GET /ready`. Prometheus counters, gauges & histograms: `GET /metrics`. Every response includes `X-Request-Id` and W3C `traceparent` headers.

## Auth & Enterprise Identity (MFA / SSO)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/auth/login` | — | Access + refresh token. Enforces `assert_not_locked` and active account status (`ENABLE`). When `totpEnabled=True`, requires 6-digit `totpCode` (returns `HTTP 401` with `detail="MFA_REQUIRED"` if omitted). |
| POST | `/auth/refresh` and `/auth/refresh-token` | refresh token | Verifies account is not locked or disabled before issuing new tokens. |
| POST | `/auth/change-password` | JWT | Required when `mustChangePassword` is set. |
| GET | `/auth/mfa/status` | JWT | Returns `{"totpEnabled": bool}` for the current user. |
| POST | `/auth/mfa/setup` | JWT | Generates RFC 6238 Base32 secret (`secret`) and `otpauth://` URI (`otpauthUri`) for Authenticator apps. |
| POST | `/auth/mfa/enable` | JWT | Verifies 6-digit `totpCode` (`{"code": "123456"}`) and activates 2FA (`totpEnabled=True`). |
| POST | `/auth/mfa/disable` | JWT | Verifies 6-digit `totpCode` (`{"code": "123456"}`) and disables 2FA (`totpEnabled=False`). |
| POST | `/auth/sso/oidc` | — | Exchanges external OIDC ID Token (`{"idToken": "..."}`) for DPU access & refresh tokens. |

Every other route needs a Bearer token. Company paths are limited to that company's active employee/admin or a system admin. Kiosk Device Tokens (`typ="kiosk"`) are strictly isolated by `AuthzMiddleware` to only `/face/ws/kiosk`, `/face/members/{detect,identify,check-in,check-in-walkby,check-face-emp}`, `/face/kiosk-attendance/{companyId}`, and `/system/tts-settings` for their assigned `companyId`.

## Members / Organization & Signed Payroll Webhooks

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET/PUT/DELETE | `/members/{id}` | JWT | Soft-delete on `DELETE`. |
| POST | `/members/` | JWT | Create member. |
| CRUD | `/companys/` | JWT | Companies. |
| CRUD | `/company-locations/company/{companyId}` | JWT | Geofence sites (`latitude`, `longitude`, `radius`). |
| CRUD | `/departments/`, `/positions/` | JWT | Company-scoped departments & positions (`shiftId` included on departments). |
| CRUD | `/employees/company/{companyId}` | JWT | Company employees (`shiftId` and `member.biometricConsentAt` included). |
| GET | `/employees/company/{companyId}/import-template` | JWT | Excel template. |
| POST | `/employees/company/{companyId}/import` | JWT | multipart `file` (.xlsx) + optional `photos` (.zip). |
| POST | `/employees/company/{companyId}/import-jobs` | JWT | Runs bulk import in background; poll `GET .../import-jobs/{jobId}`. |
| GET | `/companys/{companyId}/audit-logs` | JWT | Paginated audit trail (`limit`, `offset`). |
| GET/PUT | `/notifications/company/{companyId}/settings` | JWT | Configure `email`, `lineToken`, `webhookUrl`, `webhookSecret` (HMAC-SHA256 signing key), `cutoff` (`HH:MM`), and `events` (`attendance.checked_in`, `attendance.checked_out`, `attendance.approved`, `attendance.missing`). |
| POST | `/notifications/company/{companyId}/test` | JWT | Enqueue signed test notification across configured channels (`X-DPU-Signature-256: v1=<hmac>`). |
| GET | `/notifications/company/{companyId}/outbox` | JWT | List recent Outbox deliveries (`status`, `attempts`, `event`, `channel`, `lastError`) for the company. |
| GET | `/notifications/pending-count` | JWT | Optional `?companyId=` filter for pending outbox count. |

## Face Recognition & Kiosk

All `/face/members/{memberId}/*` and `/face/encodings/{faceEncodingId}` routes verify caller tenancy via `assert_member_company_access` / `assert_encoding_company_access`. Both multi-frame check-in and walk-by check-in enforce single-frame passive anti-spoofing (`check_passive_antispoof_bgr`: YCrCb skin chrominance variance + screen specular glare detection) when `FACE_ANTISPOOF_ENABLED=true`.

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/face/members/{memberId}/add-face` | JWT | multipart `file` enroll (dispatched via `run_on_face_gpu`; records `member.biometricConsentAt` and stores image via `storage_service`). |
| POST | `/face/members/detect` | JWT / Kiosk | Lightweight face bbox detection for preview. |
| POST | `/face/members/check-face-emp` | JWT / Kiosk | multipart `files` + `companyId` + liveness → match payload. |
| POST | `/face/members/identify` | JWT / Kiosk | single frame + `companyId` → name/confidence (no timestamp). |
| POST | `/face/members/check-in` | JWT / Kiosk | secure: liveness + passive anti-spoofing + photo + timestamp. Optional form `punchType` (`AUTO` \| `CHECK_IN` \| `CHECK_OUT`). |
| POST | `/face/members/check-in-walkby` | JWT / Kiosk | 1–3 frames + passive anti-spoofing, walk-by check-in/out + timestamp. Optional form `punchType` (`AUTO` \| `CHECK_IN` \| `CHECK_OUT`). |
| WS | `/face/ws/kiosk` | JWT / Kiosk | stream: `session` (`token`, `companyId`) must be the first message and be acknowledged with `session_ok` before `detect` / `identify` / `checkin` (supports `punchType` and `typ="kiosk"` tokens). Any other message before auth, a failed `session`, or no valid `session` within `WS_KIOSK_AUTH_TIMEOUT_SECONDS` (5 s) → `error` (`code`: `unauthenticated` / `invalid_session` / `auth_timeout`) and close 1008. Per-IP / per-company caps (`WS_KIOSK_MAX_CONN_PER_IP`=16, `WS_KIOSK_MAX_CONN_PER_COMPANY`=64) close with `too_many_connections`; nginx also applies `limit_conn` 16/IP (HTTP 429). |
| GET | `/face/kiosk-attendance/{companyId}` | JWT / Kiosk | Today's (`Asia/Bangkok`) roster + summary (`checkedInCount`, `inAreaCount`, `checkedOutCount`, `outsideCount`, `lateCount`). |
| GET | `/face/queue-stats` | JWT | GPU queue health. BFF adds `source: face-core`. |
| GET | `/face/enrolled-images/{faceEncodingId}?companyId=` | JWT | Proxies the Face Core gated image, local disk image, or S3/MinIO object. |
| GET | `/face/members/{memberId}/encodings` | JWT | Gallery metadata for member. |
| DELETE | `/face/members/{memberId}/encodings` | JWT | Clear all face encodings for member (deletes from DB, local disk, and S3/MinIO). |
| DELETE | `/face/encodings/{faceEncodingId}` | JWT | Delete single face encoding. |
| POST | `/face/members/{memberId}/verify` | JWT | 1:1 test scan against member's enrolled faces (no check-in). |

## Attendance, Multi-Shift, Leave, Holidays, PDPA & Kiosk Devices

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/timestamp/company/{companyId}` | JWT | List company timestamps (`limit` default 500, max 2000; `offset`). Includes `isLate`, `lateMinutes`, `overtimeMinutes`, `shiftName`. |
| POST | `/timestamp/company/{companyId}` | JWT | Create timestamp. Validates GPS server-side, resolves hybrid `CHECK_IN` (1) / `CHECK_OUT` (2) / `WARNING` (0), calculates shift Late/OT (including cross-midnight shifts), and emits signed outbound webhook (`attendance.checked_in` / `attendance.checked_out`). |
| PUT/DELETE | `/timestamp/company/{companyId}/{timestampId}` | JWT | Update or delete timestamp. |
| POST | `/timestamp/company/{companyId}/{timestampId}/approval` | JWT | Approve (`CHECK_IN`) or reject (`ABSENT`) outside-geofence warning timestamp and emit signed webhook (`attendance.approved` / `attendance.rejected`). |
| GET | `/timestamp/search/company/{companyId}` | JWT | Filter by `company_employeeId`, `startDate`, `endDate`, `timestampType`, `approvalStatus`, `limit`, `offset`. |
| GET | `/timestamp/export/company/{companyId}` | JWT | Download attendance report as Excel (`.xlsx`) or CSV (`.csv`). Query params: `format=xlsx\|csv`, `company_employeeId`, `startDate`, `endDate`, `timestampType`, `approvalStatus`. |
| GET/PUT | `/timestamp/company/{companyId}/shift-settings` | JWT | Get or update company default work shift (`name`, `startTime` `HH:MM`, `endTime` `HH:MM`, `graceMinutes`). |
| GET/POST | `/hr/company/{companyId}/shifts` | JWT | List or create named work shifts (`WorkShift`, supports `isCrossMidnight`, `isDefault`). |
| PUT/DELETE | `/hr/company/{companyId}/shifts/{shiftId}` | JWT | Update or soft-delete a named work shift. |
| PUT | `/hr/company/{companyId}/assign-shift` | JWT | Assign a shift (`shiftId`) to a department (`departmentId`) or employee (`company_employeeId`). |
| GET/POST | `/hr/company/{companyId}/holidays` | JWT | List or create company public holidays (`CompanyHoliday`). Skipped automatically by `attendance_cutoff_tick`. |
| DELETE | `/hr/company/{companyId}/holidays/{holidayId}` | JWT | Soft-delete a company holiday. |
| GET/POST | `/hr/company/{companyId}/leaves` | JWT | List or submit employee leave requests (`ANNUAL`, `SICK`, `PERSONAL`, `WFH`). |
| POST | `/hr/company/{companyId}/leaves/{leaveId}/approval` | JWT | Approve (`status=1`) or reject (`status=2`) a leave request. Approved leaves are excluded from missing check-in alerts. |
| GET | `/hr/company/{companyId}/pdpa-summary` | JWT | PDPA biometric consent summary & retention policy (`imageRetentionDays`, `tempRetentionHours`, `storageBackend`). |
| POST/DELETE | `/hr/company/{companyId}/members/{memberId}/biometric-consent` | JWT | Grant PDPA biometric consent (`POST`) or revoke consent & immediately purge enrolled face vectors from DB + S3/local storage (`DELETE`). |
| GET/POST | `/hr/company/{companyId}/kiosk-devices` | JWT | List provisioned Kiosk devices or provision a new device (`POST` returns one-time `kioskToken` and `kioskUrl`). |
| DELETE | `/hr/company/{companyId}/kiosk-devices/{deviceId}` | JWT | Revoke a Kiosk device token immediately (`isActive=False`, `revokedAt`). |
| GET | `/dashboard/stats/{companyId}` | JWT | `Asia/Bangkok` daily summary (`checkInsToday`, `inAreaToday`, `outsideToday`, `checkOutsToday`, `lateToday`, `pendingApproval`), 7-day chart, map points, and recent activity. |

## System, Cloud Storage & Observability

| Method | Path | Notes |
|--------|------|-------|
| GET | `/metrics` | Prometheus text exposition (`dpu_http_request_duration_ms`, `dpu_face_gpu_latency_ms`, `dpu_pgvector_search_ms`, `dpu_ws_active_kiosks`). |
| GET | `/system/observability-summary` | JSON summary of latency histograms (P50, P95, Avg), GPU queue, active Kiosk WebSockets, and Cloud Storage (`local` / `s3`). |
| GET/PUT | `/system/tts-settings` | Global kiosk TTS voice template settings. |
| POST | `/system/rebuild-index` | No-op stub (`pgvector` HNSW index is live). |
| POST | `/api/upload-image/` | Store uploaded photo (returns `path` and optional S3 `presignedUrl`). |
| GET | `/images/...`, `/enrolled_images/...` | Gated by JWT Bearer header or `?token=`. |


## SentinelVision Security, Access Control, Watchlist, Visitor & Smart Events (`/sentinel`)

All `/sentinel/company/{companyId}/*` routes enforce multi-tenant company authorization via `AuthzMiddleware` and `assert_request_company_access`. Kiosk Device Tokens (`typ="kiosk"`) are restricted to `POST /sentinel/company/{companyId}/scan`, `GET /sentinel/company/{companyId}/edge-sync`, and `GET /sentinel/company/{companyId}/zones`.

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/sentinel/company/{companyId}/overview` | JWT | Unified KPIs (`blacklistAndPoiCount`, `vipCount`, `activeVisitorCount`, `eventAttendeeCount`, `activeZonesCount`, `liveEventsCount`, `unacknowledgedAlerts`, `buildingOccupancyCount`), **Live Emergency Muster Roll** (`musterRoll`), and `recentIncidents`. |
| GET/POST | `/sentinel/company/{companyId}/identities` | JWT | List or create non-employee Sentinel identities (`BLACKLIST`, `POI`, `VIP`, `VISITOR`, `EVENT_ATTENDEE`) with optional PDPA `expiresAt`, `severity`, `alertNote`, `visitPurpose`, `seatNumber`, `eventId`, `allowedZoneIds`. |
| PUT/DELETE | `/sentinel/company/{companyId}/identities/{identityId}` | JWT | Update or revoke/soft-delete a Sentinel identity (purges `embedding` vector on delete). |
| POST | `/sentinel/company/{companyId}/identities/{identityId}/enroll-face` | JWT | Multipart `file` upload; extracts 512-d InsightFace `buffalo_l` embedding via `run_on_face_gpu` and stores in `sentinel_identity.embedding`. |
| GET/POST | `/sentinel/company/{companyId}/zones` | JWT / Kiosk (`GET`) | List or create Smart Access Control door/kiosk zones (`stationMode`, `allowedIdentityTypes`, `scheduleStart`, `scheduleEnd`, `require2FA`, `relayWebhookUrl`, `relaySecret`). |
| PUT/DELETE | `/sentinel/company/{companyId}/zones/{zoneId}` | JWT | Update or deactivate an Access Control zone. |
| POST | `/sentinel/company/{companyId}/zones/{zoneId}/trigger` | JWT | Remote manual unlock / test pulse for an Access Control door relay; logs `ACCESS_GRANTED` incident. |
| GET/POST | `/sentinel/company/{companyId}/events` | JWT | List or create Smart Event / Seminar campaigns (`name`, `locationName`, `startAt`, `endAt`, `welcomeMessage`, `capacity`, `autoExpireDays`). |
| DELETE | `/sentinel/company/{companyId}/events/{eventId}` | JWT | Close and soft-delete an event campaign. |
| POST | `/sentinel/company/{companyId}/scan` | JWT / Kiosk | Unified 1:N Biometric Scan (`file`, optional `zoneId`, `eventId`, `stationMode`, `totpOrPin`): evaluates `BLACKLIST`/`POI` silent alarms, Access Control rules, IoT door relay, Event seat lookup, and Employee verification. |
| GET | `/sentinel/company/{companyId}/incidents` | JWT | Paginated security & access incident log (`eventType`, `severity`, `limit`, `offset`). |
| POST | `/sentinel/company/{companyId}/incidents/{incidentId}/acknowledge` | JWT | Acknowledge a `WARNING` or `CRITICAL` security incident. |
| GET | `/sentinel/company/{companyId}/edge-sync` | JWT / Kiosk | Offline-First Edge Kiosk embedding manifest (`manifestVersion`, `employeeVectorsCount`, `sentinelVectorsCount`, `totalActiveVectors`, `activeZones`). |
