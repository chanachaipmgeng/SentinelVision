---
name: sentinel-e2e-verify
description: >-
  Build Web-Manage, sync static assets into the running sentinel-admin Docker container,
  and run the Playwright E2E suite against http://localhost:8880 with SentinelVision-specific
  selector, dialog, and route-animation guardrails. Use when verifying frontend changes,
  debugging Playwright E2E failures, or preparing a Web-Manage release.
---

# SentinelVision Web-Manage Build, Sync & Playwright E2E Runbook

## 1. Lint & Build (Wait for Exit 0 First)
```powershell
cd Web-Manage; npm run lint; if ($?) { npm run build }
```
- Confirm **0 ESLint errors** and Initial Bundle **`< 2.50 MB`** (0 budget warnings).
- Never run `docker cp` or Playwright in parallel with an active `ng build`.

## 2. Fast Static Sync to `sentinel-admin`
```powershell
docker cp Web-Manage/dist/preview/browser/. sentinel-admin:/usr/share/nginx/html/; if ($?) { docker exec sentinel-admin nginx -s reload }
```
- Gateway runs on **`http://localhost:8880`** (not `:80`). If `curl.exe http://localhost:8880/health` returns empty reply `(52)` after restarting `sentinel-api-gpu`, restart `sentinel-nginx`.

## 3. Run Playwright E2E Suite
```powershell
cd Web-Manage; $env:DPU_E2E_USER="<user>"; $env:DPU_E2E_PASSWORD="<pass>"; npm run test:e2e:all
```
- Never commit test credentials to any file.

## 4. Playwright Guardrails (Known Pitfalls)
- **Route Animation Strict-Mode:** Scope locators to component hosts (e.g., `app-fleet-health table`, `app-company-cameras app-page-header`) so leaving `.ng-animating` route elements do not trigger strict-mode violations.
- **Welcome Wizard:** Always call `dismissWelcomeWizard(page)` on `/company/dashboard` in fresh browser contexts.
- **Dialogs:** Use `confirmSwal(page)` for SweetAlert (`department`, `position`, `holidays`), and `page.on('dialog', d => d.accept())` for native `window.confirm` (`parking`, `rfid-cards`).
- **Exact Close Labels:** Use `{ name: 'ปิด', exact: true }` (substring `'ปิด'` also matches `'เปิดการค้นหา'`).
- **Sidebar Module Assertions:** Direct-navigating to a module disabled in the test company's `enabledModules` (e.g., `CCTV` on `DPUATT`) keeps the sidebar on `COMMAND` — assert `.sv-subpanel__group` on enabled modules such as `ATTENDANCE` or `GOVERNANCE`.
