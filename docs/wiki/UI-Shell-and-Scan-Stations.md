# UI Shell, Dual-Rail Sidebar & Modular Scan Stations

[← กลับหน้าหลัก Wiki](Home.md)

## 1. VaultX Obsidian Glass Design System

- พื้นผิวการ์ดหลักใช้ utility `card-surface` (`#070d14` obsidian base พร้อมขอบบนไล่เฉด cyan/slate) และสลับ Light/Dark theme ผ่าน semantic tokens (`#f1f5f9` / `#cbd5e1` / `#94a3b8`)
- เอฟเฟกต์แอมเบียนท์ (`ConstellationComponent`, `HorizonGlowComponent`) จำกัดเฉพาะหน้า Login / Landing / Kiosk idle เพื่อไม่ให้รบกวนการอ่านตารางข้อมูลใน Console
- มี directive เสริมประสบการณ์ผู้ใช้: View Transitions, `Spotlight` / `Magnetic`, `AudioSfxService`, และ Lightbox

## 2. Two-Column Dual-Rail Sidebar (`app-sidebar.sv-dual-sidebar`)

- **Desktop (`>= 992px`):** กว้างรวม `17.5rem` (`4.5rem` Column 1 Module Rail + `13rem` Column 2 Sub-screens Panel) พร้อมซิงค์ระยะ `.app-header`, `.content`, และ `.footer` ใน `Web-Manage/src/assets/css/dpu-theme.css`
- **Tablet / Mobile (`< 992px`):**
  - `SidebarComponent.ngOnInit()` ตั้งค่า `data-toggled="close"` เมื่อความกว้าง `< 992px`
  - ภายใต้ `@media (max-width: 991.98px)` `.app-sidebar` จะถูกซ่อนแบบ off-canvas (`transform: translateX(-100%)`, `visibility: hidden`, `pointer-events: none`) เมื่อ `html:not([data-toggled="open"])` เพื่อไม่ให้บัง Header หรือเนื้อหา
  - กดปุ่มแฮมเบอร์เกอร์ใน `.app-header` (`HeaderComponent.toggleSidebar()`, ใช้เกณฑ์ `window.innerWidth < 992`) เพื่อเปิด/ปิด Drawer และกดพื้นที่ `#responsive-overlay` เพื่อปิด
- **Module Filtering & Navigation:** Column 1 (`moduleGroups`) กรองตาม `enabledModules` + สิทธิ์ RBAC และเมื่อคลิกเปลี่ยนโมดูล (`selectModule`) จะเลือกหน้าจัดการที่ไม่ใช่ `/company/scan/` เป็นค่าเริ่มต้น

## 3. Modular Kiosk Scan Stations (`/company/scan/:stationMode`)

รองรับ 6 โหมดสถานีสแกนภายใต้ `.dpu-kiosk` (ผูก `[attr.data-station-mode]="stationMode"` เพื่อเปลี่ยน `--kiosk-accent`):

| `stationMode` | สีธีม Accent | การใช้งานหลัก |
|---|---|---|
| `ATTENDANCE` | Cyan | ลงเวลาเข้า-ออกงานพนักงาน (`AUTO` / `CHECK_IN` / `BREAK_OUT` / `BREAK_IN` / `CHECK_OUT`) |
| `ACCESS_CONTROL` | Sky | ตรวจสอบสิทธิ์ผ่านประตูตามโซน (`SentinelAccessZone`) และปลดล็อก Relay |
| `WATCHLIST_MONITOR` | Rose | เฝ้าระวังบุคคลต้องห้าม (`BLACKLIST` / `POI`) พร้อม Silent Alarm |
| `VISITOR_CHECKIN` | Violet | ลงทะเบียนและตรวจสอบผู้มาติดต่อชั่วคราว (`VISITOR`) |
| `EVENT_CHECKIN` | Amber | เช็คอินงานสัมมนา/อีเวนต์ พร้อมแสดงเลขที่นั่ง (`seatNumber`) |
| `UNIFIED_HYBRID` | Teal | ตรวจจับแบบรวมศูนย์ทุกประเภทในหน้าเดียว |
