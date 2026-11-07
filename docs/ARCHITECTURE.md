# Architecture (v3.0.0 Enterprise Release)

## Overview

DPU Attendance is a multi-tenant enterprise face-recognition and HR attendance platform:

1. **Admin & HR Console (`Web-Manage`):** Admins enroll employee faces, manage organizations/geofence locations, configure multi-shift rosters (including cross-midnight shifts), approve leaves and outside-area warnings, manage PDPA biometric consent, provision scoped Kiosk device tokens, enable 2FA, configure signed Payroll/ERP webhooks, and export `.xlsx`/`.csv` attendance reports.
2. **Realtime Multi-Person Face Kiosk (`/company/timestamp-face`):** Employees walk past the kiosk camera; WebSocket (`/face/ws/kiosk`) tracks multiple faces, enforces passive anti-spoofing, identifies employees in real time, and records **Hybrid Check-In / Check-Out** punches (`AUTO` / `CHECK_IN` / `CHECK_OUT`). Supports zero-touch provisioning via `?kioskToken=...`.
3. **Backend (`API-Fast`):** FastAPI matches InsightFace `buffalo_l` (512-d) embeddings in PostgreSQL (`pgvector` HNSW cosine index) or proxies vision tasks to **Face Core BFF**, evaluates geofences and shift rules (Late / Overtime), stores images on local disk or S3/MinIO (`AWS4-HMAC-SHA256`), and dispatches audit logs and HMAC-SHA256 signed outbox webhooks asynchronously.

## Runtime topology (Docker)

### Standalone (local InsightFace + pgvector)

```
Browser / Kiosk Tablet
  │
  ▼
nginx :80
  ├─ /                    → admin (Web-Manage static)
  └─ /auth,/face,/hr,…    → api (FastAPI :8000)
                               ├─ Postgres + pgvector :5432
                               └─ Local Disk or S3 / MinIO Object Storage
```

Start with `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build`.

On a dual-GPU host the GPU overlay runs **two API processes** (`dpu-api` on GPU0, `dpu-api-gpu1` on GPU1) behind nginx `least_conn` (`docker/nginx/default.dual-gpu.conf`). Add `docker-compose.gpu-x2.yml` for **two processes per GPU** (`dpu-api-gpu0b`, `dpu-api-gpu1b`, `default.quad-gpu.conf`) when CPU cores are spare.

### Face Core BFF (cross-host / many API replicas)

When `FACE_CORE_ENABLED=true`, DPU keeps `/face/*` URLs and Web-Manage unchanged; vision + gallery run in sibling repo **face-core**; check-in, GPS, dedupe, shift calculation, and HR stay in DPU.

```
Browser → nginx → dpu-api (BFF)
                    ├─ check-in / timestamps / shifts / leaves / PDPA / geofence (DPU DB)
                    └─ httpx → face-core-api :8000 (identify, enroll, verify, detect)
```

## Components

| Component | Path | Role |
|-----------|------|------|
| Gateway | `docker/nginx/` | Reverse proxy (`client_max_body_size 500m`; proxies `/auth`, `/members`, `/companys`, `/company-locations`, `/departments`, `/positions`, `/employees`, `/timestamp`, `/face`, `/hr`, `/notifications`, `/system`, `/dashboard`, `/api`, `/images`, `/enrolled_images`). |
| API | `API-Fast/` | FastAPI v3.0.0: Auth (JWT + RFC 6238 TOTP 2FA + OIDC SSO + Scoped Kiosk Tokens), multi-tenant RBAC, Face Recognition + Passive Anti-Spoofing, Hybrid Check-In/Out, Multi-Shift & Cross-Midnight rosters, Leave & Holiday workflows, PDPA Right to Erasure, `.xlsx`/`.csv` export, S3/MinIO storage, Prometheus histograms, and HMAC-SHA256 signed webhooks. |
| Admin UI | `Web-Manage/` | Angular 17 company/admin console + 6-tab HR/PDPA/Kiosk/Cloud console (`/company/hr-schedule`) + realtime face kiosk (`/company/timestamp-face`). |
| Database | `pgvector/pgvector:pg16` | Relational data + `vector(512)` embeddings with HNSW cosine index. |

## Face, Anti-Spoofing & Attendance Pipeline

1. **Enroll (`POST /face/members/{id}/add-face`)** → dispatched via `run_on_face_gpu` to InsightFace `buffalo_l` → records `Member.biometricConsentAt`, stores `embedding vector(512)` in `pgvector`, and saves image via `storage_service` (`enrolled_images/` + S3/MinIO when `STORAGE_BACKEND=s3`).
2. **Passive Anti-Spoofing (`check_passive_antispoof_bgr`)** → verifies YCrCb skin chrominance variance (`chroma_std >= FACE_ANTISPOOF_MIN_CHROMA_STD`) and screen specular reflection ratio (`specular_ratio <= FACE_ANTISPOOF_MAX_SPECULAR_RATIO`) on both walk-by and multi-frame check-in paths.
3. **1:N Search (`search_face_pgvector`)** → sets `LOCAL hnsw.ef_search`, joins `company_employee` and `member`, filters active employees only (`CompanyEmployee.deletedAt IS NULL`, `Member.deletedAt IS NULL`, `Member.status == ENABLE`), and records query latency in `dpu_pgvector_search_ms`.
4. **Multi-Shift & Hybrid Check-In/Out (`_resolve_employee_shift` & `_compute_shift_metrics`)** → resolves employee shift (`Employee shiftId` → `Department shiftId` → `Default WorkShift` → `Company SystemSetting`), supports cross-midnight Night Shifts (`isCrossMidnight=True`), computes `isLate`, `lateMinutes`, and `overtimeMinutes`, and emits a signed outbound webhook (`attendance.checked_in` / `attendance.checked_out`).

## Enterprise Security, Observability & Migration Controls

- **Fail-Fast Secret Hygiene:** Startup fails if `SECRET_KEY` is shorter than 32 chars or still the placeholder (`AUTH_FAIL_FAST=true`).
- **Strict Multi-Tenancy & Kiosk Scope Isolation (`AuthzMiddleware` + `deps.py`):**
  - URL paths containing `companyId` are verified against `CompanyEmployee` (`deletedAt IS NULL`).
  - Member-level and encoding-level face routes enforce `assert_member_company_access` and `assert_encoding_company_access`.
  - Scoped Kiosk Device Tokens (`typ="kiosk"`) are validated against `kiosk_device` (`revoked_at IS NULL`) and restricted by `_is_kiosk_path_allowed` to only kiosk face/attendance endpoints for their own `companyId`.
- **W3C Trace Context & Prometheus Histograms (`observability.py`):**
  - `RequestIdMiddleware` propagates `X-Request-Id` and W3C `traceparent` into `contextvars` so structured JSON logs include `requestId` and `traceId`.
  - `GET /metrics` and `GET /system/observability-summary` expose `dpu_http_request_duration_ms`, `dpu_face_gpu_latency_ms`, `dpu_pgvector_search_ms`, and `dpu_ws_active_kiosks`.
- **Multi-Replica Signed Webhook Outbox (`notification_service.py`):**
  - `drain_outbox` locks rows with `.with_for_update(skip_locked=True)`, applies exponential backoff, and signs webhook payloads with `X-DPU-Signature-256: v1=<hmac_sha256>`.
- **Schema Migrations:** Idempotent startup migrations live in `API-Fast/src/utils/schema_migrate.py` paired with Alembic revisions (`0001_initial_baseline` through `0005_phase4_kiosk_mfa_antispoof`).
