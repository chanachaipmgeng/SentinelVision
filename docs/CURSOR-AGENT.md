# Cursor agent guide (DPU Attendance)

How AI agents should work in this repo: **rules** (always-on / file-scoped) and **skills** (task workflows).

## Rules (`.cursor/rules/`)

| File | When |
|------|------|
| `dpu-project.mdc` | Always — stack overview + agent defaults |
| `dpu-face-api.mdc` | `API-Fast/**` — face endpoints, GPU queue, WS |
| `dpu-web-manage.mdc` | `Web-Manage/**` — kiosk, shared list UI kit, shell |
| `dpu-docker.mdc` | Compose / Dockerfiles / nginx |

Rules are short and actionable. Prefer editing the matching rule when conventions change.

## Skills (`.cursor/skills/`)

| Skill | Use when |
|-------|----------|
| `dpu-face-kiosk` | Multi-person kiosk, walk-by, WebSocket stream, InsightFace check-in, `dpu-kiosk-mode` fullscreen |
| `dpu-web-manage-ui` | Admin list CRUD, shared kit, header/sidebar shell, homes, dashboard, face-management dialog |
| `dpu-docker-rebuild` | Rebuild/verify containers (incl. `api-gpu1`), 502, queue-stats, dual-GPU pin |

Invoke by mentioning the skill name or describing the matching task (agent auto-discovers via `description`).

## Security baseline (keep in sync)

- Auth: `API-Fast/src/security/` — `jwt.py` (env `SECRET_KEY`, access 60 min, refresh 14 d), `middleware.py` (`AuthzMiddleware`: token required, company path binding, audit on writes), `deps.py` (`get_current_member`, `require_system_admin`, `assert_company_access`, `assert_request_company_access`), `passwords.py` (temp password, lockout)
- Open paths only: `/auth/login`, `/auth/refresh*`, `/health`, `/ready`, `/metrics`, `/`
- Frontend: `AuthGuard` + `RoleGuard`, single `HttpRequestInterceptor`, kiosk WS session sends `token`, `/auth/change-password` for first login
- Services: `services/audit_service.py`, `notification_service.py` (outbox + SMTP/LINE worker + `ImportJob`), `storage_service.py` (retention), `observability.py` (request-id, JSON logs, `/metrics`), `face_match_service.py`
- Ops: `docs/RUNBOOK.md`, `scripts/backup.sh`, `docker-compose.prod.yml`, `.gitlab-ci.yml`, `API-Fast/alembic/` (baseline marker; runtime schema still via `create_all` + `schema_migrate`)

## Face check-in evolution (keep in sync)

1. **P1** — Multi-track client, crop, parallel check-in, per-member cooldown  
2. **P2** — `POST /face/members/check-in-walkby` (no motion liveness)  
3. **P3** — `WS /face/ws/kiosk` + `face_gpu_queue`  
4. **P4** — JWT on face HTTP + WS session, `FACE_DEVICES` multi-GPU workers, det-only 320 model, WS detect backpressure, `hnsw.ef_search` + company JOIN match  
5. **P5** — Dual-API per GPU (`api` + `api-gpu1`), ORT `provider_options` pin, decode pool / reduced JPEG, realistic kiosk loadtest + saturation ceilings  

Canonical UI: `Web-Manage/.../enroll-face/` (fullscreen via `html.dpu-kiosk-mode`)  
Canonical API: `API-Fast/src/controllers/face_*.py`, `utils/face_engine.py`, `utils/face_gpu_queue.py`

## Admin UI standard (keep in sync)

Shared kit under `Web-Manage/src/app/shared/`:

- Components: `page-toolbar`, `pill-search`, `stat-chip`, `simple-pager`, `empty-state`, `location-map`
- Styles: `shared/styles/dpu-list-page.css`, brand tokens in `assets/css/dpu-theme.css`
- Shell: `content-layout` + decluttered header/sidebar; company menu includes dashboard + kiosk

Pages already on the standard include company emp / timestamp logs / location / info / department / position, admin member/company/admin-manage, dashboard, company & admin homes, face-management dialog, system TTS settings (`/admin/system-setting`). Plain standalone pages: `/company/audit-log` (usage history + notification settings), `/auth/change-password`.

There is **no** `Webview-Mobile` app — check-in is kiosk-only.

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)
- [SETUP.md](SETUP.md)
- [RUNBOOK.md](RUNBOOK.md)
- [KIOSK-LOADTEST.md](KIOSK-LOADTEST.md)
- [KIOSK-LOADTEST-SATURATION.md](KIOSK-LOADTEST-SATURATION.md)
- [BACKLOG.md](BACKLOG.md)
- [PLAN-CLEANUP-REDESIGN.md](PLAN-CLEANUP-REDESIGN.md)
