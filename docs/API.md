# API Reference (Summary)

Base URL in Docker: same origin as the UI (nginx), e.g. `http://localhost`.

**API v1 (Phase D6):** every public router is also mounted under `/api/v1` (e.g. `/api/v1/auth/login`). `/companies` is an alias of the legacy `/companys` spelling (both at root and under `/api/v1`). Errors use `{ "error": { "code", "message", "status", "requestId?" }, "detail" }` — `detail` mirrors `error.message` for older clients; 5xx never echoes raw exception text. Punch create (`POST /timestamp/company/{id}`) and employee import (`POST …/import`, `…/import-jobs`) honour `Idempotency-Key` (replay returns the first response).

**App rate limits (Phase D7):** login / identify / import are limited in-process (Redis when `REDIS_URL` is set) in addition to nginx `limit_req` → HTTP `429` `{ "error": { "code": "rate_limited" } }`.

Interactive docs are off unless `EXPOSE_API_DOCS=true`. Liveness: `GET /health`. Readiness: `GET /ready`. Prometheus counters, gauges & histograms: `GET /metrics`. Every response includes `X-Request-Id` and W3C `traceparent` headers.

## Auth & Enterprise Identity (MFA / SSO)

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/auth/login` | — | Access + refresh token. Enforces `assert_not_locked` and active account status (`ENABLE`). When `totpEnabled=True`, requires 6-digit `totpCode` (returns `HTTP 401` with `detail="MFA_REQUIRED"` if omitted). Both tokens carry `jti`, `typ` (`access` / `refresh`) and a shared session family `fam`. |
| POST | `/auth/refresh` and `/auth/refresh-token` | refresh token | **Rotates**: the presented refresh token is revoked and a new access + refresh pair (same `fam`) is returned. Presenting an already-rotated refresh token is treated as theft — the whole family is revoked (`401 Refresh token reuse detected`). Verifies account is not locked or disabled. |
| POST | `/auth/logout` | JWT (may be expired) + optional `refreshToken` | Revokes the access token in the header, the refresh token in the body, and their session family. Idempotent. Returns `{"ok": true, "revokedTokens": n, "familyRevoked": bool}`. |
| POST | `/auth/kiosk/pair` | — | Body `{"pairingCode": "ABCD-EFGH"}`. Exchanges a one-time pairing code (issued by `POST /hr/company/{companyId}/kiosk-devices`) for a device-scoped session: `deviceToken` (`typ="kiosk"`, TTL `KIOSK_TOKEN_EXPIRE_HOURS`), `deviceRefreshToken` (`typ="kiosk_refresh"`, TTL `KIOSK_REFRESH_EXPIRE_DAYS`), `deviceId`, `companyId`, `deviceName`. Single use; `401` when the code is wrong, used, or expired; `429` after `KIOSK_PAIR_MAX_ATTEMPTS_PER_MINUTE` attempts per IP. |
| POST | `/auth/kiosk/refresh` | kiosk refresh token | Rotates the device token pair (old refresh revoked; reuse revokes the device family so it must be re-paired). The previous `deviceToken` stops matching `kiosk_device.token_hash` immediately. |
| POST | `/auth/change-password` | JWT | Required when `mustChangePassword` is set. |
| GET | `/auth/mfa/status` | JWT | Returns `{"totpEnabled": bool}` for the current user. |
| POST | `/auth/mfa/setup` | JWT | Generates RFC 6238 Base32 secret (`secret`) and `otpauth://` URI (`otpauthUri`) for Authenticator apps. |
| POST | `/auth/mfa/enable` | JWT | Verifies 6-digit `totpCode` (`{"code": "123456"}`) and activates 2FA (`totpEnabled=True`). |
| POST | `/auth/mfa/disable` | JWT | Verifies 6-digit `totpCode` (`{"code": "123456"}`) and disables 2FA (`totpEnabled=False`). |
| GET | `/auth/sso/oidc/status` | — | `{"enabled": bool, "issuer": str|null, "flow": "authorization_code+pkce"}`. The Login page shows the SSO button only when `enabled`. |
| POST | `/auth/sso/oidc/start` | — | Body `{"companyId"?: uuid, "returnTo"?: "/same-origin/path"}`. Returns `{"authorizeUrl", "state", "txn", "expiresIn"}`. `txn` is an HS256-signed, short-lived transaction holding the `nonce` and PKCE `code_verifier`; the SPA keeps it in `sessionStorage` and never sends it to the IdP. `501` when `OIDC_ENABLED=false`. |
| POST | `/auth/sso/oidc/callback` (alias `/auth/sso/oidc`) | — | Body `{"code", "state", "txn"}`. Exchanges the code at the IdP token endpoint (PKCE), verifies the ID token (JWKS **RS256/ES256** only, `iss`, `aud`, `exp`, `iat`, `nonce`, `azp`, optional `at_hash`), maps `email` (must not be `email_verified=false`) to an active Member, enforces lockout + `StatusType.ENABLE`, and returns the same `Token` payload as `/auth/login` (+ `returnTo`). Unknown emails are rejected (`404`) unless the company passed to `/start` has JIT provisioning enabled. The former self-signed `{"idToken"}` contract is removed. |
| GET/PUT | `/auth/sso/policy/{companyId}` | JWT (company admin) | Per-company SSO policy: `{"jitProvisioning": false, "allowedEmailDomains": [], "defaultDepartmentId": null, "defaultPositionId": null}`. `jitProvisioning` defaults **off**; turning it on requires a default department + position of the same company. New members get role `MEMBER` / `EMP`, a random local password, `employeeId = sub`. |

