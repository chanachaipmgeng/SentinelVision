# Architecture (SentinelVision v4.0.0 Enterprise Release)

## Overview

**SentinelVision** (`https://github.com/chanachaipmgeng/SentinelVision.git`) is a multi-tenant unified biometric identity, workforce attendance, smart access control, watchlist/blacklist alerting, and event check-in platform:

1. **SentinelVision Security & HR Console (`Web-Manage`):**
   - **Sentinel Command Center (`/company/sentinel-center`):** Manage Watchlist (`BLACKLIST`, `POI`) & `VIP` registries, Smart Access Control Door Zones (`SentinelAccessZone` with schedules, 2FA, and IoT Relay Webhooks), temporary `VISITOR` face passes with automatic PDPA expiration, Smart Events & Seminar campaigns (`SentinelEvent` with seat lookup), Live Building Occupancy / Emergency Muster Roll, and Offline-First Edge AI Manifest synchronization.
   - **HR, Multi-Shift & PDPA Console (`/company/hr-schedule`):** Manage organizations, geofence sites, multi-shift rosters (including cross-midnight shifts), leaves, public holidays, PDPA biometric consent & erasure, scoped Kiosk device tokens, TOTP 2FA, and signed Payroll/ERP webhooks.
2. **Realtime Multi-Person Face Kiosk (`/company/timestamp-face`):**
   - Employees, VIPs, Visitors, or Event Attendees walk past the kiosk camera; WebSocket (`/face/ws/kiosk`) and Unified Scan (`/sentinel/company/{companyId}/scan`) track faces, enforce passive anti-spoofing, evaluate Watchlist/Access/Event rules in real time, and record **Hybrid Check-In / Check-Out** punches (`AUTO` / `CHECK_IN` / `CHECK_OUT`).
3. **Backend (`API-Fast`):**
   - FastAPI v4.0.0 matches InsightFace `buffalo_l` (512-d) embeddings in PostgreSQL via dual `pgvector` HNSW cosine indexes (`face_encoding` for employees and `sentinel_identity` for Watchlist/VIP/Visitor/Event) or proxies vision tasks to **Face Core BFF**, evaluates access zones, geofences, and shift rules, stores images on local disk or S3/MinIO (`AWS4-HMAC-SHA256`), and dispatches IoT door relays and HMAC-SHA256 signed outbox webhooks asynchronously.

## Runtime topology (Docker)

### Standalone (local InsightFace + pgvector)

```
Browser / Kiosk Tablet / IoT Door Controller
  │
  ▼
nginx :80
  ├─ /                              → admin (Web-Manage Angular 17 static)
  └─ /auth,/face,/hr,/sentinel,…    → api (FastAPI :8000)
                                         ├─ Postgres + pgvector :5432
                                         └─ Local Disk or S3 / MinIO Object Storage
```

Start with `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`.

On a dual-GPU host the GPU overlay runs **two API processes** (`dpu-api` on GPU0, `dpu-api-gpu1` on GPU1) behind nginx `least_conn` (`docker/nginx/default.dual-gpu.conf`). Add `docker-compose.gpu-x2.yml` for **two processes per GPU** (`default.quad-gpu.conf`).

## Components

| Component | Path | Role |
|-----------|------|------|
| Gateway | `docker/nginx/` | Reverse proxy (`client_max_body_size 500m`; proxies `/auth`, `/members`, `/companys`, `/company-locations`, `/departments`, `/positions`, `/employees`, `/timestamp`, `/face`, `/hr`, `/sentinel`, `/notifications`, `/system`, `/dashboard`, `/api`, `/images`, `/enrolled_images`). |
| API | `API-Fast/` | FastAPI v4.0.0: Auth (JWT + RFC 6238 TOTP 2FA + OIDC SSO + Scoped Kiosk Tokens), Unified 1:N Face Recognition + Passive Anti-Spoofing, Watchlist/Blacklist Silent Alarm, Smart Access Control + IoT Relay Webhook, Visitor Pass + Automated PDPA Expiry Sweeper, Smart Events Check-in, Emergency Muster Roll, Multi-Shift HR, and Signed Webhooks. |
| Admin UI | `Web-Manage/` | Angular 17 company/admin console + 6-tab SentinelVision Security Center (`/company/sentinel-center`) + 6-tab HR/PDPA/Cloud console (`/company/hr-schedule`) + realtime face kiosk (`/company/timestamp-face`). |
| Database | `pgvector/pgvector:pg16` | Relational data + `face_encoding.embedding vector(512)` & `sentinel_identity.embedding vector(512)` with HNSW cosine indexes. |

## Unified Biometric, Security & Attendance Pipeline

1. **Dual 1:N Vector Search (`search_face_pgvector` + `search_sentinel_identity_pgvector`):**
   - Queries both `face_encoding` (active company employees) and `sentinel_identity` (`BLACKLIST`, `POI`, `VIP`, `VISITOR`, `EVENT_ATTENDEE` within valid time bounds `valid_from <= now <= expires_at`) using `pgvector` HNSW cosine distance.
2. **Priority 1 — Watchlist & Blacklist Silent Alarm:**
   - If a `BLACKLIST` or `POI` face is matched, `SentinelVision` logs a `CRITICAL` incident in `sentinel_incident_log`, enqueues an immediate webhook notification (`sentinel.blacklist_detected`) in `notification_outbox`, and blocks access.
3. **Priority 2 — Smart Access Control & IoT Door Relay:**
   - Evaluates `SentinelAccessZone` rules (`allowed_identity_types`, `schedule_start`–`schedule_end`, `require_2fa`), logs `ACCESS_GRANTED` or `ACCESS_DENIED`, and triggers the zone's `relay_webhook_url` asynchronously in a worker thread.
4. **Priority 3 — Smart Events, Visitor Pass & Workforce Attendance:**
   - Displays event welcome message and `seat_number` for `EVENT_ATTENDEE`, checks in temporary `VISITOR` passes, or calculates shift Late/Overtime for `EMPLOYEE` punches.
5. **Automated PDPA Biometric Expiry (`expire_sentinel_identities_tick`):**
   - Hourly `_retention_loop()` automatically transitions expired `SentinelIdentity` records (`expires_at < now()`) to `status='EXPIRED'` and nulls out their 512-d `embedding` vector.
