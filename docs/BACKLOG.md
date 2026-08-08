# Backlog

Carried forward from the original Sprint#1 notes (`Web-Manage/Sprint.txt`).

## Sprint #1 — Common / platform (incomplete)

- User management (code, name, password, access rights) — partially present via members/roles
- Login audit log (user id, date, time, IP) — **not implemented**
- Activity audit (menu, view, create, update, delete) — **not implemented**
- CSV import/export with other systems — **not implemented**

## Hardening (recommended)

- Require JWT on face, timestamp, company, and system routes
- Rotate `SECRET_KEY` / DB passwords; stop committing secrets
- Wire Admin `AuthGuard` on routes
- Automated tests for enroll / check-in / geofence

## Product polish

- Admin ThemeForest demo strip + list UI standard — **done** (see [PLAN-CLEANUP-REDESIGN.md](PLAN-CLEANUP-REDESIGN.md) P1)
- Align `Webview-Mobile` shell/tokens to the same teal design system — **open**
- Finish mobile stub screens (working-plan, approval, e-document) or remove routes
- Close remaining P2 gaps: employee profile fields + approval status on mobile history