Every other route needs a Bearer token in the `Authorization` header. `?token=` in the query string is **no longer accepted** (it leaked tokens into proxy/browser logs); the deprecation flag `AUTH_ALLOW_QUERY_TOKEN=true` re-enables it temporarily and logs a warning on every use. Company paths are limited to that company's active employee/admin or a system admin. Kiosk Device Tokens (`typ="kiosk"`) are strictly isolated by `AuthzMiddleware` to only `/face/ws/kiosk`, `/face/members/{detect,identify,check-in,check-in-walkby,check-face-emp}`, `/face/kiosk-attendance/{companyId}`, and `/system/tts-settings` for their assigned `companyId`.

### Token lifecycle & revocation

- Every JWT carries `jti`, `typ` and `fam`. `AuthzMiddleware` (and the `/face/ws/kiosk` `session` handshake) rejects tokens whose `jti` or `fam` is in the `revoked_token` table with `401 Token has been revoked`. Lookups go through a small in-process cache; a revocation becomes visible on every API replica within `AUTH_REVOCATION_CACHE_SECONDS` (default 30 s). Expired rows are purged every `AUTH_REVOCATION_PURGE_SECONDS`.
- Tokens issued before this change (no `jti`) keep working until they expire but cannot be revoked.
- Kiosk device tokens are additionally bound to `kiosk_device.token_hash` (only the latest token issued to the device is valid) and to `kiosk_device.token_family`.

