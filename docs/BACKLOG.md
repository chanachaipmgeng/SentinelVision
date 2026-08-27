# Backlog

Carried forward from the original Sprint#1 notes (`Web-Manage/Sprint.txt`).

## Sprint #1 — Common / platform (incomplete)

- User management (code, name, password, access rights) — partially present via members/roles
- Login audit log (user id, date, time, IP) — **not implemented**
- Activity audit (menu, view, create, update, delete) — **not implemented**
- CSV import/export with other systems — **not implemented**

## Done — Face Core BFF (Phase 1)

- [x] `FACE_CORE_*` settings + `src/clients/face_core_client.py`
- [x] `/face/*` enroll/identify/verify/gallery proxy when `FACE_CORE_ENABLED=true`
- [x] Check-in keeps `_finalize_check_in` in DPU (GPS, dedupe, timestamp)
- [x] WS kiosk identify/checkin/detect via Face Core; URLs unchanged
- [x] `docker-compose.face-core.yml` + skip local GPU queue when enabled
- [x] `scripts/migrate_faces_to_face_core.py`

## Hardening (recommended)

- Require JWT on face, timestamp, company, and system routes
- Rotate `SECRET_KEY` / DB passwords; stop committing secrets
- Wire Admin `AuthGuard` on routes
- Automated tests for enroll / check-in / geofence (incl. Face Core BFF mocks)
- Smoke: enroll → identify → walk-by check-in isolation across companies

## Product polish

- Admin ThemeForest demo strip + list UI standard — **done** (see [PLAN-CLEANUP-REDESIGN.md](PLAN-CLEANUP-REDESIGN.md) P1)
- Face kiosk + global TTS speech templates — **done**
- Close remaining P2 gaps: employee profile fields + approval workflow polish
