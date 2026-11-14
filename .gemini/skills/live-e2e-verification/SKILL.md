---
name: live-e2e-verification
description: End-to-end live browser + real-API verification playbook for SentinelVision across all 9 modules, Kiosk scan modes, and responsive viewports.
---

# Live E2E Verification Playbook

## Pre-Flight
1. Confirm containers healthy (`sentinel-api`, `sentinel-admin`, `sentinel-nginx`, `sentinel-db`).
2. Open `http://localhost:8880/?v=<tag>#/` with cache-busting query string.
3. Log in via the UI as Company Admin (`admin`).

## Verification Matrix (0 HTTP >= 400, 0 pageerror/CSP warnings)
1. **Command**: `/company/dashboard` (KPI drill-downs), `/company/scan-hub` (Copy Direct URL).
2. **Core Org**: `/company/company-info` (Timezone/Cutoff/DateFormat), `/company/department` & `/company/position` (`employeeCount`, Export CSV, 409 delete guard), `/company/company-emp` (Quick filters + Create modal).
3. **Attendance**: `/company/timestamp-log` (Manual punch edit), `/company/approval-inbox` (Location filter + multi-select Bulk Approve/Reject), `/company/self-service` (Leave Quota cards).
4. **Access Control**: `/company/access-control/zones` (Door schedule inputs + Test Relay ms), `/company/access-control/logs` (Export CSV).
5. **Watchlist**: `/company/watchlist/identities` (Expiration date), `/company/watchlist/incidents` (Export CSV + Resolution Note close).
6. **Visitor & Events**: `/company/visitors/passes` (Copy Pre-Reg Link + Print Badge), `/company/visitors/muster-roll` (Check-off Safe + Export CSV), `/company/events/checkins` (Export Dwell CSV).
7. **CCTV**: `/company/cameras` (Ping/Snapshot/ROI), `/company/live-wall` (Save Preset + Snapshot), `/company/playback` (Event Markers), `/company/e-map` (Quick Live/Door links).
8. **Governance**: `/company/devices` (Copy Kiosk URL + Refresh Config), `/company/notification-center` (Mark All Read + Delivery History), `/company/settings/ai` (Search Settings + Reset to Default + Unsaved Changes Guard).
9. **Responsive Check**: Test `1440x900` (desktop dual-rail) and `700x900` (mobile drawer).
