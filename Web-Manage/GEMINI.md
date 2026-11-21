# SentinelVision Frontend (`Web-Manage/`) — Scoped UX/UI & Browser Invariants

## 1. Modern Browser & Form Control Guardrails
- **Chrome 135+ `<select>` Single-Chevron Invariant:** Always pair `appearance: none !important; -webkit-appearance: none !important; -moz-appearance: none !important;` with `select::picker-icon { display: none !important; }` and `white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;` so native `<select>` controls never render duplicate arrows (`▼` + `⌄`) or wrap option labels onto multiple lines.
- **Settings & Multi-Column Form Grid Widths:** Inside narrow right-hand panels (e.g., Settings Hub with dual-rail sidebar + settings rail), prefer 2-column form grids (`grid-cols-1 md:grid-cols-2`) over 4-column grids so dropdown labels never crush or wrap; always wrap data tables in `overflow-x-auto max-w-full`.
- **Global FAB Non-Occlusion Clearance:** Maintain `padding-bottom: 5.5rem !important;` on `.main-content` and add right-side clearance (`lg:pr-28`) on bottom/right-aligned filter bars so the fixed `.sv-ask-fab` never covers dropdowns, inputs, or table row actions.

## 2. Visual Polish, Contrast & Typography Invariants
- **Above-the-Fold Hero Immediate Render (LCP & Contrast):** Never gate above-the-fold hero headlines, lead paragraphs, or primary CTAs behind `opacity: 0` scroll-reveal directives (`dpuReveal`). Render them immediately at full opacity using WCAG AA contrast tokens (`#ffffff` / `#cbd5e1` on obsidian dark backgrounds).
- **Thai Typography Completion State:** Never apply `text-decoration: line-through` to completed Thai text (it collides with Thai vowels and tone marks). Indicate completion using a green checkmark icon/badge and softened opacity (`opacity: 0.82`).
- **Icon Font Validation:** Verify every icon class exists in the bundled icon sets before use (`ri-*` RemixIcon, `bx-*` Boxicons — e.g., use `ri-bank-card-2-line` instead of nonexistent `ri-rfid-line`, and `bx-check-shield` instead of nonexistent `bx-shield-check`).
- **Exact Active Highlight in Sub-Navigation Rails:** Bind explicit `[class.is-active]="active?.id === s.id"` (or `[routerLinkActiveOptions]="{ exact: true }"`) on vertical settings/sub-nav rails so inactive items never retain stale active highlights.

## 3. Telemetry Truthfulness & Role-Gated Data Loading
- **Zero Fake Numeric Fallbacks:** Never hardcode synthetic fallback numbers in KPI getters (e.g., `Math.max(28, ...)`). Default missing counts to `0` and add the real aggregate field to the backend endpoint.
- **Dynamic Health Status & Offline Hardware Guards:**
  - Never hardcode green "Healthy / เสถียรภาพสูง" labels on metric cards; derive label, icon, and color from actual score thresholds (`>= 90` emerald, `>= 70` amber, `< 70` rose).
  - For disconnected/offline devices or cameras, render `—` in latency/telemetry cells (never `ปกติ`) and disable interactive hardware controls (e.g., ONVIF PTZ buttons) with `[disabled]="cam.status !== 'online'"`.
- **Admin & System-Admin Guard on Employee-Only Endpoints:** Before calling employee-scoped endpoints on init (e.g., `/employees/company/{companyId}/member/{memberId}` on Self-Service), wait for `permissions.load(companyId)` and check `permissions.isCompanyAdmin() || permissions.isSystemAdmin()` to avoid spurious HTTP 404 console errors.
- **Timer Cleanup:** Always store `setInterval` handles as `ReturnType<typeof setInterval>` and clear them in `ngOnDestroy()`.

## 4. Performance, Theme Parity & Reusable Wrappers
- **Root Layout Change Detection:** Keep `ContentLayoutComponent` on `ChangeDetectionStrategy.Default` with **zero** `setInterval` change-detection polling loops. Never switch `ContentLayoutComponent` to `OnPush` without explicit zone triggers (it stalls async child route updates under `<router-outlet>`).
- **Porcelain Light & VaultX Obsidian Parity:** Never hardcode dark-only surfaces (`bg-[#04080f]`, `text-slate-100`) on Command/Management screens without matching `:root:not(.dark)` / `html[data-theme-mode="light"]` Porcelain Light overrides.
- **Command UI Wrappers:** Reuse `CommandTopbarComponent`, `MetricRibbonComponent`, and `SurfaceModalComponent` (`src/app/shared/components/command-ui/`) instead of duplicating header/KPI/modal markup. Keep Initial Bundle `< 2.50 MB` by avoiding unused `MaterialModuleModule`, hidden `<app-switcher>`, or legacy Material themes (`indigo-pink.css`).

## 5. Role Separation, Task-Oriented Sidebar & Side-Drawer UX
- **System Admin vs. Company Admin Scope:** Keep platform-wide telemetry/config (`/admin/infrastructure`, `/admin/system-setting`) strictly under System Admin Console; exclude `SYSTEM_ADMIN` from tenant RBAC (`/company/settings/rbac`); soft-hide employee-only routes (`self-service`, `mobile-checkin`) for `SYSTEM_ADMIN`; display the System Admin Context Banner (`← กลับ System Admin Console`) when inspecting a company.
- **Task-Oriented Sidebar Sub-Groups:** Group Column 2 sub-items using `groupLabel` (`sidebar.group.*` → `.sv-subpanel__group`) ordered by real workflow (**Daily Operations → Policy/Configuration → Live Kiosk/Terminals**) with TH/EN i18n parity.
- **Action Density & `<app-side-drawer>` Decluttering:** Keep primary page toolbars focused (collapse secondary utilities like CSV import, ONVIF discovery, and settings links into a `เครื่องมือ ▾` dropdown). Cap list/table row actions to **2 primary buttons** and move secondary controls/forms (e.g., ONVIF PTZ, PDPA Mask, create/import forms) into `<app-side-drawer>`.
