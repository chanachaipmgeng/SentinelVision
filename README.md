# SentinelVision v6.3.0 — Unified Biometric Identity, Attendance, Access Control, Watchlist, Smart Parking & Events Platform

**GitHub Repository:** `https://github.com/chanachaipmgeng/SentinelVision.git`

แพลตฟอร์มยืนยันตัวตนด้วยใบหน้า เฝ้าระวังความปลอดภัย และควบคุมการเข้า-ออกอัจฉริยะระดับ Enterprise (InsightFace `buffalo_l` 512-d + PostgreSQL `pgvector` HNSW / Face Core BFF) ครอบคลุม **8 โมดูลหลักในคอนโซลเดียว**:
1. **Time & Workforce Attendance:** ลงเวลาเข้า-ออกงานแบบ Hybrid (`AUTO` / `CHECK_IN` / `CHECK_OUT`), รองรับหลายกะและกะข้ามคืน (`WorkShift`), ระบบใบลา, ปฏิทินวันหยุด และส่งออกรายงาน `.xlsx`/`.csv`/HRIS Connectors
2. **Watchlist, Blacklist & VIP Alerting:** ตรวจจับบุคคลต้องห้าม (`BLACKLIST`), บุคคลเฝ้าระวัง (`POI`), และแขกผู้บริหาร (`VIP`) แบบ 1:N Real-time พร้อมส่ง Silent Alarm ผ่าน Webhook / LINE / Security Feed ทันที
3. **Smart Access Control, Door Zones & RFID Multi-Credential:** กำหนดสิทธิ์ผ่านประตูตามโซน (`SentinelAccessZone`), ช่วงเวลาเปิด-ปิด, บังคับ 2FA (`Face + PIN/TOTP`), บัตรผ่าน **RFID Physical Access Cards** (`/company/rfid-cards`, MIFARE/DESFire/HID), และสั่งปลดล็อกกลอนประตู IoT Relay ระยะไกล
4. **Smart Parking & Vehicle LPR:** บริหารลานจอดรถอัจฉริยะและตรวจจับป้ายทะเบียน (`/company/parking`), ควบคุมไม้กั้นอัตโนมัติ, จัดสรรช่องจอด และคำนวณเวลาจอด (Dwell Time)
5. **Visitor Pass & Temporary Biometrics:** ลงทะเบียนใบหน้าผู้มาติดต่อชั่วคราว (`VISITOR`) พร้อมลิงก์เชิญลงทะเบียนล่วงหน้า (HMAC-signed + Thai ID/Passport OCR + PDPA Consent) และล้างเวกเตอร์ใบหน้าอัตโนมัติตามกำหนด (`expire_sentinel_identities_tick`)
6. **Smart Events & Seminar Check-in:** สร้างแคมเปญงานอีเวนต์/สัมมนา ลงทะเบียนล่วงหน้าผ่าน Public QR/Face Portal พร้อมระบุโต๊ะ/ที่นั่ง (`seatNumber`) และเช็คอินหน้างานแบบเรียลไทม์
7. **Emergency Muster Roll & Offline-First Edge AI Sync:** ตรวจสอบรายชื่อผู้ที่อยู่ในอาคารวันนี้แบบ Real-time สำหรับกรณีฉุกเฉิน/อพยพหนีไฟ และซิงค์ Manifest เวกเตอร์ใบหน้าไปยังเครื่อง Edge Kiosk
8. **Edge Fleet Health & Governance:** ศูนย์ตรวจวัดสุขภาพอุปกรณ์ Edge Kiosk & CCTV (`/company/fleet-health`), Hash-chained Audit Log, RBAC รายสาขา/แผนก และ Notification Template Engine

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| URL | บริการ |
|-----|--------|
| `http://localhost:8880/` | SentinelVision Admin Console (`Web-Manage` — Angular 17+, VaultX Obsidian Glass + Two-Column Dual-Rail Sidebar) |
| `http://localhost:8880/company/sentinel-center` | **SentinelVision Security & Access Command Center** (Watchlist, Access Zones, Visitor Pass, Smart Events, Muster Roll, Investigation Graph & 1:N Scanner) |
| `http://localhost:8880/company/parking` | **Smart Parking & Vehicle LPR** (ผังช่องจอดสด, ทะเบียนรถ, ประวัติสแกน LPR, LPR Gate Simulator) |
| `http://localhost:8880/company/rfid-cards` | **RFID Physical Access Cards** (ออกบัตร MIFARE/HID/DESFire, Swipe Access Simulator) |
| `http://localhost:8880/company/fleet-health` | **Edge Fleet Health Telemetry** (ดัชนีความพร้อม Kiosk / CCTV / GPU Queue) |
| `http://localhost:8880/company/scan-hub` / `/company/scan/:stationMode` | **Modular Kiosk Scan Stations** (6 โหมด: `ATTENDANCE`, `ACCESS_CONTROL`, `WATCHLIST_MONITOR`, `VISITOR_CHECKIN`, `EVENT_CHECKIN`, `UNIFIED_HYBRID` + MediaPipe Edge Hand Gesture) |
| `http://localhost:8880/company/timestamp-face` | Kiosk สแกนใบหน้าแบบ Multi-person Realtime (WebSocket; จับคู่อุปกรณ์ด้วยรหัสครั้งเดียวที่ `/kiosk/pair`) |
| `http://localhost:8880/company/hr-schedule` | ศูนย์จัดการกะงาน / ใบลา / วันหยุด / PDPA / Kiosk & 2FA / Payroll Webhook & Cloud Metrics |
| Floating **Ask AI** Dock | **AI Copilot (`app-ask-dock`)** รองรับ SSE Streaming (`/sentinel/company/{companyId}/assistant/chat`) + Silero VAD Voice Input (`@ricky0123/vad-web`) |
| `http://localhost:8880/docs` | API Swagger (เมื่อตั้ง `EXPOSE_API_DOCS=true`) |
| `http://localhost:8880/health` / `/ready` / `/metrics` | Liveness, Readiness และ Prometheus Histograms (`dpu_face_gpu_latency_ms`, `dpu_pgvector_search_ms`) |

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/wiki/Home.md](docs/wiki/Home.md) | **SentinelVision Wiki** (สารบัญวิกิระบบ, สถาปัตยกรรม, Edge AI, UI/UX & Operations) |
| [GEMINI.md](GEMINI.md) | **กฎสถาปัตยกรรมและมาตรฐานวิศวกรรมระดับ Enterprise (Root Rules)** |
| [Web-Manage/GEMINI.md](Web-Manage/GEMINI.md) | **กฎ UX/UI และมาตรฐาน Frontend เฉพาะฝั่ง `Web-Manage/`** |
| [docs/SENTINELVISION-ROADMAP.md](docs/SENTINELVISION-ROADMAP.md) | **แผนแม่บทและสถานะการพัฒนา SentinelVision (Phase 1–8 / v6.3.0 Complete)** |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | โครงสร้างระบบ, Dual `pgvector` HNSW Pipeline, Edge AI, AI Copilot & Investigation Graph |
| [docs/API.md](docs/API.md) | สรุป Endpoint ทั้งหมด (Auth/2FA/SSO, Face, SentinelVision Security/Access/Parking/RFID/Events/Graph/Copilot, Attendance, HR/PDPA) |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | **สัญญา API ระดับ Enterprise** (Response Envelopes, Error Taxonomy, Pagination, Scoping & Streaming Protocols) |
| [docs/USER-MANUAL-SENTINELVISION.md](docs/USER-MANUAL-SENTINELVISION.md) | คู่มือการใช้งานระบบ SentinelVision สำหรับผู้ดูแลและผู้ปฏิบัติงาน |
| [docs/DEPLOY-SERVER.md](docs/DEPLOY-SERVER.md) | **คู่มือติดตั้งบนเซิร์ฟเวอร์** (clone / Docker / GPU·CPU / seed mock) |
| [docs/SETUP.md](docs/SETUP.md) | ติดตั้งบนเครื่องพัฒนา / Docker / env |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | คู่มือดูแลระบบ (RPO/RTO, GPU, Face Core, Alembic Migrations `0001..0037`) |

## Layout

```
docker-compose.yml
docker/                 # nginx single/dual/quad-GPU gateway (port 8880) + DB init + backup + CSP runtime
API-Fast/               # FastAPI + InsightFace + pgvector + Alembic (0001..0037)
Web-Manage/             # Angular SentinelVision console + Edge AI WASM assets (public/) + realtime face kiosk
docs/                   # Architecture, API, API Contract, Wiki (docs/wiki/), Roadmap, Capacity & Runbook docs
```
