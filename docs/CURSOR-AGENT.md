# Cursor agent guide (DPU Attendance)

How AI agents should work in this repo: **rules** (always-on / file-scoped) and **skills** (task workflows).

## Rules (`.cursor/rules/`)

| File | When |
|------|------|
| `dpu-project.mdc` | Always — stack overview + agent defaults |
| `dpu-face-api.mdc` | `API-Fast/**` — face endpoints, GPU queue, WS |
| `dpu-web-manage.mdc` | `Web-Manage/**` — kiosk + Angular patterns |
| `dpu-docker.mdc` | Compose / Dockerfiles / nginx |

Rules are short and actionable. Prefer editing the matching rule when conventions change.

## Skills (`.cursor/skills/`)

| Skill | Use when |
|-------|----------|
| `dpu-face-kiosk` | Multi-person kiosk, walk-by, WebSocket stream, InsightFace check-in |
| `dpu-docker-rebuild` | Rebuild/verify containers, 502, queue-stats |

Invoke by mentioning the skill name or describing the matching task (agent auto-discovers via `description`).

## Face check-in evolution (keep in sync)

1. **P1** — Multi-track client, crop, parallel check-in, per-member cooldown  
2. **P2** — `POST /face/members/check-in-walkby` (no motion liveness)  
3. **P3** — `WS /face/ws/kiosk` + `face_gpu_queue`  

Canonical UI: `Web-Manage/.../enroll-face/`  
Canonical API: `API-Fast/src/controllers/face_*.py`, `utils/face_engine.py`, `utils/face_gpu_queue.py`

## Related docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [API.md](API.md)
- [SETUP.md](SETUP.md)
- [BACKLOG.md](BACKLOG.md)
