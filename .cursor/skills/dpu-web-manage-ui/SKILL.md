---
name: dpu-web-manage-ui
description: >-
  Redesigns or extends Web-Manage admin list pages, shared UI kit, shell
  (header/sidebar/content-layout), company/admin homes, dashboard, or
  face-management dialog using DPU teal tokens. Use when editing page-toolbar,
  pill-search, list CRUD screens, dpu-theme.css shell, or aligning UI to the
  modern-card glass standard.
---

# DPU Web-Manage UI workflow

## When to use

Admin CRUD lists, homes, dashboard polish, header/sidebar shell, face-management dialog, or shared list components — **not** face match/check-in pipeline (use `dpu-face-kiosk` for that).

## Read first

1. `.cursor/rules/dpu-web-manage.mdc`
2. Shared kit under `Web-Manage/src/app/shared/components/`
3. Tokens: `Web-Manage/src/assets/css/dpu-theme.css`
4. A recent reference page: `company-emp`, `timestamp-log`, `department`, or `user-setting`

## Standard page shape

1. `app-page-header`
2. `app-page-toolbar` — title + `app-stat-chip` + `app-pill-search` + actions
3. List panel (`modern-card glass` + `dpu-list-page.css`)
4. `app-simple-pager` after client-side filter
5. `app-empty-state` for loading / empty / no search hits
6. Modal CRUD — keep existing save/delete APIs

## Shell rules

- Keep Ynex attrs (`data-toggled`, `data-nav-layout`); do not remove mounted `app-switcher`
- Kiosk fullscreen is `dpu-kiosk-mode` — do not break those selectors
- Maps: prefer `location-map` (OSM fallback) over raw Google Maps on localhost

## Checklist

- [ ] Reuse shared kit; avoid duplicate toolbar/search CSS per page
- [ ] `ng-select` → `[appendTo]="'body'"`
- [ ] Labeled buttons: no `ti-btn-sm`
- [ ] Filter full list, then slice for pager
- [ ] Rebuild admin: `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build admin`
- [ ] Smoke-check touched routes return 200

## Out of scope unless asked

- Face WS / GPU / check-in logic
- Auto-redirect company home → dashboard (hub is intentional)
- ThemeForest demo restoration

## Reference

- [docs/CURSOR-AGENT.md](../../docs/CURSOR-AGENT.md)
- [docs/PLAN-CLEANUP-REDESIGN.md](../../docs/PLAN-CLEANUP-REDESIGN.md)