## Members / Organization & Signed Payroll Webhooks

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET/PUT/DELETE | `/members/{id}` | JWT | Soft-delete on `DELETE`. |
| POST | `/members/` | JWT | Create member. |
| CRUD | `/companys/` and `/companies/` (also under `/api/v1`) | JWT | Companies. |
| CRUD | `/company-locations/company/{companyId}` | JWT | Geofence sites (`latitude`, `longitude`, `radius`). |
| CRUD | `/departments/`, `/positions/` | JWT | Company-scoped departments & positions (`shiftId` included on departments). |
| CRUD | `/employees/company/{companyId}` | JWT | Company employees (`shiftId` and `member.biometricConsentAt` included). |
| GET | `/employees/company/{companyId}/import-template` | JWT | Excel template. |
| POST | `/employees/company/{companyId}/import` | JWT | multipart `file` (.xlsx) + optional `photos` (.zip). |
| POST | `/employees/company/{companyId}/import-jobs` | JWT | Stores the upload and queues an `import_job` for the `worker` service → `{jobId, status: "pending", progress}`. Poll `GET .../import-jobs/{jobId}` → `{jobId, status: pending\|running\|done\|failed, progress: {processed,total,success,failed,facesEnrolled}, result, error, attempts, createdAt, startedAt, finishedAt}`. |
| GET | `/companys/{companyId}/audit-logs` | JWT | Paginated audit trail (`limit`, `offset`). |
| GET/PUT | `/notifications/company/{companyId}/settings` | JWT | Configure `email`, `lineToken`, `webhookUrl`, `webhookSecret` (HMAC-SHA256), `telegramBotToken`, `telegramChatId`, `discordWebhookUrl` (Incoming Webhook), `cutoff` (`HH:MM`), and `events`. Secrets are never echoed — use `hasLineToken` / `hasTelegramBotToken` / `hasDiscordWebhookUrl` / `hasWebhookSecret`. Blank secret on PUT keeps the stored value. |
| POST | `/notifications/company/{companyId}/test` | JWT | Enqueue test notification across configured channels (email / LINE / webhook / Telegram / Discord / in_app). Webhook tests include `X-DPU-Signature-256: v1=<hmac>`. |
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
| POST | `/face/members/check-in` | JWT / Kiosk | secure: liveness + passive anti-spoofing + photo + timestamp. Optional form `punchType` (`AUTO` \| `CHECK_IN` \| `BREAK_OUT` \| `BREAK_IN` \| `CHECK_OUT`). AUTO advances IN→BREAK_OUT→BREAK_IN→OUT. |
| POST | `/face/members/check-in-walkby` | JWT / Kiosk | 1–3 frames + passive anti-spoofing, walk-by check-in/out + timestamp. Optional form `punchType` (`AUTO` \| `CHECK_IN` \| `BREAK_OUT` \| `BREAK_IN` \| `CHECK_OUT`). |
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
| POST | `/timestamp/company/{companyId}` | JWT | Create timestamp. Validates GPS server-side, resolves hybrid punch types `CHECK_IN` (1) / `BREAK_OUT` (4) / `BREAK_IN` (5) / `CHECK_OUT` (2) / `WARNING` (0); AUTO state machine IN→BREAK_OUT→BREAK_IN→OUT (cross-midnight preserved). Late/OT only on IN/OUT. Emits webhooks (`attendance.checked_in` / `attendance.break_out` / `attendance.break_in` / `attendance.checked_out`). |
| PUT/DELETE | `/timestamp/company/{companyId}/{timestampId}` | JWT | Update or delete timestamp. |
| POST | `/timestamp/company/{companyId}/{timestampId}/approval` | JWT | Approve (`CHECK_IN`) or reject (`ABSENT`) outside-geofence warning timestamp and emit signed webhook (`attendance.approved` / `attendance.rejected`). |
| GET | `/timestamp/search/company/{companyId}` | JWT | Filter by `company_employeeId`, `startDate`, `endDate`, `timestampType`, `approvalStatus`, `limit`, `offset`. |
| GET | `/timestamp/export/company/{companyId}` | JWT | Download attendance report as Excel (`.xlsx`) or CSV (`.csv`). Query params: `format=xlsx\|csv`, `company_employeeId`, `startDate`, `endDate`, `timestampType`, `approvalStatus`. |
| GET/PUT | `/timestamp/company/{companyId}/shift-settings` | JWT | Get or update company default work shift (`name`, `startTime` `HH:MM`, `endTime` `HH:MM`, `graceMinutes`). |
| GET/POST | `/hr/company/{companyId}/shifts` | JWT | List or create named work shifts (`WorkShift`, supports `isCrossMidnight`, `isDefault`). |
| PUT/DELETE | `/hr/company/{companyId}/shifts/{shiftId}` | JWT | Update or soft-delete a named work shift. |
| PUT | `/hr/company/{companyId}/assign-shift` | JWT | Assign a shift (`shiftId`) to a department (`departmentId`) or employee (`company_employeeId`). |
| GET/POST | `/hr/company/{companyId}/holidays` | JWT | List or create company public holidays (`CompanyHoliday`). GET accepts optional `start`/`end` date filters for metrics. Skipped automatically by `attendance_cutoff_tick`. |
| POST | `/hr/company/{companyId}/holidays/import` | JWT | Import holidays from CSV or iCal (`.ics`) via multipart `file` or JSON `{format, content}`. Upserts by date; sets `source` to `CSV`/`ICAL`. |
| POST | `/hr/company/{companyId}/holidays/thai-preset` | JWT | Seed Thai public-holiday preset for `year` (body/query; default Asia/Bangkok current year). `source=THAI_PRESET`. |
| DELETE | `/hr/company/{companyId}/holidays/{holidayId}` | JWT | Soft-delete a company holiday. |
| GET/POST | `/hr/company/{companyId}/leaves` | JWT | List or submit employee leave requests (`ANNUAL`, `SICK`, `PERSONAL`, `WFH`). |
| POST | `/hr/company/{companyId}/leaves/{leaveId}/approval` | JWT | Approve (`status=1`) or reject (`status=2`) a leave request. Approved leaves are excluded from missing check-in alerts. |
| GET | `/hr/company/{companyId}/pdpa-summary` | JWT | PDPA biometric consent summary & retention policy (`imageRetentionDays`, `tempRetentionHours`, `storageBackend`). |
| POST/DELETE | `/hr/company/{companyId}/members/{memberId}/biometric-consent` | JWT | Grant PDPA biometric consent (`POST`) or revoke consent & immediately purge enrolled face vectors from DB + S3/local storage (`DELETE`). |
| GET/POST | `/hr/company/{companyId}/kiosk-devices` | JWT | List Kiosk devices (`isPaired`, `pairingPending`, `pairingExpiresAt`, `lastSeenAt`, `isActive`) or provision a new device. `POST` body `{"name", "locationId"?}` returns a **one-time `pairingCode`** (`ABCD-EFGH`, valid `KIOSK_PAIRING_CODE_TTL_MINUTES`, shown once, stored hashed) to enter on the tablet at `/kiosk/pair`. No token or URL is returned. |
| POST | `/hr/company/{companyId}/kiosk-devices/{deviceId}/pairing-code` | JWT | Re-pair an existing device: revokes its current token family and issues a fresh `pairingCode`. `409` when the device is revoked. |
| DELETE | `/hr/company/{companyId}/kiosk-devices/{deviceId}` | JWT | Revoke a Kiosk device immediately (`isActive=False`, `revokedAt`): its token family is denied, `token_hash` cleared, and pending pairing codes dropped. |
| GET | `/dashboard/stats/{companyId}` | JWT | `Asia/Bangkok` daily summary (`checkInsToday`, `inAreaToday`, `outsideToday`, `checkOutsToday`, `lateToday`, `pendingApproval`), 7-day chart, map points, and recent activity. |

