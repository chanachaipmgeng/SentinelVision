# DPU Attendance v3.0.0 — Enterprise Face Recognition & HR Attendance Platform

ระบบลงเวลาเข้า-ออกงานด้วยใบหน้าแบบเรียลไทม์ระดับ Enterprise (InsightFace `buffalo_l` 512-d + PostgreSQL `pgvector` HNSW / Face Core BFF) รองรับ Multi-Company, โหมดลงเวลาเข้า-ออกงานแบบ Hybrid (`AUTO` / `CHECK_IN` / `CHECK_OUT`), ระบบหลายกะทำงานและกะข้ามคืน (`WorkShift`), ระบบใบลาและปฏิทินวันหยุดบริษัท, การจัดการข้อมูลชีวมิติตาม พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล (PDPA), Kiosk Device Tokens & 2FA (TOTP / OIDC SSO), ระบบป้องกันภาพปลอมแปลง (Passive Anti-Spoofing), Object Storage (S3/MinIO) และ Signed Payroll Webhooks

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| URL | บริการ |
|-----|--------|
| `http://localhost/` | Admin Console (`Web-Manage` — Angular 17) |
| `http://localhost/company/timestamp-face` | Kiosk ลงเวลาด้วยใบหน้าแบบ Multi-person Realtime (WebSocket + `?kioskToken=...`) |
| `http://localhost/company/hr-schedule` | ศูนย์จัดการกะงาน / ใบลา / วันหยุด / PDPA / Kiosk & 2FA / Payroll Webhook & Cloud Metrics |
| `http://localhost/docs` | API Swagger (เมื่อตั้ง `EXPOSE_API_DOCS=true`) |
| `http://localhost/health` / `/ready` / `/metrics` | Liveness, Readiness และ Prometheus Histograms (`dpu_face_gpu_latency_ms`, `dpu_pgvector_search_ms`) |

## Key Enterprise Capabilities (Phase 1 – Phase 5 Complete)

- **Realtime Multi-Person Face Kiosk & Passive Anti-Spoofing (`/company/timestamp-face`):** สแกนใบหน้าต่อเนื่องผ่าน WebSocket (`/face/ws/kiosk`) พร้อมคิว GPU (`run_on_face_gpu`) และระบบตรวจจับภาพปลอมแปลง `check_passive_antispoof_bgr` (YCrCb skin chrominance + specular screen glare)
- **Hybrid Check-In / Check-Out & Multi-Shift (Cross-Midnight):** สแกนครั้งแรกของวันเป็น `CHECK_IN` และสแกนถัดไปเป็น `CHECK_OUT` อัตโนมัติ รองรับกะข้ามเที่ยงคืน (`isCrossMidnight`) และการผูกกะรายแผนก/รายบุคคล พร้อมคำนวณเวลาสาย (`lateMinutes`) และล่วงเวลา (`overtimeMinutes`)
- **Leave Workflow, Company Holidays & Excel/CSV Export:** ยื่นและอนุมัติใบลา (`ANNUAL`, `SICK`, `PERSONAL`, `WFH`), ปฏิทินวันหยุดบริษัทที่เชื่อมต่อกับระบบแจ้งเตือนขาดงานอัตโนมัติ และส่งออกรายงาน `.xlsx` / `.csv`
- **PDPA Biometric Compliance & Right to Erasure:** บันทึกเวลาให้ความยินยอม (`biometricConsentAt`) และรองรับการเพิกถอนความยินยอมที่ลบเวกเตอร์ใบหน้าออกจาก `pgvector` และไฟล์ภาพออกจาก Disk / S3 ทันที
- **Enterprise Identity (TOTP 2FA / OIDC SSO) & Scoped Kiosk Device Tokens:** ยืนยันตัวตน 2 ชั้นตามมาตรฐาน RFC 6238 TOTP และออกโทเค็นเฉพาะตู้ Kiosk (`typ="kiosk"`) ที่จำกัดสิทธิ์เฉพาะ Endpoint สแกนใบหน้าของบริษัทตนเองและเพิกถอนได้ทันที
- **Cloud-Native Storage (S3/MinIO), W3C Trace Context & Signed Payroll Webhooks:** รองรับ AWS Signature V4 Presigned URLs (`STORAGE_BACKEND=s3`), เฮดเดอร์ `traceparent`, Prometheus Latency Histograms และส่ง Outbound Webhook พร้อมลายเซ็น `X-DPU-Signature-256: v1=<hmac_sha256>` ไปยังระบบเงินเดือน/ERP

## Documentation

| Doc | Contents |
|-----|----------|
| [GEMINI.md](GEMINI.md) | **กฎสถาปัตยกรรมและมาตรฐานวิศวกรรมระดับ Enterprise** |
| [docs/DEPLOY-SERVER.md](docs/DEPLOY-SERVER.md) | **คู่มือติดตั้งบนเซิร์ฟเวอร์** (clone / Docker / GPU·CPU / seed mock) |
| [docs/SETUP.md](docs/SETUP.md) | ติดตั้งบนเครื่องพัฒนา / Docker / env |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | โครงสร้างระบบ, Face Pipeline, Security, Storage & Outbox Architecture |
| [docs/API.md](docs/API.md) | สรุป Endpoint ทั้งหมด (Auth/2FA/SSO, Face, Attendance, HR/PDPA, Kiosk Devices, Webhooks) |
| [docs/RUNBOOK.md](docs/RUNBOOK.md) | คู่มือดูแลระบบ (RPO/RTO, GPU, Face Core, Alembic Migrations) |
| [docs/CURSOR-AGENT.md](docs/CURSOR-AGENT.md) | Cursor rules & skills สำหรับ AI agent |
| [docs/BACKLOG.md](docs/BACKLOG.md) | สรุปสถานะ **Enterprise Roadmap (Phase 1–5 Completed)** |

## Layout

```
docker-compose.yml
docker/                 # nginx + DB init
API-Fast/               # FastAPI v3.0.0 + InsightFace + pgvector + Alembic (0001..0005)
Web-Manage/             # Angular 17 admin + HR/PDPA/Cloud console + realtime face kiosk
docs/                   # Architecture, API, Capacity & Runbook docs
```
