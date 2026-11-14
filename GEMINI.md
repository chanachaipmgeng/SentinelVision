# SentinelVision (DPU Attendance v4.0) — Architecture & Enterprise Engineering Rules

## 1. Current Stack & Topology
- **Repository:** `https://github.com/chanachaipmgeng/SentinelVision.git`
- **Backend (`API-Fast/`):** FastAPI v4.0.0 (Python 3.11, async SQLAlchemy + `asyncpg`) with **InsightFace `buffalo_l` (512-d)** embeddings stored in PostgreSQL `pgvector` (`face_encoding.embedding` for employees and `sentinel_identity.embedding` for Watchlist/Blacklist/VIP/Visitor/Event, both with HNSW cosine indexes), or **Face Core BFF** (`FACE_CORE_ENABLED=true`).
- **Frontend (`Web-Manage/`):** Angular 17 standalone/modular hybrid console + SentinelVision Security & Access Command Center (`/company/sentinel-center`) + realtime multi-person Face Kiosk (`/company/timestamp-face`) using WebSocket (`/face/ws/kiosk`) and shared UI kit (`src/app/shared/components/`).
- **Gateway (`docker/nginx/`):** Single-origin Nginx reverse proxy on port 80 (`default.conf` / `default.dual-gpu.conf` / `default.quad-gpu.conf`).

## 2. Mandatory Security & Multi-Tenancy Guardrails
- **Strict Company Scoping:** Every endpoint accepting `companyId`, `memberId`, `company_employeeId`, or `faceEncodingId` MUST verify caller tenancy via `assert_company_access` / `assert_request_company_access`. Never allow cross-company access.
- **Active Identity Filtering in 1:N Face Match:**
  - Employee 1:N queries (`search_face_pgvector` and `_finalize_check_in`) MUST filter `CompanyEmployee.deletedAt.is_(None)`, `Member.deletedAt.is_(None)`, and `Member.status == StatusType.ENABLE`.
  - Sentinel 1:N queries (`search_sentinel_identity_pgvector`) MUST filter `SentinelIdentity.companyId == companyId`, `SentinelIdentity.deletedAt.is_(None)`, `SentinelIdentity.status == 'ACTIVE'`, and active validity windows (`valid_from <= now <= expires_at`).
- **Kiosk Token & Scope Isolation:** Kiosk WebSocket sessions must validate JWT expiration continuously (not only at handshake) and enforce per-connection rate/concurrency limits. Kiosk tokens (`typ="kiosk"`) are restricted to Kiosk check-in/scan/read endpoints (`_is_kiosk_path_allowed`) and must never be permitted to mutate or delete identities, zones, or company settings.
- **Secret & Credential Hygiene:** `SECRET_KEY` must be >= 32 chars (`AUTH_FAIL_FAST=true`). Never hardcode default passwords (`1234`) or log tokens, passwords, or raw biometric embeddings.

## 3. Performance, Testing & Concurrency Invariants
- **Never Block the Asyncio Event Loop:**
  - All InsightFace inference (`generate_face_encoding`, `verify_liveness_and_get_encoding`, `extract_face_features*`, `detect_faces*`) MUST be dispatched through `run_on_face_gpu(...)`, never called synchronously on a FastAPI route coroutine.
  - Lazy-import `src.utils.face_engine` inside route functions rather than at module top-level so unit tests (`pytest`) can import route modules without requiring GPU/ONNX runtime packages on the test runner.
  - Register all ORM model modules in `API-Fast/src/models/__init__.py` so SQLAlchemy relationship mappers resolve cleanly in isolated tests.
  - Image decoding (`cv2.imdecode`) MUST run on `get_decode_executor()`.
  - Outbox notifications (SMTP / HTTP webhooks) MUST run asynchronously or in a thread pool with `SELECT ... FOR UPDATE SKIP LOCKED` to support multi-replica API deployments safely.
- **Bounded Queries:** List and search endpoints on high-growth tables (`employee_timestamp`, `audit_log`, `notification_outbox`, `sentinel_incident_log`, `sentinel_identity`) MUST enforce server-side pagination (`limit` / `offset` or cursor) with composite indexes.
- **Timezone Consistency:** Business day boundaries (e.g., dashboard stats, kiosk attendance, muster roll, cutoff ticks) MUST use a consistent configured timezone (`Asia/Bangkok` / company timezone) rather than mixing naive `datetime.utcnow()` and aware timestamps.