## Face Monitor Analytics (Phase 6C)

Postgres-first aggregates (no ClickHouse). Requires `cameras.read`. Admin UI: `/company/face-monitor`.

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/analytics/company/{companyId}/heatmap` | JWT (`cameras.read`) | Hour×weekday grid (`Asia/Bangkok`). Query `start`, `end`, `source`=`incidents`\|`attendance`\|`both`. |
| GET | `/analytics/company/{companyId}/occupancy` | JWT | Distinct subjects per hour from `sentinel_incident_log`. |
| GET | `/analytics/company/{companyId}/dwell` | JWT | Session dwell per camera/zone (5-minute gap). |
| GET | `/analytics/company/{companyId}/camera-health` | JWT | MediaMTX camera registry status + event counts. |
| GET | `/analytics/company/{companyId}/summary` | JWT | Bundle of KPIs + heatmap + occupancy + dwell + camera health. |
| GET | `/analytics/company/{companyId}/export/pdf` | JWT | PDF attachment of the summary (reportlab, with minimal fallback). |

## System, Cloud Storage & Observability

| Method | Path | Notes |
|--------|------|-------|
| GET | `/metrics` | Prometheus text exposition (`dpu_http_request_duration_ms`, `dpu_face_gpu_latency_ms`, `dpu_pgvector_search_ms`, `dpu_ws_active_kiosks`). |
| GET | `/system/observability-summary` | JSON summary of latency histograms (P50, P95, Avg), GPU queue, active Kiosk WebSockets, and Cloud Storage (`local` / `s3`). |
| GET/PUT | `/system/tts-settings` | Global kiosk TTS voice template settings. |
| POST | `/system/rebuild-index` | No-op stub (`pgvector` HNSW index is live). |
| POST | `/api/upload-image/` | Store uploaded photo (returns `path` and optional S3 `presignedUrl`). |
| GET | `/images/...`, `/enrolled_images/...` | Gated by JWT Bearer header (`?token=` is rejected unless `AUTH_ALLOW_QUERY_TOKEN=true`). The kiosk loads punch photos through `HttpClient` and renders them from blob URLs (`AuthedImageService`). |


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
