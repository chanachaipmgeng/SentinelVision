# DPU Attendance — Architecture & Enterprise Engineering Rules

## 1. Current Stack & Topology
- **Backend (`API-Fast/`):** FastAPI (Python 3.11, async SQLAlchemy + `asyncpg`) with **InsightFace `buffalo_l` (512-d)** embeddings stored in PostgreSQL `pgvector` (`face_encoding.embedding vector(512)` with HNSW cosine index), or **Face Core BFF** (`FACE_CORE_ENABLED=true`).
- **Frontend (`Web-Manage/`):** Angular 17 standalone/modular hybrid console + realtime multi-person Face Kiosk (`/company/timestamp-face`) using WebSocket (`/face/ws/kiosk`) and shared UI kit (`src/app/shared/components/`).
- **Gateway (`docker/nginx/`):** Single-origin Nginx reverse proxy on port 80 (`default.conf` / `default.dual-gpu.conf` / `default.quad-gpu.conf`).

## 2. Mandatory Security & Multi-Tenancy Guardrails
- **Strict Company Scoping:** Every endpoint accepting `companyId`, `memberId`, `company_employeeId`, or `faceEncodingId` MUST verify caller tenancy via `assert_company_access` / `assert_request_company_access`. Never allow cross-company access.
- **Active Employee Filtering in 1:N Face Match:** All face matching queries (`search_face_pgvector` and `_finalize_check_in`) MUST filter `CompanyEmployee.deletedAt.is_(None)`, `Member.deletedAt.is_(None)`, and `Member.status == StatusType.ENABLE`.
- **Kiosk Token & Scope Isolation:** Kiosk WebSocket sessions must validate JWT expiration continuously (not only at handshake) and enforce per-connection rate/concurrency limits.
- **Secret & Credential Hygiene:** `SECRET_KEY` must be >= 32 chars (`AUTH_FAIL_FAST=true`). Never hardcode default passwords (`1234`) or log tokens, passwords, or raw biometric embeddings.

## 3. Performance & Concurrency Invariants
- **Never Block the Asyncio Event Loop:**
  - All InsightFace inference (`generate_face_encoding`, `verify_liveness_and_get_encoding`, `extract_face_features*`, `detect_faces*`) MUST be dispatched through `run_on_face_gpu(...)`, never called synchronously on a FastAPI route coroutine.
  - Image decoding (`cv2.imdecode`) MUST run on `get_decode_executor()`.
  - Outbox notifications (SMTP / HTTP webhooks) MUST run asynchronously or in a thread pool with `SELECT ... FOR UPDATE SKIP LOCKED` to support multi-replica API deployments safely.
- **Bounded Queries:** List and search endpoints on high-growth tables (`employee_timestamp`, `audit_log`, `notification_outbox`) MUST enforce server-side pagination (`limit` / `offset` or cursor) with composite indexes.
- **Timezone Consistency:** Business day boundaries (e.g., dashboard stats, kiosk attendance, cutoff ticks) MUST use a consistent configured timezone (`Asia/Bangkok` / company timezone) rather than mixing naive `datetime.utcnow()` and aware timestamps.

## 4. Schema & Deployment Workflow
- **Database Migrations:** Never use destructive `DROP TABLE` at startup. Add idempotent schema updates in `API-Fast/src/utils/schema_migrate.py` paired with an Alembic revision in `API-Fast/alembic/versions/`.
- **Docker Rebuild Matrix:** Source code is baked into images. Rebuild `api` (and `api-gpu1` on dual-GPU), `admin`, and `nginx` as appropriate, then verify `/health` and `/ready`.
