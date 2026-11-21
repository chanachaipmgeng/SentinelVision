# SentinelVision `v6.4.0` — Enterprise UAT & E2E Delivery Sign-Off

**Release Version:** `v6.4.0`  
**Verification Date:** `2026-11-21`  
**Target Stack:** `http://localhost:8880` (`sentinel-api-gpu` CUDA `cuda:0`, `sentinel-worker`, `sentinel-admin`, `sentinel-nginx`, PostgreSQL 16 `pgvector` schema `0037_vehicle_parking_rfid`, Redis 7, MediaMTX)  
**Repository:** `https://github.com/chanachaipmgeng/SentinelVision.git`

---

## 1. Automated Verification Scorecard

| Layer | Verification Command | Result |
| :--- | :--- | :--- |
| **Backend Linter & Types** | `ruff check .` + `python -m mypy --no-incremental` | ✅ **0 errors** |
| **Backend Automated Suite** | `python -m pytest -q -p no:cacheprovider` | ✅ **587 passed** |
| **Frontend Linter & Build** | `npm run lint` + `npm run build` | ✅ **0 errors, 0 warnings** |
| **Container Security (Trivy)** | `trivy image --config trivy.yaml --scanners vuln dpu/backup:ci` | ✅ **0 vulnerabilities** |
| **Full Playwright E2E Suite** | `npm run test:e2e:all` (7 spec files, all 8 modules + Admin + WS Kiosk) | ✅ **23 / 23 passed (56.1s)** |
| **Live Gateway Health** | `GET /health` & `GET /ready` | ✅ **HTTP 200 (`cuda:0`, `0037_vehicle_parking_rfid`)** |

---

## 2. Module-by-Module E2E Sign-Off Matrix

| Phase | Module / Scope | Playwright Spec | Live CRUD / Simulator Verified | Result |
| :--- | :--- | :--- | :--- | :---: |
| **Smoke & Kiosk WS** | Gateway Health, Login Form, Live Login, Kiosk WebSocket JWT Handshake | `e2e/smoke.spec.ts`, `e2e/kiosk-session.spec.ts` | Live JWT handshake + invalid first-frame rejection | ✅ **4 / 4 PASS** |
| **Phase 1 (Modules 0–1)** | Landing Hero, Global Search (`Ctrl K`), Dashboard KPI (`totalEmployees`), Departments, Positions, Employees | `e2e/phase1-admin-org.spec.ts` | Compact 8-char UUID pills, Dept & Pos CRUD + auto-cleanup, Emp `...` overflow menu | ✅ **5 / 5 PASS** |
| **Phase 2 (Module 2)** | Timestamp Log, Warning Log, Approval Inbox, Reports, Self-Service (`0 HTTP 404`), Mobile Check-In, GPS Locations, HR Shifts/Leaves/Holidays, Face Scan Kiosk | `e2e/phase2-attendance-hr.spec.ts` | Styled VaultX file uploads, Holiday CRUD + auto-cleanup, Fake-webcam Kiosk PDPA modal | ✅ **4 / 4 PASS** |
| **Phase 3A (Module 3)** | Access Control (Zones/Logs/Settings), Smart Parking & LPR, RFID Physical Access Cards | `e2e/phase3a-access-parking-rfid.spec.ts` | Parking Spot + Vehicle CRUD + **LPR Entry/Exit Gate Simulator** (`BARRIER OPEN` + Dwell Time) + cleanup; RFID Issue + **Swipe Simulator** (`ACCESS GRANTED`) + cleanup | ✅ **3 / 3 PASS** |
| **Phase 3B (Modules 4–6)** | Watchlist (Identities/Incidents/Settings), Emergency Muster Roll, Visitors (Passes/Settings), Smart Events (Campaigns/Check-ins/Settings) | `e2e/phase3b-watchlist-visitor-events.spec.ts` | All 10 routes load with 0 page/HTTP errors | ✅ **2 / 2 PASS** |
| **Phase 4 (Module 7)** | Audit Log, Kiosk Devices, Edge Fleet Health, Cameras/CCTV, Settings Hub & RBAC, Notification Center, Profile Security | `e2e/phase4-governance-fleet.spec.ts` | Dynamic health score badge, offline CCTV `—` latency, `<app-page-header>` + disabled offline PTZ, single active settings rail, single `<select>` chevron (`::picker-icon`), translated `ประวัติการส่ง` | ✅ **5 / 5 PASS** |

---

## 3. Re-Running the E2E Suite Locally

```powershell
# Run all 23 E2E tests against http://localhost:8880
cd Web-Manage
$env:DPU_E2E_USER="<admin_username>"
$env:DPU_E2E_PASSWORD="<admin_password>"
npm run test:e2e:all

# Open the generated Playwright HTML report
npx playwright show-report
```

> [!NOTE]
> All CRUD tests use the `E2E-...` naming prefix and clean up created test records automatically before completing, leaving production/demo company data untouched.

---

## 4. Handover Sign-Off

- [x] Backend & Frontend CI checks green (`ruff`, `mypy`, `pytest`, `eslint`, `ng build`)
- [x] Full 4-Phase Playwright E2E suite green (`23/23 passed`)
- [x] Scoped frontend engineering guardrails codified in `Web-Manage/GEMINI.md`
- [x] Project documentation (`README.md`, `docs/README.md`, `docs/SENTINELVISION-ROADMAP.md`) synced to `v6.4.0`
