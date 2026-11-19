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
- **PDPA PII Masking & Signed Replication:** Never persist or log raw 13-digit Thai National IDs or full Passport numbers from OCR/SCIM; always mask via `mask_document_number()`. Cross-region DR endpoints (`/sentinel/dr/replicate`) must verify HMAC-SHA256 (`X-Sentinel-DR-Sig`) with constant-time `hmac.compare_digest` and deduplicate via Redis idempotency keys (`kiosk_scan_debounce_check("dr", event_id, ttl_seconds=86400)`).
- **Soft-Delete Query Consistency:** Every soft-deletable ORM model (`deletedAt`) MUST filter `Model.deletedAt.is_(None)` across **all** list, company-scoped list (`get_*_by_companyId`), get-by-ID, and update queries — never only in `delete_*` — so soft-deleted rows never reappear in UI tables or trigger `404` on follow-up actions.
- **Incident Location & Camera Batch-Enrichment Invariant:** Every endpoint or service querying, serializing, or broadcasting security and access incidents (`list_incidents`, `get_overview`, incident lifecycle transitions `acknowledge`/`assign`/`close`, and real-time WebSocket push `publish_incident_event`) MUST batch-enrich records via `enrich_incidents_location_metadata(db, company_id, ...)` to populate `cameraName`, `building`, `floorLevel`, `floorName`, `mapPosX`, `mapPosY`, `siteFloorId`, `locationName`, `latitude`, and `longitude` without N+1 queries.

## 3. Performance, Testing & Concurrency Invariants
- **Never Block the Asyncio Event Loop:**
  - All InsightFace inference (`generate_face_encoding`, `verify_liveness_and_get_encoding`, `extract_face_features*`, `detect_faces*`) MUST be dispatched through `run_on_face_gpu(...)`, never called synchronously on a FastAPI route coroutine.
  - Lazy-import `src.utils.face_engine` inside route functions rather than at module top-level so unit tests (`pytest`) can import route modules without requiring GPU/ONNX runtime packages on the test runner.
  - Register all ORM model modules in `API-Fast/src/models/__init__.py` so SQLAlchemy relationship mappers resolve cleanly in isolated tests.
  - Image decoding (`cv2.imdecode`) MUST run on `get_decode_executor()`.
  - Outbox notifications (SMTP / HTTP webhooks) MUST run asynchronously or in a thread pool with `SELECT ... FOR UPDATE SKIP LOCKED` to support multi-replica API deployments safely.
- **Bounded Queries:** List and search endpoints on high-growth tables (`employee_timestamp`, `audit_log`, `notification_outbox`, `sentinel_incident_log`, `sentinel_identity`) MUST enforce server-side pagination (`limit` / `offset` or cursor) with composite indexes.
- **Timezone Consistency:** Business day boundaries (e.g., dashboard stats, kiosk attendance, muster roll, cutoff ticks) MUST use a consistent configured timezone (`Asia/Bangkok` / company timezone) rather than mixing naive `datetime.utcnow()` and aware timestamps.
- **Model-First & Permission-Signature Verification (Backend & Tests):**
  - Before writing SQLAlchemy queries, serializers, or pytest fixtures, inspect the exact ORM model (`API-Fast/src/models/`) for column/attribute names, NOT NULL constraints, and whether `deletedAt` exists (e.g., `WorkShift.name`, `Member.username`/`passwordHash`/`RoleType`, `CompanyEmployee.positionId`, `AttendanceDaily.employeeId`/`otMinutes`, and `EmployeeTimestamp` has no `deletedAt`).
  - Always pass `assert_request_permission(request, db, perm_code, companyId)` (`perm_code` before `companyId`) and use `world.auth("admin_a")` in `API-Fast/tests/` instead of nonexistent `*.admin_headers` attributes.
  - Verify backend changes with `ruff check .`, `python -m mypy --no-incremental`, and `python -m pytest -q -p no:cacheprovider`.
