# Backlog & Enterprise Roadmap

## Completed — Foundation & Face Core BFF
- [x] InsightFace `buffalo_l` (512-d) + PostgreSQL `pgvector` HNSW index
- [x] `FACE_CORE_*` settings + `src/clients/face_core_client.py` BFF proxy
- [x] WebSocket kiosk (`/face/ws/kiosk`) multi-person tracking + global TTS speech templates
- [x] Admin UI (`Web-Manage`) list components & theme standardization

## Completed — Phase 1: Enterprise Security & Performance Hardening
- [x] Strict multi-tenant IDOR guardrails (`assert_member_company_access`, `assert_encoding_company_access`) on all `/face/members/*` and `/face/encodings/*` endpoints
- [x] Exclude soft-deleted (`deletedAt IS NOT NULL`) and disabled (`StatusType.DISABLE`) employees from 1:N `pgvector` search and check-in finalization
- [x] Enforce account lockout (`assert_not_locked`) and active status check on both `/auth/login` and `/auth/refresh`
- [x] Offload synchronous `generate_face_encoding` and `verify_liveness_and_get_encoding` to `run_on_face_gpu` so the FastAPI `asyncio` event loop never blocks
- [x] Per-connection WebSocket task semaphore (`asyncio.Semaphore(4)`) and continuous JWT expiration enforcement in `/face/ws/kiosk`
- [x] `/face/ws/kiosk` auth gating: reject every message before an authenticated `session` (close 1008), 5 s auth deadline, per-IP / per-company connection caps (`WS_KIOSK_*`), nginx `limit_conn` on `/face/ws/` (A3)
- [x] Non-blocking Audit Log writes (`asyncio.create_task`) + real client IP extraction from `X-Forwarded-For` / `X-Real-IP`
- [x] Multi-replica safe Notification Outbox (`SELECT ... FOR UPDATE SKIP LOCKED`), non-blocking SMTP/LINE/Webhook dispatch (`asyncio.to_thread`), and persistent daily cutoff markers (`cutoff_sent:{companyId}`)
- [x] Standardized `Asia/Bangkok` business day boundaries across Kiosk, Dashboard, and Cutoff ticks

## Completed — Phase 2: Core HR & Attendance Operations
- [x] **Hybrid Check-In / Check-Out (`AUTO` / `CHECK_IN` / `CHECK_OUT`):** Auto-detect `CHECK_IN (1)` on first scan of the day and `CHECK_OUT (2)` on subsequent scans, plus explicit mode selector buttons on the Kiosk UI
- [x] **Work Shifts & Late / Overtime Calculation:** Configurable per-company shift settings (`GET/PUT /timestamp/company/{companyId}/shift-settings`) calculating `isLate`, `lateMinutes`, `overtimeMinutes`, and `shiftName`
- [x] **Excel (`.xlsx`) & CSV (`.csv`) Attendance Export:** Server-side report generation (`GET /timestamp/export/company/{companyId}`) + one-click export buttons in `TimestampLogComponent`
- [x] Server-side pagination (`limit`, `offset`) and composite database indexes (`0003_enterprise_shifts_and_indexes`)

## Completed — Phase 3: Advanced HR Workflows, Multi-Shift & PDPA Compliance
- [x] **Multi-Shift & Cross-Midnight Roster Assignment (`WorkShift`):** Multiple named shifts per company (including cross-midnight Night Shifts) with hierarchy resolution: Employee override (`company_employee.shift_id`) → Department shift (`department.shift_id`) → Default company shift
- [x] **Leave Requests & Company Holiday Calendar (`LeaveRequest`, `CompanyHoliday`):** Leave request submission (`ANNUAL`, `SICK`, `PERSONAL`, `WFH`) with manager approval workflow (`PENDING` → `APPROVED` / `REJECTED`), plus public holiday calendar integrated with `attendance_cutoff_tick` to skip holidays and approved leaves
- [x] **PDPA Biometric Consent & Right to Erasure:** Track `member.biometric_consent_at` on enrollment/grant, and provide one-click PDPA consent revocation (`DELETE /hr/company/{companyId}/members/{memberId}/biometric-consent`) that immediately purges all enrolled face vectors and images
- [x] **Admin UI (`/company/hr-schedule`):** Unified HR & PDPA Console (`HrScheduleComponent`) in `Web-Manage`

## Completed — Phase 4: Enterprise Identity (SSO / MFA), Kiosk Device Tokens & Passive Anti-Spoofing
- [x] **TOTP Two-Factor Authentication (RFC 6238) & OIDC SSO:** Standard-library RFC 6238 TOTP (`src/security/totp.py`), `/auth/mfa/{status,setup,enable,disable}`, `/auth/sso/oidc`, and 6-digit `totpCode` verification on `/auth/login` (`MFA_REQUIRED` challenge in `LoginComponent`)
- [x] **Dedicated Kiosk Device Provisioning & Scoped Tokens (`KioskDevice`):** Revocable, company-bound `typ="kiosk"` JWTs (`kiosk_device` table with `token_hash`, `last_seen_at`, `revoked_at`), strict route & WebSocket scope isolation (`AuthzMiddleware` + `/face/ws/kiosk`), and one-time pairing codes (`/kiosk/pair` → `/auth/kiosk/pair`, replaced the former `?kioskToken=` URL flow in A5)
- [x] **Single-Frame Passive Anti-Spoofing (`check_passive_antispoof_bgr`):** YCrCb skin chrominance variance + specular screen glare/reflection checks integrated into both walk-by (`get_walkby_encoding_frames`) and multi-frame (`verify_liveness_and_get_encoding`) face recognition paths
- [x] **Admin UI Tab 5 (`อุปกรณ์ Kiosk & 2FA`):** Provision/revoke/re-pair Kiosk devices with a one-time pairing code + setup/enable/disable TOTP 2FA in `HrScheduleComponent`

