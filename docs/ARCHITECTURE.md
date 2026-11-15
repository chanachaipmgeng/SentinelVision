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
  ├─ /                              → admin (Web-Manage Angular 19 static)
  └─ /auth,/face,/hr,/sentinel,…    → api (FastAPI :8000)
                                         ├─ Postgres + pgvector :5432
                                         └─ Local Disk or S3 / MinIO Object Storage
```

Start with `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`.

On a dual-GPU host the GPU overlay runs **two API processes** (`sentinel-api` on GPU0, `sentinel-api-gpu1` on GPU1) behind nginx `least_conn` (`docker/nginx/default.dual-gpu.conf`). Add `docker-compose.gpu-x2.yml` for **two processes per GPU** (`default.quad-gpu.conf`).

## Components

| Component | Path | Role |
|-----------|------|------|
| Gateway | `docker/nginx/` | Reverse proxy (`client_max_body_size 500m`; proxies `/auth`, `/members`, `/companys`, `/company-locations`, `/departments`, `/positions`, `/employees`, `/timestamp`, `/face`, `/hr`, `/sentinel`, `/notifications`, `/system`, `/dashboard`, `/api`, `/images`, `/enrolled_images`). |
| API | `API-Fast/` | FastAPI v4.0.0: Auth (JWT + RFC 6238 TOTP 2FA + OIDC SSO + Scoped Kiosk Tokens), Unified 1:N Face Recognition + Passive Anti-Spoofing, Watchlist/Blacklist Silent Alarm, Smart Access Control + IoT Relay Webhook, Visitor Pass + Automated PDPA Expiry Sweeper, Smart Events Check-in, Emergency Muster Roll, Multi-Shift HR, and Signed Webhooks. |
| Admin UI | `Web-Manage/` | Angular 17 company/admin console (`VaultX Obsidian Glass`, Two-Column Dual-Rail Sidebar with `< 992px` off-canvas drawer) + SentinelVision Security Center (`/company/sentinel-center` incl. Investigation Graph) + HR/PDPA/Cloud console (`/company/hr-schedule`) + 6 Modular Scan Stations (`/company/scan/:stationMode`) + Floating AI Copilot (`app-ask-dock` + Silero VAD) + Browser Edge AI WASM assets (`Web-Manage/public/`). |
| Database | `pgvector/pgvector:pg16` | Relational data + `face_encoding.embedding vector(512)` & `sentinel_identity.embedding vector(512)` with HNSW cosine indexes (Alembic `0001..0035`). |

## Browser Edge AI, AI Copilot & Investigation Graph

- **Same-Origin Edge AI Assets (`Web-Manage/public/`):** `angular.json` ignores `**/models/**` under `src/assets`, so MediaPipe (`@mediapipe/tasks-vision`), ONNX Runtime Web (`onnxruntime-web`), `hand_landmarker.task`, and Silero VAD (`@ricky0123/vad-web`) are served from `Web-Manage/public/` (`/mediapipe/*`, `/ort/*`, `/models/*`). Nginx CSP (`docker/nginx/entrypoint/30-dpu-runtime.sh`) permits `'wasm-unsafe-eval'` and `microphone=(self)`.
- **MediaPipe Gesture on Kiosk (`KioskGestureService`):** Opt-in, throttled (~4 Hz) hand-gesture recognition on Kiosk stations without blocking InsightFace WebSocket frames.
- **Security Investigation Graph (`/sentinel/company/{companyId}/graph`):** Company-scoped node/edge graph linking cameras, zones, identities, and incidents.
- **AI Copilot (`app-ask-dock` → `POST /sentinel/company/{companyId}/assistant/chat`):** SSE-streamed operational Q&A backed by `GOOGLE_API_KEY` with automatic fallback to live PostgreSQL company summaries when no API key is configured.

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

## System-admin face login gallery (`system`)

Role-99 (platform system admin) console face login uses a dedicated gallery key **`system`**, separate from company attendance galleries:

| Concern | Today (`FACE_CORE_ENABLED=false`) | Later (Face Core BFF) |
|---|---|---|
| Consent policy | `GET /members/pdpa/consent-policy` → `pdpa_consent:system` (console login copy, not attendance) | Same DPU endpoint; text still owned by DPU |
| Consent record | `Member.biometricConsentAt` (+ version/text) | Unchanged |
| Encodings | Local `face_encoding` rows with `companyId IS NULL` | Face Core `company_code=system` (+ keep local until identify migrates) |
| List / manage | `/face/members/{id}/encodings` always includes local system-gallery rows for role 99 | Merge Face Core `system` + local; never empty solely because the admin has no `company_employee` |
| Identify / login | `POST /auth/login/face` → `search_system_admin_face_pgvector` (local only) | Next cutover: Face Core identify on `system`; login threshold/ambiguity stay stricter than enroll |

Admin Manage (`/admin/admin-manage`) shows PDPA consent dialog **before** grant (no silent auto-grant) and list badges for consent + face count.


## Enterprise Scale, Security & Integration Architecture (Phases 1–10)

- **SCIM 2.0 & HRIS Connectors**: Supports inbound SCIM 2.0 provisioning and Workday / SAP SuccessFactors / BambooHR connectors. Document numbers from OCR/SCIM are masked via `mask_document_number()` before persistence or logging.
- **Redis Hot Cache & Multi-Replica Safety**: Caches company module configuration (`sv:modcfg:{companyId}`) and zone metadata (`sv:zones:{companyId}`) with immediate invalidation on write/delete. Outbox notifications use `SELECT ... FOR UPDATE SKIP LOCKED` to coordinate safely across multiple API replicas.
- **Non-Blocking GPU Inference & TensorRT FP16**: All InsightFace inference is dispatched through `run_on_face_gpu(...)` and image decoding (`cv2.imdecode`) runs on `get_decode_executor()`, supporting CUDA and TensorRT FP16 execution providers without blocking the FastAPI asyncio event loop.
- **ONVIF Discovery, PTZ & PDPA Privacy Mask**: Provides ONVIF network camera discovery, PTZ controls, and per-camera privacy mask zones (`PDPA Mask`) to redact sensitive regions.
- **NVR AI-Marker Timeline & Incident WebSocket**: Streams real-time incidents over WebSocket and surfaces AI incident markers directly on NVR playback timelines.
- **Breakout Room Capacity Check-in**: Tracks per-room capacity limits and live occupancy for event breakout sessions in `/company/sentinel-center`.
- **Multi-Region Disaster Recovery (`/sentinel/dr/replicate`)**: Verifies cross-region replication payloads with HMAC-SHA256 (`X-Sentinel-DR-Sig`, `hmac.compare_digest`) and deduplicates via Redis idempotency keys (`ttl_seconds=86400`).

## Testing & Verification

- **Backend Static Analysis & Unit/Integration Tests (`API-Fast/`)**:
  - Lint: `ruff check .`
  - Type check: `python -m mypy --no-incremental`
  - Test suite: `python -m pytest -q -p no:cacheprovider` (53 passed)
- **Frontend Production Build (`Web-Manage/`)**:
  - Build: `npm run build` (Angular 17 production bundle synced to `sentinel-admin`)