## 4. Schema, Gateway & Deployment Workflow
- **Database Migrations:** Alembic (`API-Fast/alembic/`) is the only thing that changes the schema; the API runs no DDL at startup. Change the model, then `alembic revision --autogenerate` + `alembic upgrade head`; `alembic check` must stay clean.
- **Nginx Gateway Prefix Sync:** Whenever a new top-level router prefix is added in `API-Fast/src/main.py` (e.g., `/sentinel`), add that prefix to the FastAPI regex location block in `docker/nginx/default.conf`, `default.dual-gpu.conf`, and `default.quad-gpu.conf`.
- **Docker Rebuild Matrix:** Source code is baked into images. Rebuild `api` (and `api-gpu1` on dual-GPU), `admin`, and `nginx` as appropriate, then verify `/health` and `/ready`.

## 5. Frontend Architecture & UI/UX Design System Guardrails
- **VaultX Obsidian Glass & Theme Token Invariants**:
  - Never style card surfaces (`.box`, `.card`, `.modern-card`) with hardcoded light `background: linear-gradient(180deg, rgba(255,255,255,...))` without an explicit dark-theme override (`html[data-theme="dark"]`, `html.dark`, `.dark`, `html[data-theme-mode="dark"]`).
  - Dark surfaces must use the centralized `card-surface` utility (`#070d14` obsidian base, top-lit cyan/slate rim highlight `linear-gradient(180deg, rgba(255, 255, 255, 0.16)...)`).
  - All form labels and body copy inside cards must bind to high-contrast semantic tokens (`#f1f5f9` / `#cbd5e1` / `#94a3b8`) — never rely on inherited body color that could result in light text on light cards.
- **Desktop Shell Overlay Protection**:
  - Modal backdrops intended for mobile navigation drawers (`#responsive-overlay`) MUST be suppressed on desktop screens (`@media (min-width: 992px) { #responsive-overlay { display: none !important; } }`) to prevent screen-blocking dimming.
- **Fast Docker Static Asset Deployment**:
  - For frontend-only changes in `Web-Manage`, build locally via `npm run build` and **wait for the build to exit 0 before** syncing assets into the running container without rebuilding the Docker image:
    `docker cp Web-Manage/dist/preview/browser/. sentinel-admin:/usr/share/nginx/html/`
    `docker exec sentinel-admin nginx -s reload`
- **Modular Scan/Kiosk Visual & Balance Invariants (`/company/scan/:stationMode`)**:
  - `.dpu-kiosk` MUST use the VaultX Obsidian Glass dark base (`#04080f`–`#070d14`) and bind `[attr.data-station-mode]="stationMode"` to drive per-module `--kiosk-accent` / `--kiosk-accent-rgb` tokens (`ATTENDANCE` cyan, `ACCESS_CONTROL` sky, `WATCHLIST_MONITOR` rose, `VISITOR_CHECKIN` violet, `EVENT_CHECKIN` amber, `UNIFIED_HYBRID` teal).
  - Every non-attendance station mode MUST render a dedicated module summary/status card above "ผลล่าสุด" in `.dpu-kiosk__feed-panel` so the right column remains visually balanced with no empty void.
  - Keep background watermark labels (`.dpu-kiosk__float`) low-contrast so they never collide with foreground chips, and verify chip bars and `html.dpu-kiosk-large-text` at `1024x768`.
- **i18n Key Parity**:
  - Whenever adding or renaming labels in `nav.service.ts` or templates using `| translate`, add matching keys to both `Web-Manage/src/assets/i18n/th.json` and `Web-Manage/src/assets/i18n/en.json`.
- **Two-Column Dual-Rail Sidebar Invariants (`app-sidebar.sv-dual-sidebar`)**:
  - Maintain the `17.5rem` (`4.5rem` module rail + `13rem` sub-screens panel) desktop width and synchronized `.app-header` / `.content` / `.footer` offsets in `Web-Manage/src/assets/css/dpu-theme.css`.
  - Derive Column 1 (`moduleGroups`) strictly from `enabledModules` + RBAC permission filtering and hide modules with zero visible items.
  - Clicking a module in Column 1 (`selectModule`) MUST prefer the first non-`/company/scan/` management route so operators stay inside the 2-column Console rather than jumping directly into fullscreen Kiosk mode.
- **File Editing Line Endings**:
  - On Windows environments, normalize CRLF to LF in targeted files prior to calling `edit_file` to ensure exact character-sequence matching.
