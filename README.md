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
| http://localhost/mobile/ | Mobile |
| http://localhost/docs | API Swagger |

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/SETUP.md](docs/SETUP.md) | ติดตั้ง / Docker / env |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | โครงสร้างระบบและ face pipeline |
| [docs/API.md](docs/API.md) | สรุป endpoint |
| [docs/BACKLOG.md](docs/BACKLOG.md) | สิ่งที่ยังค้าง |

## Layout

```
docker-compose.yml
docker/                 # nginx + DB init
API-Fast/               # FastAPI + InsightFace
Web-Manage/             # Angular 17 admin
Webview-Mobile/         # Angular 15 mobile
docs/
```

**หมายเหตุ:** ต้อง enroll หน้าใหม่หลังย้ายจาก `face_recognition` เก่า — encoding 128-d ใช้ต่อไม่ได้
