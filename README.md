# SentinelVision v4.0.0 — Unified Biometric Identity, Attendance, Access Control, Watchlist & Smart Events Platform

**GitHub Repository:** `https://github.com/chanachaipmgeng/SentinelVision.git`

แพลตฟอร์มยืนยันตัวตนด้วยใบหน้า เฝ้าระวังความปลอดภัย และควบคุมการเข้า-ออกอัจฉริยะระดับ Enterprise (InsightFace `buffalo_l` 512-d + PostgreSQL `pgvector` HNSW / Face Core BFF) ต่อยอดจากระบบลงเวลาเข้า-ออกงานสู่ **6 โมดูลหลักในสมองกลเดียว**:
1. **Time & Workforce Attendance:** ลงเวลาเข้า-ออกงานแบบ Hybrid (`AUTO` / `CHECK_IN` / `CHECK_OUT`), รองรับหลายกะและกะข้ามคืน (`WorkShift`), ระบบใบลา, ปฏิทินวันหยุด และส่งออกรายงาน `.xlsx`/`.csv`
2. **Watchlist, Blacklist & VIP Alerting:** ตรวจจับบุคคลต้องห้าม (`BLACKLIST`), บุคคลเฝ้าระวัง (`POI`), และแขกผู้บริหาร (`VIP`) แบบ 1:N Real-time พร้อมส่ง Silent Alarm ผ่าน Webhook / LINE / Security Feed ทันที
3. **Smart Access Control & Door Zones:** กำหนดสิทธิ์ผ่านประตูตามโซน (`SentinelAccessZone`), ช่วงเวลาเปิด-ปิด, บังคับ 2FA (`Face + PIN/TOTP`) สำหรับพื้นที่ความมั่นคงสูง และสั่งปลดล็อกกลอนประตู IoT Relay ระยะไกล
4. **Visitor Pass & Temporary Biometrics:** ลงทะเบียนใบหน้าผู้มาติดต่อชั่วคราว (`VISITOR`) พร้อมตั้งเวลาหมดอายุและล้างข้อมูลเวกเตอร์ใบหน้าอัตโนมัติตามมาตรฐาน PDPA (`expire_sentinel_identities_tick`)
5. **Smart Events & Seminar Check-in:** สร้างแคมเปญงานอีเวนต์/สัมมนา ลงทะเบียนใบหน้าผู้ร่วมงานพร้อมระบุโต๊ะ/ที่นั่ง (`seatNumber`) และแสดงข้อความต้อนรับบนจอ Kiosk
6. **Emergency Muster Roll & Offline-First Edge AI Sync:** ตรวจสอบรายชื่อผู้ที่อยู่ในอาคารวันนี้แบบ Real-time สำหรับกรณีฉุกเฉิน/อพยพหนีไฟ และซิงค์ Manifest เวกเตอร์ใบหน้าไปยังเครื่อง Edge Kiosk

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| URL | บริการ |
|-----|--------|
| `http://localhost/` | SentinelVision Admin Console (`Web-Manage` — Angular 17) |
| `http://localhost/company/sentinel-center` | **SentinelVision Security & Access Command Center** (Watchlist, Access Zones, Visitor Pass, Smart Events, Muster Roll & 1:N Scanner) |
| `http://localhost/company/timestamp-face` | Kiosk สแกนใบหน้าแบบ Multi-person Realtime (WebSocket + `?kioskToken=...`) |
| `http://localhost/company/hr-schedule` | ศูนย์จัดการกะงาน / ใบลา / วันหยุด / PDPA / Kiosk & 2FA / Payroll Webhook & Cloud Metrics |
| `http://localhost/docs` | API Swagger (เมื่อตั้ง `EXPOSE_API_DOCS=true`) |
| `http://localhost/health` / `/ready` / `/metrics` | Liveness, Readiness และ Prometheus Histograms (`dpu_face_gpu_latency_ms`, `dpu_pgvector_search_ms`) |

## Documentation

| Doc | Contents |
|-----|----------|
| [GEMINI.md](GEMINI.md) | **กฎสถาปัตยกรรมและมาตรฐานวิศวกรรมระดับ Enterprise (SentinelVision v4.0)** |
| [docs/SENTINELVISION-ROADMAP.md](docs/SENTINELVISION-ROADMAP.md) | **แผนแม่บทและสถาปัตยกรรม SentinelVision (Phase 1–6 Complete)** |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | โครงสร้างระบบ, Dual `pgvector` HNSW Pipeline, Security, Access Control & Outbox Architecture |
| [docs/API.md](docs/API.md) | สรุป Endpoint ทั้งหมด (Auth/2FA/SSO, Face, SentinelVision Security/Access/Events, Attendance, HR/PDPA) |
| [docs/BACKLOG.md](docs/BACKLOG.md) | สรุปสถานะ **Enterprise & SentinelVision Roadmap (Phase 1–6 Completed)** |
| [docs/DEPLOY-SERVER.md](docs/DEPLOY-SERVER.md) | **คู่มือติดตั้งบนเซิร์ฟเวอร์** (clone / Docker / GPU·CPU / seed mock) |
| [docs/SETUP.md](docs/SETUP.md) | ติดตั้งบนเครื่องพัฒนา / Docker / env |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | คู่มือดูแลระบบ (RPO/RTO, GPU, Face Core, Alembic Migrations `0001..0006`) |

## Layout

```
docker-compose.yml
docker/                 # nginx single/dual/quad-GPU gateway + DB init
API-Fast/               # FastAPI v4.0.0 + InsightFace + pgvector + Alembic (0001..0006)
Web-Manage/             # Angular 17 SentinelVision console + HR/PDPA + realtime face kiosk
docs/                   # Architecture, API, SentinelVision Roadmap, Capacity & Runbook docs
```