- **PostgreSQL Session GUC & Redis Cache Safety:** Wrap optional session-level `SET LOCAL` tuning (e.g., `hnsw.iterative_scan`) in `db.begin_nested()` (`SAVEPOINT`) with `AsyncMock` safety so test mocks and non-pgvector engines never abort transactions. Always invalidate `sv:modcfg:{companyId}` / `sv:zones:{companyId}` on every write/delete path.
- **Single-Line OCR Regex Guard:** In OCR text parsers (`id_ocr_service.py`), never use `\s` inside single-line capture groups (use explicit `' '`) so matches never bleed across newlines.
- **CI Strict `mypy` & `cv2` Mock-Safe Testing:**
  - Explicitly annotate local SQLAlchemy `select(...)` variables (e.g. `prev_q: Any = (...)`) when `.where(...)` uses inline conditional expressions so strict CI `mypy` (`[var-annotated]`) passes cleanly.
  - Because some unit tests (`test_kiosk_blacklist_exposure.py`, `test_sentinel_search_gate.py`) assign `sys.modules["cv2"] = MagicMock()`, any service lazy-importing `cv2` (`privacy_mask_service.py`) MUST validate `isinstance(result, np.ndarray) and result.shape == expected_shape` and provide a pure-NumPy fallback.

## 4. Schema, Gateway & Deployment Workflow
- **Database Migrations:** Alembic (`API-Fast/alembic/`) is the only thing that changes the schema; the API runs no DDL at startup. Change the model, then `alembic revision --autogenerate` + `alembic upgrade head`; `alembic check` must stay clean.
- **Nginx Gateway Prefix Sync:** Whenever a new top-level router prefix is added in `API-Fast/src/main.py` (e.g., `/sentinel`), add that prefix to the FastAPI regex location block in `docker/nginx/default.conf`, `default.dual-gpu.conf`, and `default.quad-gpu.conf`.
- **Docker Rebuild Matrix (GPU-First `api-gpu`):** `docker-compose.yml` runs **`api-gpu`** (`sentinel-api-gpu`, with network alias `api`) and GPU-enabled **`worker`** (`CUDA_VISIBLE_DEVICES=0`, `FACE_DEVICE=cuda:0`) by default. Source code is baked into images; rebuild `api-gpu` (and `api-gpu1` only when using the dual-GPU `docker-compose.gpu.yml` overlay), `admin`, and `nginx` as appropriate, then verify `/health` and `/ready` (`devices: ["cuda:0"]`).
- **Trivy Container Security & Alpine Nginx Dynamic Modules:** In Alpine-based Nginx images (`Web-Manage/Dockerfile`, `docker/nginx/Dockerfile`), unused pre-installed dynamic modules (`nginx-module-geoip`, `nginx-module-image-filter`, `nginx-module-njs`, `nginx-module-xslt`) MUST be purged via `apk del` before running `apk upgrade` to prevent pinned version locks from blocking Nginx security upgrades during CI `trivy image` vulnerability scans.
- **Full-Stack Docker Build & Health Verification:** When building all container services, rebuild the complete matrix (`docker compose build api-gpu admin nginx worker`), recreate containers with `docker compose up -d`, and verify `/health`, `/ready` (`devices: ["cuda:0"]` with active queue workers), and HTTP 200 on Nginx.

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
  - Never launch `docker cp`, `git commit`, or browser verification in parallel with a running `ng build` task; wait for the background `npm run build` notification (`Command exited with code 0`) first.
  - When verifying in an existing browser session after deploying static assets, reload with cache disabled or a cache-busting query string (e.g., `/?v=...#/`) and confirm the newly built `styles-*.css` bundle is loaded.
- **Model-First Template & Exporter Edits**:
  - Before adding CSV exporters, filters, or template bindings, inspect the exact TypeScript model/interface (`*.model.ts` / `*.models.ts` / `*.service.ts`) so field names match 100% on the first build.
  - Before implementing a roadmap item, search the target module/component to confirm what already exists so duplicate endpoints or UI controls are never added.
