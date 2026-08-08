# DPU Attendance

ระบบเช็คอินด้วยใบหน้า (InsightFace + pgvector) สำหรับโปรเจกต์จบ DPU

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| URL | บริการ |
|-----|--------|
| http://localhost/ | Admin |
| http://localhost/company/timestamp-face | Kiosk ลงเวลาด้วยใบหน้า |
| http://localhost/docs | API Swagger |

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/DEPLOY-SERVER.md](docs/DEPLOY-SERVER.md) | **คู่มือติดตั้งบนเซิร์ฟเวอร์** (clone / Docker / GPU·CPU / seed mock) |
| [docs/SETUP.md](docs/SETUP.md) | ติดตั้งบนเครื่องพัฒนา / Docker / env |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | โครงสร้างระบบและ face pipeline |
| [docs/API.md](docs/API.md) | สรุป endpoint |
| [docs/CURSOR-AGENT.md](docs/CURSOR-AGENT.md) | Cursor rules & skills สำหรับ AI agent |
| [docs/BACKLOG.md](docs/BACKLOG.md) | สิ่งที่ยังค้าง |

## Layout

```
docker-compose.yml
docker/                 # nginx + DB init
API-Fast/               # FastAPI + InsightFace
Web-Manage/             # Angular 17 admin + face kiosk
docs/
```

**หมายเหตุ:** ต้อง enroll หน้าใหม่หลังย้ายจาก `face_recognition` เก่า — encoding 128-d ใช้ต่อไม่ได้
