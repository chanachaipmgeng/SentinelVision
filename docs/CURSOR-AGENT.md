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
| `dpu-docker-rebuild` | Rebuild/verify containers, 502, queue-stats |

Invoke by mentioning the skill name or describing the matching task (agent auto-discovers via `description`).

## Face check-in evolution (keep in sync)

1. **P1** — Multi-track client, crop, parallel check-in, per-member cooldown  
2. **P2** — `POST /face/members/check-in-walkby` (no motion liveness)  
3. **P3** — `WS /face/ws/kiosk` + `face_gpu_queue`  

Canonical UI: `Web-Manage/.../enroll-face/` (fullscreen via `html.dpu-kiosk-mode`)  
Canonical API: `API-Fast/src/controllers/face_*.py`, `utils/face_engine.py`, `utils/face_gpu_queue.py`

## Admin UI standard (keep in sync)

Shared kit under `Web-Manage/src/app/shared/`:

- Components: `page-toolbar`, `pill-search`, `stat-chip`, `simple-pager`, `empty-state`, `location-map`
- Styles: `shared/styles/dpu-list-page.css`, brand tokens in `assets/css/dpu-theme.css`
- Shell: `content-layout` + decluttered header/sidebar; company menu includes dashboard + kiosk

Pages already on the standard include company emp / timestamp logs / location / info / department / position, admin member/company/admin-manage, dashboard, company & admin homes, face-management dialog, system TTS settings (`/admin/system-setting`).

There is **no** `Webview-Mobile` app — check-in is kiosk-only.

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)
- [SETUP.md](SETUP.md)
- [BACKLOG.md](BACKLOG.md)
- [PLAN-CLEANUP-REDESIGN.md](PLAN-CLEANUP-REDESIGN.md)