## Completed — Phase 5: Cloud-Native Observability, Object Storage (S3/MinIO) & Signed Payroll Webhooks
- [x] **S3 / MinIO Object Storage (`src/services/storage_service.py`):** AWS Signature V4 (`AWS4-HMAC-SHA256`) object storage client and presigned URL generator (`generate_presigned_url`, `store_image_bytes`, `store_image_file`, `read_image_bytes`, `delete_stored_image`) integrated across enrollment, check-in photos, file uploads, and PDPA erasure
- [x] **OpenTelemetry W3C Trace Context (`traceparent`) & Prometheus Histograms (`src/services/observability.py`):** Distributed `traceparent` / `X-Request-Id` context propagation into structured JSON logs, plus Prometheus latency histograms (`dpu_http_request_duration_ms`, `dpu_face_gpu_latency_ms`, `dpu_pgvector_search_ms`), live gauges (`dpu_ws_active_kiosks`), and `GET /system/observability-summary`
- [x] **HMAC-SHA256 Signed Outbound Webhooks (`src/services/notification_service.py`):** Signed webhook delivery (`X-DPU-Signature-256: v1=<hmac_sha256>`, `X-DPU-Timestamp`, `X-DPU-Event`, `X-DPU-Delivery-Id`) with exponential backoff, real-time emission on check-in/check-out/approval (`emit_company_webhook_event`), and delivery history inspection (`GET /notifications/company/{companyId}/outbox`)
- [x] **Admin UI Tab 6 (`Payroll Webhook & Cloud Metrics`):** Live P95/Avg latency cards, Storage Backend status, Signed Webhook settings, and Outbox delivery table in `HrScheduleComponent`


## Completed — Phase 6 (SentinelVision v4.0.0): Unified Biometric Security, Access Control, Watchlist, Visitor & Smart Events
- [x] **Unified Non-Employee Biometric Registry (`SentinelIdentity` + `0006_sentinel_vision_core`):** Dedicated `sentinel_identity` table with `embedding vector(512)` HNSW cosine index (`sentinel_identity_embedding_hnsw_idx`) supporting `BLACKLIST`, `POI`, `VIP`, `VISITOR`, and `EVENT_ATTENDEE` profiles with `valid_from` / `expires_at` lifecycle bounds
- [x] **Watchlist, Blacklist & VIP Silent Alarm Engine:** Dual 1:N `pgvector` matching (`search_face_pgvector` + `search_sentinel_identity_pgvector`) across both `/sentinel/company/{companyId}/scan` and live Kiosk recognition (`_resolve_match_response`), logging `CRITICAL` incidents in `sentinel_incident_log` and dispatching immediate `sentinel.blacklist_detected` webhooks via `NotificationOutbox`
- [x] **Smart Access Control Zones & Non-Blocking IoT Door Relay (`SentinelAccessZone`):** Configurable door/turnstile zones with allowed identity types, time schedules (`schedule_start`–`schedule_end`), 2FA enforcement (`require_2fa`), HMAC-SHA256 signed IoT relay webhooks (`_dispatch_relay_webhook_async`), and remote console unlock (`POST .../zones/{zoneId}/trigger`)
- [x] **Visitor Pass & Automated PDPA Expiry Sweeper (`expire_sentinel_identities_tick`):** Temporary visitor face enrollment with automatic PDPA expiration and hourly vector purging in `_retention_loop()`
- [x] **Smart Events & Seminar Check-in (`SentinelEvent`):** Event campaign management, attendee face + seat/table enrollment (`seat_number`), and live welcome/seat lookup on scan
- [x] **Live Building Occupancy, Emergency Muster Roll & Offline-First Edge Sync:** Real-time roster of employees and visitors inside the building today (`GET /sentinel/company/{companyId}/overview`) plus Edge AI vector manifest (`GET /sentinel/company/{companyId}/edge-sync`)
- [x] **UX/UI Modernization & SentinelVision Command Console (`/company/sentinel-center`):** 4-pillar sidebar navigation, container-query responsive sticky tables (`.sv-table-wrapper`), CSS layout containment (`.sv-contain-region`), and 6-tab `SentinelCenterComponent`

## Open — Phase B follow-ups
- [ ] **Playwright E2E smoke (Web-Manage):** add `@playwright/test`, replace the placeholder `e2e/smoke.spec.ts` with login → admin home → kiosk page reaching `session_ok` against a mocked backend (skip when `DPU_BASE_URL` is unset), and run it as a non-blocking CI job before promoting it to a gate
- [ ] **Lint debt (Web-Manage):** re-enable the rules baselined in `.eslintrc.json` one at a time (`@typescript-eslint/no-explicit-any` 248, `no-non-null-asserted-optional-chain` 71, `no-unused-vars` 67, `@angular-eslint/use-lifecycle-interface` 10, `ban-types` 7, `no-empty-lifecycle-method` 2, `no-unsafe-declaration-merging` 2, template `eqeqeq`)