- **Header Control Uniformity & Dark-Mode Logo**:
  - Keep `.sv-search-chip`, `.dpu-header-lang`, `.sv-header-btn`, and `.dpu-header-avatar` in `.app-header` on a single shared height and pill/circle geometry (`2.25rem` on desktop; `2.5rem` on `< 992px` mobile).
  - In dark mode, explicitly hide `.app-header .dpu-header-brand img.desktop-logo` / `img.toggle-logo` and display `img.toggle-dark` so dark logos never blend into the obsidian header.
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
  - Under `@media (max-width: 991.98px)`, keep `.app-sidebar` off-canvas (`transform: translateX(-100%)` / `visibility: hidden` / `pointer-events: none` for `html:not([data-toggled="open"])`) so it never overlaps `.app-header` or `.content` on initial load.
  - Align JS breakpoint checks (`SidebarComponent.ngOnInit()`, `HeaderComponent.toggleSidebar()`) strictly to `window.innerWidth < 992` (matching CSS `991.98px` / `992px`), initialize `data-toggled="close"` on `< 992px` load unless already `open`, and only strip `data-toggled` in `selectModule()` on desktop (`>= 992px`) icon-collapsed states.
- **File Editing Line Endings**:
  - On Windows environments, normalize CRLF to LF in targeted files prior to calling `edit_file` to ensure exact character-sequence matching.
  - Never write `open(p, 'wb').write(open(p, 'rb').read()...)` on the same path (opening `'wb'` truncates the file before `'rb'` reads it); always read into a variable first, then write.
  - In Windows PowerShell 5.1, chain dependent commands with `; if ($?) { ... }` instead of `&&`.
- **Browser Edge AI & WASM Asset Serving (`Web-Manage/public/`)**:
  - `Web-Manage/angular.json` ignores `**/models/**` under `src/assets`. Same-origin browser AI assets (`/mediapipe/*`, `/ort/*`, `/models/*`) MUST be served from `Web-Manage/public/` (mapped to `/`) and populated via `npm run sync-mediapipe`, `npm run sync-ort`, `npm run fetch-hand-model`, and `npm run fetch-silero-vad`.
  - Keep browser-side MediaPipe Gesture (`KioskGestureService`) opt-in and throttled (~4 Hz) so it never competes with InsightFace WebSocket frames on low-power Kiosk hardware.
  - Keep ambient canvas effects (`ConstellationComponent`, `HorizonGlowComponent`) scoped to Login / Landing / Kiosk idle — never mount them behind dense admin data tables.
- **Copilot & Investigation Graph Tenancy**:
  - `/sentinel/company/{companyId}/graph` and `/sentinel/company/{companyId}/assistant/chat` MUST enforce `assert_request_company_access` and fall back gracefully to live PostgreSQL company summaries when `GOOGLE_API_KEY` is unset.
- **Bento Grid Architecture & Shared Component Invariants**:
  - Grid wrapper `<app-bento-grid>` enforces responsive 12-column CSS Grid (`grid-template-columns: repeat(12, minmax(0, 1fr))`) collapsing to 1 column on `< 768px`. It MUST dynamically support both Tailwind gap classes (`gap="gap-5"`) and raw CSS lengths (`gap="1.25rem"`).
  - Child cards `<app-bento-card>` MUST use `:host { display: contents; }` so child `.sv-bento-card` participates directly in the parent grid's 12-column layout via responsive span classes (`col-span-12 xl:col-span-8`, etc.) with VaultX Obsidian Glass dark surfaces (`#070d14` base + rim highlight) and light-theme overrides.
  - Accent tones are strictly constrained to 7 semantic tokens: `cyan` (Attendance/Core), `sky` (Access Control), `rose` (Watchlist/Threats), `amber` (Visitor/Events), `violet` (CCTV/MediaMTX), `emerald` (Active/Healthy), and `slate` (Neutral/Inactive).
  - In component `@Input()` definitions, avoid `Record<string, any>` (which fails strict ESLint `@typescript-eslint/no-explicit-any`); use `Params` from `@angular/router` or `Record<string, unknown>`.
  - In Karma unit tests for standalone components or test hosts consuming `@ngx-translate/core` pipes (`| translate`), always provide `TranslateModule.forRoot()` in `TestBed.configureTestingModule({ imports: [TranslateModule.forRoot(), ...] })` to prevent `NG0201: No provider found for TranslateStore`.
