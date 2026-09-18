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
4. `API-Fast/src/controllers/face_controller.py`, `face_ws_controller.py`, `services/face_match_service.py`
5. `API-Fast/src/utils/face_engine.py`, `face_gpu_queue.py`
6. `API-Fast/src/security/deps.py` (`assert_request_company_access`) and `security/middleware.py`
7. Kiosk helpers: `enroll-face/kiosk-ws-client.ts` (session payload with JWT), `kiosk-tracker.service.ts` (capture interval under backpressure)

## Modes (do not mix carelessly)

| Mode | Client | Server |
|------|--------|--------|
| Secure | multi-frame motion | `POST .../check-in` |
| Walk-by HTTP | 1–2 crops | `POST .../check-in-walkby` |
| Stream (P3) | WS frames | `WS /face/ws/kiosk` → GPU queue |

Kiosk default: **stream**, HTTP walk-by fallback.

## Auth contract

- Every face HTTP route needs `Authorization: Bearer`; form `companyId` is bound to the caller (company admin of that company or system admin)
- WS: first message `{"type":"session","companyId":..,"token":..,"latitude":..,"longitude":..}` — server validates the token and company before accepting frames. Without a valid token the server replies `{"type":"error","detail":"Invalid token"}`
- Access tokens last `ACCESS_TOKEN_EXPIRE_MINUTES` (60). A kiosk that runs all day relies on the HTTP interceptor refresh; re-send `session` after a reconnect with the current token
- Punch photo URLs from the kiosk use `authedImage()` → `/images/<file>?token=<jwt>`

## GPU / backpressure

- `FACE_DEVICES=cuda:0,cuda:1` → one worker per device; `queue-stats.devices` lists them
- Detect frames use the 320 det-size model; embedding uses 640
- When `pending >= WS_QUEUE_BACKPRESSURE` the server answers `detect` with `dropped: true`; use `nextCaptureInterval(queueDepth)` to slow the kiosk

## Fullscreen chrome

- Route match → `html.dpu-kiosk-mode` (content-layout + enroll-face add/remove)
- CSS hides `app-header`, `app-sidebar`, `app-footer`, overlay; content fills `100dvh`
- Layout polish only: do **not** alter detectFace / WS / check-in / geofence logic

## Implementation checklist

- [ ] Multi-track IoU; per-member cooldown; crop-per-track
- [ ] Identify vs check-in separated; check-in goes through `_finalize_check_in`
- [ ] Blocking InsightFace only via `run_on_face_gpu`
- [ ] New face route: `Request` param + `assert_request_company_access(request, db, companyId)` when `companyId` comes from a form/body
- [ ] 1:N search only through `face_match_service.search_face_pgvector` (company JOIN)
- [ ] Dedupe + geofence note handled
- [ ] Nginx WS Upgrade intact if touching gateway
- [ ] Rebuild `api` / `admin` / `nginx` as needed
- [ ] Verify: queue-stats, kiosk shows stream connected, multi-face boxes
- [ ] Leaving kiosk restores shell chrome (class removed)

## Debug

- `GET /face/queue-stats` (Bearer token) — `pending`/`active`/`completed`/`devices`
- 401 on every face call → token missing/expired; 403 → token belongs to another company
- WS closes right after `session` → check `token` in payload and `FACE_ROUTES_REQUIRE_JWT`
- API logs: InsightFace device, pgvector distance
- If 502 after recreate: rebuild/restart nginx (DNS upstream)
- WS fail → client should fall back to HTTP without breaking check-in

## Reference

- [docs/CURSOR-AGENT.md](../../docs/CURSOR-AGENT.md)
- [docs/ARCHITECTURE.md](../../docs/ARCHITECTURE.md)
