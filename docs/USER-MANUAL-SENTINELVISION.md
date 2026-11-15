# คู่มือการใช้งานระบบ SentinelVision v4.6.0 (Unified Biometric Identity, Attendance & Smart Security Platform)

> **เวอร์ชันเอกสาร:** 4.6.0 (Sprints 1–6 Complete)  
> **Repository:** `https://github.com/chanachaipmgeng/SentinelVision.git`  
> **เทคโนโลยีหลัก:** FastAPI v4.0 (Python 3.11) + InsightFace `buffalo_l` (512-d) + PostgreSQL `pgvector` (HNSW) + Angular 20 Console & Multi-Face WebSocket Kiosk

---

## สารบัญ (Table of Contents)
1. [ภาพรวมสถาปัตยกรรมและบทบาทผู้ใช้งาน](#1-ภาพรวมสถาปัตยกรรมและบทบาทผู้ใช้งาน)
2. [การเข้าสู่ระบบ Enterprise SSO (OIDC / SAML 2.0) และ Multi-Company](#2-การเข้าสู่ระบบ-enterprise-sso-oidc--saml-20-และ-multi-company)
3. [แดชบอร์ดภาพรวมองค์กรและการลงเวลา (Executive Attendance Dashboard)](#3-แดชบอร์ดภาพรวมองค์กรและการลงเวลา-executive-attendance-dashboard)
4. [ศูนย์บัญชาการ SentinelVision (Command Center, Incident SLA & 1:N Scan)](#4-ศูนย์บัญชาการ-sentinelvision-command-center-incident-sla--1n-scan)
5. [การจัดการบัญชีเฝ้าระวัง Watchlist / Blacklist / VIP](#5-การจัดการบัญชีเฝ้าระวัง-watchlist--blacklist--vip)
6. [การควบคุมประตูอัจฉริยะ, Tailgating AI, Anti-Passback, Health Check & Wiegand/OSDP](#6-การควบคุมประตูอัจฉริยะ-tailgating-ai-anti-passback-health-check--wiegandosdp)
7. [ระบบบัตรผู้มาติดต่อด้วยใบหน้า & QR Self-Service (Visitor Face Pass)](#7-ระบบบัตรผู้มาติดต่อด้วยใบหน้า--qr-self-service-visitor-face-pass)
8. [การจัดการงานอีเวนต์ สัมมนา และค้นหาที่นั่งด้วยใบหน้า (Smart Events & Seat Lookup)](#8-การจัดการงานอีเวนต์-สัมมนา-และค้นหาที่นั่งด้วยใบหน้า-smart-events--seat-lookup)
9. [บัญชีรวมพลฉุกเฉิน Fire Alarm Fail-Safe, Batch Vector Re-Index & Edge Sync](#9-บัญชีรวมพลฉุกเฉิน-fire-alarm-fail-safe-batch-vector-re-index--edge-sync)
10. [การจัดการกะเวลาทำงาน โควตาลา OT Engine, Roster Swap, Anti-Mock GPS & PDPA](#10-การจัดการกะเวลาทำงาน-โควตาลา-ot-engine-roster-swap-anti-mock-gps--pdpa)
11. [จุดลงเวลาและตรวจสอบใบหน้าแบบกลุ่มเรียลไทม์ & Offline HMAC Sync Kiosk](#11-จุดลงเวลาและตรวจสอบใบหน้าแบบกลุ่มเรียลไทม์--offline-hmac-sync-kiosk)

---

## 1. ภาพรวมสถาปัตยกรรมและบทบาทผู้ใช้งาน

**SentinelVision v4.6.0** เป็นแพลตฟอร์มระบุตัวตนด้วยชีวมิติ (Biometric Identity), บริหารเวลาทำงาน (Enterprise HR & Time Attendance) และรักษาความปลอดภัยอัจฉริยะ (Physical Access & SOC) ที่ใช้ฐานข้อมูลเวกเตอร์ใบหน้า **512 มิติ (InsightFace `buffalo_l` + PostgreSQL `pgvector` HNSW Index)** ร่วมกันในทุกโมดูล:

| โมดูล (Module) | ความสามารถหลัก (Core Capabilities) |
| :--- | :--- |
| **Smart Time & Attendance** | ลงเวลาเข้า-ออกงานแบบกลุ่ม (Multi-face WebSocket), Walk-by & Mask/Anti-Spoof, Offline HMAC Sync (`X-DPU-Signature-256`), Anti-Mock GPS / Wi-Fi BSSID Integrity, คำนวณสาย/OT Rate Engine (`1.0x`/`1.5x`/`2.0x`/`3.0x`) และ Leave Policy |
| **SOC & Incident Lifecycle** | วงจรจัดการเหตุการณ์ (`OPEN` -> `ACKNOWLEDGED` -> `ASSIGNED` -> `CLOSED`), SLA Due Tracking, Evidence Video Clips, Bulk Ack/Close และ Alert Outbox |
| **Watchlist / Blacklist / VIP** | แจ้งเตือนบุคคลเฝ้าระวัง/บุคคลต้องห้ามทันทีที่ปรากฏหน้ากล้อง พร้อมบันทึก Incident ระดับ `CRITICAL` และต้อนรับแขก `VIP` อัตโนมัติ |
| **Smart Access Control & Edge** | โซนประตู (Entry/Exit/Bidirectional), **Tailgating AI** (`peopleCount > 1`), **Anti-Passback**, **Door Held-Open & Camera RTSP Health Check**, **Fire Alarm Fail-Safe** และ **Wiegand-26 / OSDP RS-485 Edge Bridge** |
| **Visitor Face Pass & Events** | ลงทะเบียนผู้มาติดต่อ (Walk-in, ลิงก์ Self-Service, QR Check-in/Check-out), หมดอายุอัตโนมัติ, ระบบงานอีเวนต์และการค้นหาหมายเลขที่นั่งด้วยใบหน้า |
| **Muster Roll & Vector Ops** | บัญชีรวมพลฉุกเฉิน (Live Building Occupancy + Entry/Exit + Export CSV), **Batch Vector Re-Index (512-d)** และ Edge AI Offline Manifest Sync |

---

## 2. การเข้าสู่ระบบ Enterprise SSO (OIDC / SAML 2.0) และ Multi-Company

![หน้าเข้าสู่ระบบ SentinelVision](./screenshots/01-login.png)

### ขั้นตอนการเข้าใช้งาน
1. เปิดเว็บเบราว์เซอร์ไปที่ URL ของระบบ (เช่น `http://localhost/auth/login` หรือ `http://127.0.0.1:4200/#/auth/login`)
2. กรอก **ชื่อผู้ใช้งาน (Username)** และ **รหัสผ่าน (Password)** หรือเลือกเข้าสู่ระบบผ่าน **Enterprise SSO (OIDC / SAML 2.0)**:
   - รองรับ **OIDC Authorization Code** (`/auth/sso/oidc/start`, `/auth/sso/oidc/callback`) และ **SAML 2.0 ACS** (`/auth/sso/saml/acs`) พร้อม **JIT Provisioning** สร้างบัญชีพนักงานให้อัตโนมัติตามนโยบายบริษัท (`/auth/sso/policy/{companyId}`)
   - รองรับ **RBAC Multi-Tenancy & Location Scoping** ระดับบทบาท `ADMIN_SYSTEM`, `ADMIN_COMPANY`, `SECURITY_GUARD`, และ `EMPLOYEE`
3. ระบบจะออก JWT Token (พร้อม HttpOnly Cookie และ CSRF Protection) และนำเข้าสู่หน้าแดชบอร์ดขององค์กรโดยอัตโนมัติ

---

## 3. แดชบอร์ดภาพรวมองค์กรและการลงเวลา (Executive Attendance Dashboard)

![แดชบอร์ดภาพรวมองค์กร](./screenshots/02-dashboard.png)

### ฟีเจอร์หลักบนหน้าแดชบอร์ด (`/company/dashboard`)
- **แบนเนอร์ทางลัด SentinelVision Center:** เข้าถึงศูนย์ควบคุมความปลอดภัย Watchlist, Access Control, Visitor Pass และ Smart Events ได้ในคลิกเดียว
- **ตัวชี้วัดสำคัญรายวัน (Daily KPIs):** จำนวนพนักงานทั้งหมด, สถิติเข้างานวันนี้ (ตรงเวลา, มาสาย, ขาดงาน, ลางาน), รายการรออนุมัติ (Pending Approvals) และสถานะความพร้อมของระบบ
- **กราฟแนวโน้มการเข้างาน 7 วันย้อนหลัง:** แสดงสัดส่วนการเข้างานตรงเวลาและมาสายรายวันแบบโต้ตอบได้

---

## 4. ศูนย์บัญชาการ SentinelVision (Command Center, Incident SLA & 1:N Scan)

![ศูนย์บัญชาการ SentinelVision Command Center](./screenshots/03-sentinel-command.png)

### การใช้งานหน้า Command & 1:N Scan (`/company/sentinel-center`)
1. **แถบ KPI ด้านบน (6 ตัวชี้วัด):** แสดงจำนวนรายการใน Blacklist/Watchlist, VIP, ผู้มาติดต่อ (Active Visitors), โซนประตู (Access Zones), งานอีเวนต์ และจำนวนคนในอาคารขณะนี้ (In-Building Muster)
2. **Unified 1:N Biometric Verification & Gate Simulator (ฝั่งซ้าย):**
   - เลือก **โซนประตู/กล้อง (Access Zone)** หรือ **งานอีเวนต์ (Event)** ที่ต้องการจำลองการสแกน
   - อัปโหลดภาพใบหน้าเพื่อทดสอบการค้นหาแบบ **Unified 1:N** (ค้นหาพร้อมกันทั้งฐานข้อมูลพนักงานและฐานข้อมูล Sentinel Identities)
   - แสดงผลการตัดสินใจทันที (`GRANT`, `DENY`, `ALERT_WATCHLIST`, `VIP_WELCOME`) พร้อมค่าความเหมือน (Cosine Similarity %) และหมายเลขที่นั่ง
3. **Real-Time Security & Incident Lifecycle Feed (ฝั่งขวา):**
   - ติดตามวงจรเหตุการณ์ `OPEN` -> `ACKNOWLEDGED` -> `ASSIGNED` -> `CLOSED` พร้อมตัวนับเวลา **SLA Due**
   - รองรับปุ่ม **`Ack`**, **`Assign`**, **`Close`**, การจัดการแบบกลุ่ม (**Bulk Ack / Bulk Close**), และการเปิดดู **Evidence Video Clip** จากกล้องที่เชื่อมโยง

---

## 5. การจัดการบัญชีเฝ้าระวัง Watchlist / Blacklist / VIP

![การจัดการบัญชีเฝ้าระวัง Watchlist / Blacklist / VIP](./screenshots/04-sentinel-watchlist.png)

### การเพิ่มและจัดการรายชื่อ (แท็บ `Watchlist / Blacklist & VIP`)
1. ในฟอร์ม **ลงทะเบียน Watchlist / Blacklist / VIP** ด้านซ้าย เลือกประเภทบัญชี:
   - `BLACKLIST`: บุคคลต้องห้าม/อดีตพนักงานที่ถูกเพิกถอนสิทธิ์ (แจ้งเตือนระดับ `CRITICAL` + ปฏิเสธการเข้าพื้นที่)
   - `WATCHLIST`: บุคคลเฝ้าระวังพิเศษ (แจ้งเตือนเจ้าหน้าที่รักษาความปลอดภัยทันทีที่พบหน้ากล้อง)
   - `VIP`: แขกผู้บริหาร/ลูกค้าคนสำคัญ (แจ้งเตือนทีมต้อนรับพร้อมข้อความต้อนรับบนจอ Kiosk)
2. กรอกชื่อ-นามสกุล, รหัสอ้างอิง, องค์กร และหมายเหตุการแจ้งเตือน (Alert Reason) แล้วแนบภาพถ่ายใบหน้าเพื่อสกัดเวกเตอร์ 512-d ลง `pgvector`
3. ในตารางด้านขวา สามารถกรองดูตามหมวดหมู่ อัปเดตใบหน้าใหม่ หรือลบรายการได้ทันที

---

## 6. การควบคุมประตูอัจฉริยะ, Tailgating AI, Anti-Passback, Health Check & Wiegand/OSDP

![การควบคุมประตูและโซนพื้นที่อัจฉริยะ](./screenshots/05-sentinel-access.png)

### การตั้งค่าโซนประตูและการตรวจสอบสถานะ (แท็บ `Access Control & โซนประตู`)
1. **การสร้างโซนควบคุมประตู (Create Access Zone):**
   - กำหนด **ชื่อโซน/ประตู**, **รหัสโซน**, **ทิศทาง (`ENTRY` / `EXIT` / `BIDIRECTIONAL`)**, ช่วงเวลาเปิด-ปิด (Schedule) และสิทธิ์กลุ่มบุคคล (`EMPLOYEE`, `VIP`, `VISITOR`)
   - เปิดใช้ **2FA (Face + PIN/TOTP)** สำหรับโซนความมั่นคงสูง
   - เปิดใช้ **Anti-Passback** (`antiPassbackEnabled`, `antiPassbackMinutes`) เพื่อป้องกันการใช้สิทธิ์เข้าซ้ำโดยไม่ผ่านประตูออกก่อน และตรวจจับ **Tailgating AI** (`peopleCount > 1` -> `TAILGATING_DETECTED`) ผ่าน `POST /sentinel/company/{companyId}/zones/{zoneId}/evaluate-access`
   - เลือก **Edge Hardware Protocol** (`WEBHOOK`, `WIEGAND`, `OSDP` RS-485 พร้อม `osdpAddress` 0–126 และ `edgeBridgeUrl`) สำหรับสั่งปลดล็อกผ่าน `POST /sentinel/company/{companyId}/zones/{zoneId}/edge-unlock`
2. **Health Check & Fail-Safe Controls (ด้านขวาบน):**
   - กดปุ่ม **`Health Check`** (`POST /sentinel/company/{companyId}/health-check`) เพื่อตรวจสอบ **Camera RTSP Offline** (ไม่มี heartbeat เกิน 3 นาที) และ **Door Held-Open** (`doorOpenSince` เกิน `doorHeldMaxSeconds`) พร้อมบันทึก Incident และส่ง Notification Outbox อัตโนมัติ
   - กดปุ่ม **`Fire Alarm: ปลดล็อกทุกประตู`** (`POST /fire-alarm`) เพื่อสั่งปลดล็อกประตูฉุกเฉินพร้อมกันทุกโซน และ **`รีเซ็ต Alarm`** (`POST /fire-alarm/reset`) เมื่อเหตุการณ์คลี่คลาย

---

## 7. ระบบบัตรผู้มาติดต่อด้วยใบหน้า & QR Self-Service (Visitor Face Pass)

![ระบบบัตรผู้มาติดต่อด้วยใบหน้า Visitor Face Pass](./screenshots/06-sentinel-visitors.png)

### การออกบัตรผู้มาติดต่อ (แท็บ `ผู้มาติดต่อ (Visitor Pass)`)
1. **ลิงก์ลงทะเบียนล่วงหน้าด้วยตนเอง (Self-Service Pre-Registration Link):** คัดลอก URL ส่งให้ผู้มาติดต่อลงทะเบียนชื่อและอัปโหลดใบหน้าผ่านสมาร์ทโฟนล่วงหน้า พร้อมรับรหัส/QR Check-in
2. **การลงทะเบียนหน้าเคาน์เตอร์ (Walk-in Visitor Registration):** กรอกชื่อ-นามสกุล, บริษัท, พนักงานผู้รับรอง และระยะเวลาอนุญาต (เช่น `8 ชั่วโมง`) พร้อมภาพถ่ายใบหน้า
3. **Check-out & PDPA Auto-Expiry:** รองรับการกด **Check-out** เมื่อผู้มาติดต่อออกจากอาคาร และเมื่อครบกำหนดเวลา (`expiresAt`) ระบบจะเปลี่ยนสถานะเป็น `EXPIRED` โดยอัตโนมัติ

---

## 8. การจัดการงานอีเวนต์ สัมมนา และค้นหาที่นั่งด้วยใบหน้า (Smart Events & Seat Lookup)

![การจัดการงานอีเวนต์และค้นหาที่นั่งด้วยใบหน้า](./screenshots/07-sentinel-events.png)

### ขั้นตอนการจัดงานและลงทะเบียนผู้ร่วมงาน (แท็บ `งานอีเวนต์ & สัมมนา`)
1. **สร้างงานอีเวนต์ใหม่:** ระบุชื่องาน, สถานที่, โซนประตูที่เชื่อมโยง, จำนวนที่นั่งสูงสุด และช่วงวันเวลาจัดงาน
2. **ลงทะเบียนผู้เข้าร่วมงาน + กำหนดที่นั่ง:** เลือกงานอีเวนต์ กรอกชื่อ-องค์กร และหมายเลขที่นั่ง/โซน (เช่น `VIP-A01`) พร้อมรูปใบหน้า
3. **การสแกนหน้างาน:** เมื่อผู้ร่วมงานสแกนใบหน้าที่จุด Kiosk ระบบจะแสดงข้อความต้อนรับพร้อมหมายเลขที่นั่งทันที และอัปเดตยอด **Checked-In / Registered** แบบเรียลไทม์

---

## 9. บัญชีรวมพลฉุกเฉิน Fire Alarm Fail-Safe, Batch Vector Re-Index & Edge Sync

![บัญชีรวมพลฉุกเฉินและ Batch Vector Re-Index](./screenshots/08-sentinel-muster.png)

### เครื่องมือจัดการภาวะฉุกเฉินและเวกเตอร์ AI (แท็บ `เช็คยอดคนในอาคาร & Edge AI`)
1. **Edge AI Offline Sync & Batch Vector Re-Index (ฝั่งซ้าย):**
   - ดูรุ่น Manifest, จำนวน Employee Vectors และ Sentinel Vectors ที่พร้อมซิงค์ไปยัง Edge Box
   - กด **`อัปเดต Edge Manifest ล่าสุด`** เพื่อดึง Manifest ล่าสุด
   - กด **`Batch Vector Re-Index (512-d)`** (`POST /reindex-vectors`) เพื่อ L2-normalize และอัปเดต `modelVersion` ของเวกเตอร์ใบหน้าทั้งหมดแบบ batch พร้อมแสดงจำนวนที่ประมวลผลและสถานะ
2. **Live Building Occupancy & Emergency Muster Roll (ฝั่งขวา):**
   - แสดงรายชื่อบุคคลที่อยู่ในอาคารวันนี้ (รวม `PRESENT` จาก `attendance_daily`, ผู้เช็คอินค้าง และผู้มาติดต่อ)
   - กด **`ปลอดภัยแล้ว`** เพื่อเช็คชื่อผู้มาถึงจุดรวมพล, กด **`Fire Alarm`** เพื่อเปิดโหมดอพยพฉุกเฉิน, และกด **`Export CSV`** เพื่อนำส่งรายงานรวมพล

---

## 10. การจัดการกะเวลาทำงาน โควตาลา OT Engine, Roster Swap, Anti-Mock GPS & PDPA

![การจัดการกะเวลาทำงาน วันหยุด และการลา](./screenshots/09-hr-schedule.png)

### การบริหารจัดการงานบุคคล (`/company/hr-schedule`)
- **กะเวลาทำงาน (Work Shifts & Roster Swap):** กำหนดเวลาเข้า-ออก, นาทีผ่อนผันสาย (Grace Minutes), ตารางกะรายวัน (**Shift Roster**) และระบบขอสลับกะระหว่างพนักงาน (**Shift Swap Approval**)
- **Leave Policy & OT Rate Engine:** คำนวณสิทธิ์วันลาตามอายุงาน, ยอดยกมา (Carry-over), การลาแบบครึ่งวัน/รายชั่วโมง, แนบใบรับรองแพทย์ และคำนวณ OT อัตโนมัติตามอัตรา `1.0x` / `1.5x` / `2.0x` / `3.0x`
- **Multi-Level Approval & Delegation:** อนุมัติใบลา/OT/Regularization หลายลำดับขั้นพร้อมตั้งค่าผู้รับมอบอำนาจแทนชั่วคราว
- **Anti-Mock GPS & Wi-Fi BSSID Integrity:** ตรวจสอบความถูกต้องของพิกัด GPS และ Wi-Fi BSSID สำหรับการลงเวลานอกสถานที่
- **PDPA Biometric Purge (`/company/enroll-face`):** ตรวจสอบจำนวนเวกเตอร์ใบหน้าและลบข้อมูลชีวมิติทันทีเมื่อพนักงานลาออกหรือถอนความยินยอม

---

## 11. จุดลงเวลาและตรวจสอบใบหน้าแบบกลุ่มเรียลไทม์ & Offline HMAC Sync Kiosk

![จุดลงเวลาและตรวจสอบใบหน้าแบบกลุ่ม Multi-Face Kiosk](./screenshots/10-face-kiosk.png)

### การใช้งานหน้าจอ Kiosk (`/company/scan/:stationMode` และ `/company/timestamp-face`)
1. รองรับโหมดการทำงานเฉพาะทาง 6 รูปแบบ (`ATTENDANCE`, `ACCESS_CONTROL`, `WATCHLIST_MONITOR`, `VISITOR_CHECKIN`, `EVENT_CHECKIN`, `UNIFIED_HYBRID`)
2. เชื่อมต่อผ่าน **WebSocket (`/face/ws/kiosk`)** ความหน่วงต่ำ พร้อมวาดกรอบใบหน้าแบบกลุ่ม (Multi-Person HUD Overlay), Walk-by Detection, และ Anti-Spoof / Mask Check
3. **Offline-First Kiosk HMAC Sync (`BL-12`):** เมื่อเครือข่ายขาดหาย เครื่อง Kiosk จะแคชเวกเตอร์จาก Edge Sync Manifest และบันทึกการสแกนลง Local Queue เมื่อกลับมาออนไลน์จะส่งซิงค์ผ่าน `POST /timestamp/company/{companyId}/offline-sync` พร้อมลายเซ็น **`X-DPU-Signature-256`** (HMAC-SHA256) และ `X-DPU-Timestamp` ป้องกันการปลอมแปลงและ Replay Attack


## 12. ฟีเจอร์ระดับ Enterprise (Phases 1–10)

ส่วนเสริมระดับองค์กรที่เพิ่มเข้ามาใน SentinelVision v4.0 ครอบคลุมการตรวจสอบความปลอดภัย การเชื่อมต่อระบบบุคคล การจัดการกล้องและวิดีโอ และความต่อเนื่องทางธุรกิจ:

1. **Audit Log Integrity Verification (`/company/audit-log`)**
   - กดปุ่ม **Verify Integrity** เพื่อตรวจสอบความถูกต้องของ Hash-chain (`audit_log`) แบบเรียลไทม์ ระบบรองรับทั้งเรกคอร์ดใหม่และเรกคอร์ดย้อนหลัง (Legacy fallback) โดยแสดงสถานะ `VERIFIED` พร้อมจำนวนรายการที่ตรวจสอบแล้ว
2. **HRIS / Identity Connectors & SCIM 2.0**
   - เชื่อมต่อระบบ HRIS ภายนอก (Workday, SAP SuccessFactors, BambooHR) และรองรับโปรโตคอล SCIM 2.0 สำหรับซิงค์ข้อมูลพนักงานเข้าสู่ `CompanyEmployee` / `Member` อัตโนมัติ พร้อมปิดบังข้อมูลส่วนบุคคล (PDPA masking) สำหรับเลขบัตรประชาชนและพาสปอร์ต
3. **ONVIF Camera Discovery, PTZ & PDPA Privacy Mask (`/company/cameras`)**
   - ใช้ปุ่ม **Discover ONVIF** เพื่อค้นหากล้อง IP ในเครือข่ายอัตโนมัติ ควบคุมทิศทางกล้อง (PTZ) และกำหนดกรอบ **PDPA Privacy Mask** (Blur/Blackout) บนพื้นที่อ่อนไหวของภาพกล้อง
4. **NVR AI-Marker Timeline Scrubber**
   - ในหน้าดูวิดีโอบันทึกย้อนหลัง (NVR Playback) แถบไทม์ไลน์จะแสดงเครื่องหมายเหตุการณ์ AI (Incident Markers) ตามเวลาที่เกิดเหตุ เพื่อให้ผู้ดูแลระบบกดข้ามไปยังช่วงเวลาสำคัญได้ทันที
5. **Visitor Invite, ID OCR & Guest Self-Check-in Portal**
   - สร้างลิงก์/QR เชิญผู้มาติดต่อล่วงหน้า รองรับการสแกนบัตรประชาชนหรือพาสปอร์ตด้วย OCR (บันทึกเฉพาะข้อมูลที่ปิดบังตาม PDPA) และเปิดให้ผู้มาติดต่อลงทะเบียนด้วยตนเองผ่าน Guest Portal
6. **Breakout Room Capacity Check-in (`/company/sentinel-center` — แท็บ Events)**
   - กำหนดห้องย่อย (Breakout Rooms) ภายใต้ Event พร้อมเพดานความจุสูงสุด (Capacity) และติดตามยอดผู้เข้าร่วมแบบเรียลไทม์เมื่อสแกนเช็กอินเข้าห้องย่อย
7. **Multi-Region Disaster Recovery (DR) Replication**
   - ติดตามสถานะการจำลองข้อมูลข้ามภูมิภาคผ่าน Multi-Region DR Strip โดยทุกคำขอ Replication (`/sentinel/dr/replicate`) ผ่านการยืนยันตัวตนด้วยลายเซ็น HMAC-SHA256 (`X-Sentinel-DR-Sig`) และป้องกันข้อมูลซ้ำด้วย Redis Idempotency Keys
