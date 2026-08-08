---
name: dpu-face-kiosk
description: >-
  Implements or debugs DPU multi-person face kiosk (track, walk-by, WebSocket
  stream, GPU queue). Use when editing timestamp-face/enroll-face, face check-in
  APIs, /face/ws/kiosk, queue-stats, InsightFace liveness/walk-by modes, or
  kiosk fullscreen chrome (dpu-kiosk-mode).
---

# DPU face kiosk workflow

## When to use

Changing kiosk UX, face match/check-in, stream mode, GPU inference queuing, or fullscreen shell for `/company/timestamp-face` (the only check-in UI — no separate mobile app).

## Read first

1. `.cursor/rules/dpu-face-api.mdc` and `dpu-web-manage.mdc`
2. `Web-Manage/.../enroll-face/enroll-face.component.ts`
3. `Web-Manage/.../content-layout.component.ts` + `assets/css/dpu-theme.css` (`dpu-kiosk-mode`)
4. `API-Fast/src/controllers/face_controller.py`, `face_ws_controller.py`
5. `API-Fast/src/utils/face_engine.py`, `face_gpu_queue.py`

## Modes (do not mix carelessly)

| Mode | Client | Server |
|------|--------|--------|
| Secure | multi-frame motion | `POST .../check-in` |
| Walk-by HTTP | 1–2 crops | `POST .../check-in-walkby` |
| Stream (P3) | WS frames | `WS /face/ws/kiosk` → GPU queue |

Kiosk default: **stream**, HTTP walk-by fallback.

## Fullscreen chrome

- Route match → `html.dpu-kiosk-mode` (content-layout + enroll-face add/remove)
- CSS hides `app-header`, `app-sidebar`, `app-footer`, overlay; content fills `100dvh`
- Layout polish only: do **not** alter detectFace / WS / check-in / geofence logic

## Implementation checklist

- [ ] Multi-track IoU; per-member cooldown; crop-per-track
- [ ] Identify vs check-in separated; check-in goes through `_finalize_check_in`
- [ ] Blocking InsightFace only via `run_on_face_gpu`
- [ ] Dedupe + geofence note handled
- [ ] Nginx WS Upgrade intact if touching gateway
- [ ] Rebuild `api` / `admin` / `nginx` as needed
- [ ] Verify: queue-stats, kiosk shows stream connected, multi-face boxes
- [ ] Leaving kiosk restores shell chrome (class removed)

## Debug

- `GET /face/queue-stats` — `pending`/`active`/`completed`
- API logs: InsightFace device, pgvector distance
- If 502 after recreate: rebuild/restart nginx (DNS upstream)
- WS fail → client should fall back to HTTP without breaking check-in

## Reference

- [docs/CURSOR-AGENT.md](../../docs/CURSOR-AGENT.md)
- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)
