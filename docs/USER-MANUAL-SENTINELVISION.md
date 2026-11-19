# คู่มือการใช้งานระบบ SentinelVision v6.0.1 (Unified Biometric Identity, Attendance & Smart Security Platform)

> **เวอร์ชันเอกสาร:** 6.0.1 (Enterprise Phases 1–10, GPU-First `api-gpu`, Edge AI & Copilot)  
> **Repository:** `https://github.com/chanachaipmgeng/SentinelVision.git`  
> **เทคโนโลยีหลัก:** FastAPI v4.0 (Python 3.11, CUDA 12.8 GPU-First) + InsightFace `buffalo_l` (512-d) + PostgreSQL `pgvector` (HNSW) + Angular Console & Multi-Face WebSocket Kiosk

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
12. [ฟีเจอร์ระดับ Enterprise (Phases 1–10)](#12-ฟีเจอร์ระดับ-enterprise-phases-110)
13. [การจัดการองค์กร แผนก ตำแหน่ง พนักงาน และสถานที่ตั้ง (`/company/company-*`)](#13-การจัดการองค์กร-แผนก-ตำแหน่ง-พนักงาน-และสถานที่ตั้ง-companycompany-)
14. [การลงเวลา การอนุมัติ รายงาน และ Employee Self-Service (ESS)](#14-การลงเวลา-การอนุมัติ-รายงาน-และ-employee-self-service-ess)
15. [หน้าจอเฉพาะทาง Access / Watchlist / Visitors / Events & Scan Hub](#15-หน้าจอเฉพาะทาง-access--watchlist--visitors--events--scan-hub)
16. [ระบบกล้องวงจรปิด Live Wall, NVR Playback, E-Map, Face Monitor & Presence](#16-ระบบกล้องวงจรปิด-live-wall-nvr-playback-e-map-face-monitor--presence)
17. [ความปลอดภัย Audit Log, อุปกรณ์ Kiosk, การแจ้งเตือน, AI Copilot & System Admin](#17-ความปลอดภัย-audit-log-อุปกรณ์-kiosk-การแจ้งเตือน-ai-copilot--system-admin)

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

![หน้าจอเข้าสู่ระบบ SentinelVision](images/manual/01-login.png)

## 3. แดชบอร์ดภาพรวมองค์กรและการลงเวลา (Executive Attendance Dashboard)

![แดชบอร์ดภาพรวมองค์กร](./screenshots/02-dashboard.png)

### สถาปัตยกรรม Bento Grid และฟีเจอร์หลักบนหน้าแดชบอร์ด (`/company/dashboard`)
หน้าแดชบอร์ดได้รับการออกแบบใหม่ด้วย **Bento Grid Architecture** บนมาตรฐาน VaultX Obsidian Glass ที่จัดสรรพื้นที่แสดงผลอย่างสมดุลแบบ 12 คอลัมน์:
- **แถบ 4 Bento KPI Metric Tiles ด้านบน:**
  - *ลงเวลาวันนี้ (Punches today)* [โทนสี Cyan]: จำนวนบันทึกการลงเวลาเข้า-ออกงานทั้งหมดในรอบวัน พร้อมลิงก์ไปยังหน้า Timestamp Log
  - *ในพื้นที่วันนี้ (In area today)* [โทนสี Emerald]: จำนวนการลงเวลาที่อยู่ในกรอบรัศมีพิกัด GPS/Geofence ขององค์กร
  - *นอกพื้นที่วันนี้ (Out of area today)* [โทนสี Rose]: จำนวนการลงเวลาที่อยู่นอกพื้นที่พิกัดอนุญาต พร้อมตัวบ่งชี้สถานะแจ้งเตือน
  - *รอการอนุมัติ (Pending approval)* [โทนสี Amber]: จำนวนคำขอลา OT หรือขอแก้ไขเวลาที่ค้างอยู่ในคิวอนุมัติ
- **Bento Card การวิเคราะห์แนวโน้ม 7 วันย้อนหลัง (7-day Velocity Trend - Span 8, `cyan`):** แสดงกราฟแท่งเปรียบเทียบปริมาณและสัดส่วนการลงเวลาตรงเวลาและมาสายในรอบสัปดาห์ พร้อมยอดรวม Week Total
- **Bento Card สัดส่วนการลงเวลาวันนี้ (Today Mix Ratio - Span 4, `sky`):** กราฟโดนัทจำแนกสถานะการลงเวลาในพื้นที่เทียบกับนอกพื้นที่
- **Bento Card แผนที่พิกัดจุดลงเวลา (Today Punch Map - Span 7, `emerald`):** แผนที่ดาวเทียมแสดงพิกัด GPS ตำแหน่งที่พนักงานสแกนลงเวลาจริงเทียบกับพื้นที่สำนักงาน
- **Bento Card สตรีมตรวจจับใบหน้าสด (Live Biometric Sightings Feed - Span 5, `rose`):** แสดงภาพถ่ายใบหน้า เวลา ชื่อพนักงาน ตำแหน่ง และแท็กสถานะแบบ Real-time พร้อมจุดกระพริบ Pulse แสดงสถานะ Streaming สด

---

![แดชบอร์ดภาพรวมองค์กรและการลงเวลา](images/manual/02-dashboard.png)

## 4. ศูนย์บัญชาการ SentinelVision (Command Center, Incident SLA & 1:N Scan)

![ศูนย์บัญชาการ SentinelVision Command Center](./screenshots/03-sentinel-command.png)

### การใช้งานหน้า Command & 1:N Scan (`/company/sentinel-center`)
1. **แถบ KPI ด้านบน (6 ตัวชี้วัด):** แสดงจำนวนรายการใน Blacklist/Watchlist, VIP, ผู้มาติดต่อ (Active Visitors), โซนประตู (Access Zones), งานอีเวนต์ และจำนวนคนในอาคารขณะนี้ (In-Building Muster)
2. **Unified 1:N Biometric Verification & Gate Simulator (ฝั่งซ้าย):**
   - เลือก **โซนประตู/กล้อง (Access Zone)** หรือ **งานอีเวนต์ (Event)** ที่ต้องการจำลองการสแกน
   - อัปโหลดภาพใบหน้าเพื่อทดสอบการค้นหาแบบ **Unified 1:N** (ค้นหาพร้อมกันทั้งฐานข้อมูลพนักงานและฐานข้อมูล Sentinel Identities)
   - แสดงผลการตัดสินใจทันที (`GRANT`, `DENY`, `ALERT_WATCHLIST`, `VIP_WELCOME`) พร้อมค่าความเหมือน (Cosine Similarity %) และหมายเลขที่นั่ง
3. **Real-Time Security & Incident Lifecycle Feed (ฝั่งขวา) และการระบุพิกัดสถานที่:**
   - ติดตามวงจรเหตุการณ์ `OPEN` -> `ACKNOWLEDGED` -> `ASSIGNED` -> `CLOSED` พร้อมตัวนับเวลา **SLA Due**
   - **การระบุกล้องและตำแหน่งพิกัดอัจฉริยะ (Enriched Camera & Location):**
     - 📷 **ชื่อกล้องวงจรปิด/คีออสก์ (`cameraName`):** แสดงชื่อกล้องตัวที่ตรวจพบ เช่น `CAM-01 ทางเข้าหลัก` พร้อมรหัสกล้อง
     - 🏢 **ตำแหน่งบนแผนผังอาคาร (Floor Plan & E-Map):** แสดงชื่ออาคาร (`building`), ชั้น (`floorLevel`), และพิกัด 2D (`mapPosX`, `mapPosY` %) พร้อมปุ่มลัด **"ดูตำแหน่งบน E-Map อาคาร"** เพื่อกระโดดไปดูตำแหน่งกล้องบนผังชั้นอาคารทันที
     - 📍 **พิกัดภูมิศาสตร์ (GPS Coordinates):** แสดงชื่อสถานที่ตั้งของสาขา (`locationName`) และพิกัดละติจูด/ลองจิจูดจริง พร้อมลิงก์ **"เปิดดูบน Google Maps"**
   - รองรับปุ่ม **`Ack`**, **`Assign`**, **`Close`**, การจัดการแบบกลุ่ม (**Bulk Ack / Bulk Close**), การเปิดดู **Evidence Video Clip** จากกล้องที่เชื่อมโยง, และการส่งออก **CSV Export** ที่รวมข้อมูลกล้อง, อาคาร, ชั้น และพิกัด GPS ครบถ้วน

---

![ศูนย์บัญชาการ SentinelVision และ Multi-Region DR](images/manual/03-sentinel-center.png)

## 5. การจัดการบัญชีเฝ้าระวัง Watchlist / Blacklist / VIP

![การจัดการบัญชีเฝ้าระวัง Watchlist / Blacklist / VIP](./screenshots/04-sentinel-watchlist.png)

### การเพิ่มและจัดการรายชื่อ (แท็บ `Watchlist / Blacklist & VIP`)
1. ในฟอร์ม **ลงทะเบียน Watchlist / Blacklist / VIP** ด้านซ้าย เลือกประเภทบัญชี:
   - `BLACKLIST`: บุคคลต้องห้าม/อดีตพนักงานที่ถูกเพิกถอนสิทธิ์ (แจ้งเตือนระดับ `CRITICAL` + ปฏิเสธการเข้าพื้นที่)
   - `WATCHLIST`: บุคคลเฝ้าระวังพิเศษ (แจ้งเตือนเจ้าหน้าที่รักษาความปลอดภัยทันทีที่พบหน้ากล้อง)
   - `VIP`: แขกผู้บริหาร/ลูกค้าคนสำคัญ (แจ้งเตือนทีมต้อนรับพร้อมข้อความต้อนรับบนจอ Kiosk)
2. กรอกชื่อ-นามสกุล, รหัสอ้างอิง, องค์กร และหมายเหตุการแจ้งเตือน (Alert Reason) แล้วแนบภาพถ่ายใบหน้าเพื่อสกัดเวกเตอร์ 512-d ลง `pgvector`
3. ในตารางด้านขวา สามารถกรองดูตามหมวดหมู่ อัปเดตใบหน้าใหม่ หรือลบรายการได้ทันที
4. **การตรวจจับและแจ้งเตือนพิกัดแบบเรียลไทม์ (Sighting & Location Tracking):**
   - เมื่อบุคคลใน Blacklist หรือ Watchlist เดินผ่านกล้องวงจรปิดหรือคีออสก์ ระบบจะจับภาพสแนปช็อต และบันทึก `SentinelIncidentLog` ทันที
   - แถบแจ้งเตือน Incident Detail จะระบุชื่อกล้องที่ตรวจพบ, โซนประตู, ชั้นและชื่ออาคารบนผัง 2D E-Map พร้อมพิกัด GPS เพื่อให้เจ้าหน้าที่รักษาความปลอดภัยเข้าควบคุมสถานการณ์ได้ตรงจุดทันที

---

![แท็บ Watchlist / Blacklist & VIP](images/manual/04-sentinel-watchlist.png)

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

![แท็บ Access Control & โซนประตู](images/manual/05-sentinel-access-control.png)

## 7. ระบบบัตรผู้มาติดต่อด้วยใบหน้า & QR Self-Service (Visitor Face Pass)

![ระบบบัตรผู้มาติดต่อด้วยใบหน้า Visitor Face Pass](./screenshots/06-sentinel-visitors.png)

### การออกบัตรผู้มาติดต่อ (แท็บ `ผู้มาติดต่อ (Visitor Pass)`)
1. **ลิงก์ลงทะเบียนล่วงหน้าด้วยตนเอง (Self-Service Pre-Registration Link):** คัดลอก URL ส่งให้ผู้มาติดต่อลงทะเบียนชื่อและอัปโหลดใบหน้าผ่านสมาร์ทโฟนล่วงหน้า พร้อมรับรหัส/QR Check-in
2. **การลงทะเบียนหน้าเคาน์เตอร์ (Walk-in Visitor Registration):** กรอกชื่อ-นามสกุล, บริษัท, พนักงานผู้รับรอง และระยะเวลาอนุญาต (เช่น `8 ชั่วโมง`) พร้อมภาพถ่ายใบหน้า
3. **Check-out & PDPA Auto-Expiry:** รองรับการกด **Check-out** เมื่อผู้มาติดต่อออกจากอาคาร และเมื่อครบกำหนดเวลา (`expiresAt`) ระบบจะเปลี่ยนสถานะเป็น `EXPIRED` โดยอัตโนมัติ

---

![แท็บผู้มาติดต่อ (Visitor Pass)](images/manual/06-sentinel-visitors.png)

## 8. การจัดการงานอีเวนต์ สัมมนา และค้นหาที่นั่งด้วยใบหน้า (Smart Events & Seat Lookup)

![การจัดการงานอีเวนต์และค้นหาที่นั่งด้วยใบหน้า](./screenshots/07-sentinel-events.png)

### ขั้นตอนการจัดงานและลงทะเบียนผู้ร่วมงาน (แท็บ `งานอีเวนต์ & สัมมนา`)
1. **สร้างงานอีเวนต์ใหม่:** ระบุชื่องาน, สถานที่, โซนประตูที่เชื่อมโยง, จำนวนที่นั่งสูงสุด และช่วงวันเวลาจัดงาน
2. **ลงทะเบียนผู้เข้าร่วมงาน + กำหนดที่นั่ง:** เลือกงานอีเวนต์ กรอกชื่อ-องค์กร และหมายเลขที่นั่ง/โซน (เช่น `VIP-A01`) พร้อมรูปใบหน้า
3. **การสแกนหน้างาน:** เมื่อผู้ร่วมงานสแกนใบหน้าที่จุด Kiosk ระบบจะแสดงข้อความต้อนรับพร้อมหมายเลขที่นั่งทันที และอัปเดตยอด **Checked-In / Registered** แบบเรียลไทม์

---

![แท็บงานอีเวนต์ & Breakout Room Capacity Check-in](images/manual/07-sentinel-events-breakout.png)

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

![บัญชีรวมพลฉุกเฉิน (Muster Roll)](images/manual/14b-muster-roll.png)

## 10. การจัดการกะเวลาทำงาน โควตาลา OT Engine, Roster Swap, Anti-Mock GPS & PDPA

![การจัดการกะเวลาทำงาน วันหยุด และการลา](./screenshots/09-hr-schedule.png)

### การบริหารจัดการงานบุคคล (`/company/hr-schedule`)
- **กะเวลาทำงาน (Work Shifts & Roster Swap):** กำหนดเวลาเข้า-ออก, นาทีผ่อนผันสาย (Grace Minutes), ตารางกะรายวัน (**Shift Roster**) และระบบขอสลับกะระหว่างพนักงาน (**Shift Swap Approval**)
- **Leave Policy & OT Rate Engine:** คำนวณสิทธิ์วันลาตามอายุงาน, ยอดยกมา (Carry-over), การลาแบบครึ่งวัน/รายชั่วโมง, แนบใบรับรองแพทย์ และคำนวณ OT อัตโนมัติตามอัตรา `1.0x` / `1.5x` / `2.0x` / `3.0x`
- **Multi-Level Approval & Delegation:** อนุมัติใบลา/OT/Regularization หลายลำดับขั้นพร้อมตั้งค่าผู้รับมอบอำนาจแทนชั่วคราว
- **Anti-Mock GPS & Wi-Fi BSSID Integrity:** ตรวจสอบความถูกต้องของพิกัด GPS และ Wi-Fi BSSID สำหรับการลงเวลานอกสถานที่
- **PDPA Biometric Purge (`/company/enroll-face`):** ตรวจสอบจำนวนเวกเตอร์ใบหน้าและลบข้อมูลชีวมิติทันทีเมื่อพนักงานลาออกหรือถอนความยินยอม

---

![การจัดการกะเวลาทำงาน โควตาลา และ OT Engine](images/manual/09-hr-schedule.png)

## 11. จุดลงเวลาและตรวจสอบใบหน้าแบบกลุ่มเรียลไทม์ & Offline HMAC Sync Kiosk

![จุดลงเวลาและตรวจสอบใบหน้าแบบกลุ่ม Multi-Face Kiosk](./screenshots/10-face-kiosk.png)

### การใช้งานหน้าจอ Kiosk (`/company/scan/:stationMode` และ `/company/timestamp-face`)
1. รองรับโหมดการทำงานเฉพาะทาง 6 รูปแบบ (`ATTENDANCE`, `ACCESS_CONTROL`, `WATCHLIST_MONITOR`, `VISITOR_CHECKIN`, `EVENT_CHECKIN`, `UNIFIED_HYBRID`)
2. เชื่อมต่อผ่าน **WebSocket (`/face/ws/kiosk`)** ความหน่วงต่ำ พร้อมวาดกรอบใบหน้าแบบกลุ่ม (Multi-Person HUD Overlay), Walk-by Detection, และ Anti-Spoof / Mask Check
3. **Offline-First Kiosk HMAC Sync (`BL-12`):** เมื่อเครือข่ายขาดหาย เครื่อง Kiosk จะแคชเวกเตอร์จาก Edge Sync Manifest และบันทึกการสแกนลง Local Queue เมื่อกลับมาออนไลน์จะส่งซิงค์ผ่าน `POST /timestamp/company/{companyId}/offline-sync` พร้อมลายเซ็น **`X-DPU-Signature-256`** (HMAC-SHA256) และ `X-DPU-Timestamp` ป้องกันการปลอมแปลงและ Replay Attack


![จุดลงเวลาและตรวจสอบใบหน้าแบบกลุ่มเรียลไทม์ (Kiosk)](images/manual/20-kiosk-attendance.png)

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


![Investigation Graph & SentinelVision AI Copilot](images/manual/08-sentinel-investigation-graph.png)

## 13. การจัดการองค์กร แผนก ตำแหน่ง พนักงาน และสถานที่ตั้ง (`/company/company-*`)

- **ข้อมูลบริษัท (`/company/company-info`)**: แก้ไขชื่อองค์กร, เลขทะเบียน, ที่อยู่, โซนเวลาเริ่มต้น (`Asia/Bangkok`) และโมดูลที่เปิดใช้งาน
- **จัดการแผนก (`/company/company-department`)**: สร้าง/แก้ไข/ลบแผนก, ค้นหา และส่งออกข้อมูลแผนกเป็น CSV
- **จัดการตำแหน่ง (`/company/company-position`)**: สร้าง/แก้ไข/ลบตำแหน่งงาน และส่งออกข้อมูลเป็น CSV
- **ทะเบียนพนักงาน & ใบหน้า (`/company/company-emp`)**:
  - เพิ่ม/แก้ไขข้อมูลพนักงาน, นำเข้าพนักงานจำนวนมาก (Batch Excel/CSV Import), และกรองตามแผนก/ตำแหน่ง/สถานะ
  - **5-Angle Face Quality Gate Enrollment**: ลงทะเบียนใบหน้าพนักงาน 5 มุม พร้อมตรวจสอบความคมชัด ความสว่าง และมุมเอียงของใบหน้าก่อนบันทึกเวกเตอร์ 512 มิติ
- **สถานที่ตั้ง / สาขา (`/company/company-location`)**: กำหนดพิกัด GPS Geofencing, รัศมีที่อนุญาต และ Wi-Fi BSSID สำหรับการลงเวลาผ่านมือถือ

---

![ข้อมูลบริษัท](images/manual/10a-company-info.png)

![ทะเบียนพนักงาน & 5-Angle Face Enrollment](images/manual/10b-company-employees.png)

## 14. การลงเวลา การอนุมัติ รายงาน และ Employee Self-Service (ESS)

- **ศูนย์รวมจุดสแกนและสถานีปฏิบัติการ Bento Grid (`/company/scan-hub`)**:
  - **Biometric Face Scan Terminal (Hero Bento Card - Span 8, `cyan`)**: ศูนย์สั่งการเทอร์มินัลตรวจจับใบหน้าหลายคนพร้อมกันความเร็วสูง แสดงสถานะความพร้อม (`PRIMARY TERMINAL` / `READY`), โหมดเริ่มต้น, ปุ่มเปิดเทอร์มินัลสด (`Open Terminal`), ปุ่มคัดลอกลิงก์ตรง (`Copy URL`), แถบสลับโหมดด่วน 6 โหมด (`ATTENDANCE`, `ACCESS_CONTROL`, `WATCHLIST_MONITOR`, `VISITOR_CHECKIN`, `EVENT_CHECKIN`, `UNIFIED_HYBRID`), และรายการ Active Terminal Endpoints แยกจุด
  - **Hardware & Automation Rules (Bento Card - Span 4, `sky`)**: กำหนดค่าประตูเริ่มต้น, กิจกรรมเริ่มต้น, การตอบสนอง Unknown Face และสวิตช์กฎอัตโนมัติ (แจ้งเตือนเงียบ Blacklist, ข้อความต้อนรับ VIP, เสียงพูดสังเคราะห์ TTS, ปลดล็อกประตูรีเลย์เมื่อลงเวลาสำเร็จ)
  - **5 Operational Domains Bento Cards (โครงสร้าง 5 มิติการทำงาน)**:
    - *Security & Watchlist (`rose`)*: เฝ้าระวังบัญชีดำและบุคคลน่าสงสัย ลิงก์ตรงเข้า Sentinel Center และเปิด Watchlist Scanner
    - *Smart Access Control (`sky`)*: ควบคุมประตูทางเข้า-ออก ไม้กั้น พร้อมลิงก์ไปยัง Zone Management และ Access Gate Scanner
    - *Attendance & Workforce (`cyan`)*: การลงเวลาพนักงาน กะทำงาน และตารางเวลา พร้อมลิงก์ไปยัง Timestamp Log
    - *Visitor & Event Check-In (`amber`)*: รองรับทั้งบัตรผู้มาติดต่อ (Visitor Pass) และงานอีเวนต์ (Event Check-In) ในการ์ดเดียว
    - *CCTV & Perimeter Surveillance (`violet`)*: สตรีมมิ่งกล้องวงจรปิดผ่าน MediaMTX WebRTC เชื่อมต่อไปยัง CCTV Wall
- **ประวัติการลงเวลา (`/company/timestamp-log`) & รายการแจ้งเตือน/ผิดปกติ (`/company/warning-timestamp-log`)**: ตรวจสอบบันทึกเวลาเข้า-ออกงาน ภาพถ่ายขณะสแกน คะแนนความมั่นใจ (Confidence) รายการมาสาย/ออกก่อน/นอกพื้นที่ และส่งออก CSV/Excel
- **กล่องอนุมัติ (`/company/approval-inbox`)**: อนุมัติหรือปฏิเสธคำขอลา, คำขอ OT, การสลับกะ (Roster Swap) และการแก้ไขเวลาทำงานแบบ Multi-level Approval Chain พร้อมตัวกรองตามสถานที่ตั้ง
- **รายงาน (`/company/reports`)**: สรุปรายงานเวลาทำงานรายวัน/รายเดือน ชั่วโมง OT และสถิติการเข้างาน
- **พอร์ทัลพนักงาน (`/company/self-service`)**: ให้พนักงานดูประวัติการลงเวลาของตนเอง ยื่นคำขอลา/OT/สลับกะ และติดตามสถานะการอนุมัติ

---

![ศูนย์รวมจุดสแกน - เทอร์มินัลและกฎอัตโนมัติ (Scan Hub Hero)](images/manual/11-scan-hub.png)

![ศูนย์รวมจุดสแกน - โครงสร้าง 5 มิติปฏิบัติการ (Scan Hub 5 Domains)](images/manual/11-scan-hub-domains.png)

![ประวัติการลงเวลา](images/manual/12a-timestamp-log.png)

![กล่องอนุมัติ (Approval Inbox)](images/manual/12b-approval-inbox.png)

![รายงาน (Reports)](images/manual/13a-reports.png)

![พอร์ทัลพนักงาน (Employee Self-Service)](images/manual/13b-self-service.png)

## 15. หน้าจอเฉพาะทาง Access / Watchlist / Visitors / Events & Scan Hub

นอกเหนือจากหน้า Command Center รวม (`/company/sentinel-center`) ระบบแยกหน้าจอจัดการเฉพาะทางตามเมนู Dual-Rail Sidebar เพื่อให้ทีมปฏิบัติการเข้าถึงได้รวดเร็ว:

- **Access Control (`/company/scan/access-control`, `/company/access-control/zones`, `/logs`, `/settings`)**:
  - จัดการโซนประตู ตารางเวลาเปิด-ปิดประตู อัปเดตสถานะ Relay Latency (ms) ส่งออก Access Logs เป็น CSV และตั้งค่านโยบาย Tailgating / Anti-Passback
- **Watchlist & Blacklist (`/company/scan/watchlist`, `/company/watchlist/identities`, `/incidents`, `/settings`)**:
  - จัดการรายชื่อเฝ้าระวัง พร้อมวันหมดอายุ (Expiration), บันทึกปิดเคส Incident Resolution Note และตั้งค่าระดับความไวในการแจ้งเตือน
- **Visitors (`/company/scan/visitor`, `/company/visitors/passes`, `/muster-roll`, `/settings` และ `/visitor-invite/:token`)**:
  - ออกบัตร Visitor Pass, พิมพ์บัตร, ส่งลิงก์เชิญล่วงหน้า (`/visitor-invite/:token`) ให้ผู้มาติดต่อสแกนบัตรประชาชน/พาสปอร์ต (OCR + PDPA masking) และลงทะเบียนด้วยตนเอง รวมถึงหน้า **Muster Roll (`/company/visitors/muster-roll`)** สำหรับเช็กชื่อรวมพลฉุกเฉินและส่งออก CSV
- **Events (`/company/scan/event`, `/company/events/campaigns`, `/checkins`, `/settings`)**:
  - สร้างแคมเปญอีเวนต์ จัดการผู้ลงทะเบียน ค้นหาที่นั่งด้วยใบหน้า คุมความจุห้องประชุมย่อย (**Breakout Room Capacity Check-in**) และส่งออก Event Dwell CSV

---

![จัดการโซนประตู (Access Zones)](images/manual/14a-access-zones.png)

## 16. ระบบกล้องวงจรปิด Live Wall, NVR Playback, E-Map, Face Monitor & Presence

- **จัดการกล้อง (`/company/cameras`)**: เพิ่ม/แก้ไขกล้อง RTSP, กด **Discover ONVIF** เพื่อค้นหากล้องในวง LAN อัตโนมัติ, ควบคุมทิศทาง **PTZ**, และตั้งค่า **PDPA Privacy Mask** (เบลอโซนอ่อนไหวบนภาพกล้อง)
- **Live Wall (`/company/live-wall`)**: แสดงภาพสดหลายช่องพร้อมกัน (WebRTC/HLS ผ่าน MediaMTX) รองรับการสลับ Layout Preset และถ่ายภาพ Snapshot
- **NVR Playback (`/company/playback`)**: ดูวิดีโอบันทึกย้อนหลังพร้อมแถบ **AI-Marker Timeline Scrubber** เพื่อกระโดดไปยังช่วงเวลาที่เกิดเหตุการณ์ AI ได้ทันที
- **E-Map (`/company/e-map`)**: แผนผังตำแหน่งกล้องและประตูแบบโต้ตอบ พร้อมปุ่มเปิดดูภาพสด (Quick Live) และสั่งปลดล็อกประตู (Quick Door Link)
- **Face Monitor (`/company/face-monitor`) & Presence (`/company/presence`)**: ติดตามการตรวจจับใบหน้าแบบเรียลไทม์จากกล้อง CCTV และสรุปยอดคนในอาคารแยกตามโซน

---

![จัดการกล้อง ONVIF, PTZ & PDPA Privacy Mask](images/manual/15-cameras-onvif-pdpa.png)

![Live Wall](images/manual/16a-live-wall.png)

![NVR Playback & AI-Marker Timeline](images/manual/16b-nvr-playback.png)

![Floor E-Map](images/manual/16c-e-map.png)

![Face Monitor](images/manual/17a-face-monitor.png)

![Presence & Dwell-Time Intelligence](images/manual/17b-presence.png)

## 17. ความปลอดภัย Audit Log, อุปกรณ์ Kiosk, การแจ้งเตือน, AI Copilot & System Admin

- **Audit Log (`/company/audit-log`)**: บันทึกการเปลี่ยนแปลงสำคัญทั้งหมดแบบ Append-only พร้อมปุ่ม **Verify Hash-Chain** (`VERIFIED`) เพื่อพิสูจน์ว่าไม่มีการแก้ไขข้อมูลย้อนหลัง
- **จัดการอุปกรณ์ (`/company/devices` และ `/kiosk/pair`)**: ลงทะเบียนและจับคู่เครื่อง Kiosk ด้วย Pairing Code (`/kiosk/pair`), หมุนเวียน Key และเพิกถอนอุปกรณ์ที่ไม่ได้ใช้งาน
- **ศูนย์แจ้งเตือน (`/company/notification-center`)**: ตรวจสอบประวัติการส่งแจ้งเตือน (Delivery History) ผ่าน LINE Messaging API, SMTP Email และ Webhook Outbox
- **โปรไฟล์ & ความปลอดภัย (`/company/profile-security`)**: เปลี่ยนรหัสผ่าน และเปิดใช้งาน Two-Factor Authentication (2FA/TOTP)
- **ตั้งค่าบริษัท (`/company/settings`)**: ค้นหาการตั้งค่า (Settings Search Filter), รีเซ็ตค่าเริ่มต้น, เตือนเมื่อมีการเปลี่ยนแปลงที่ยังไม่บันทึก (Unsaved Changes Guard), ตั้งค่าภูมิภาค, SCIM 2.0 / HRIS Connectors และ Multi-Region DR Status
- **Investigation Graph & AI Copilot**: แท็บกราฟความสัมพันธ์ใน Sentinel Center และปุ่ม **Ask AI** สำหรับถาม-ตอบสรุปเหตุการณ์และข้อมูลองค์กรแบบเรียลไทม์
- **System Admin Console (`/admin/*`)** (สำหรับผู้ดูแลระบบระดับ Platform):
  - `/admin/member-manage`: จัดการผู้ใช้งานทั้งหมดข้ามองค์กร
  - `/admin/manage-companys`: สร้าง/ระงับ/จัดการโควตาของแต่ละบริษัท (Multi-tenant)
  - `/admin/admin-manage`: จัดการสิทธิ์ผู้ดูแลระบบแพลตฟอร์ม
  - `/admin/system-setting`: ตั้งค่าระบบส่วนกลาง
  - `/admin/error-logs`: ตรวจสอบบันทึกข้อผิดพลาดของระบบ (Error Logs)

![Audit Log Hash-Chain Verified](images/manual/18-audit-log-verified.png)

![จัดการอุปกรณ์ Kiosk](images/manual/19a-devices.png)

![ศูนย์แจ้งเตือน (Notification Center)](images/manual/19b-notification-center.png)

![โปรไฟล์ & ความปลอดภัย 2FA](images/manual/19c-profile-security.png)

![ตั้งค่าบริษัท](images/manual/19d-company-settings.png)
