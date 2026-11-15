# Operations, Migrations & Deployment

[← กลับหน้าหลัก Wiki](Home.md)

## 1. Docker Stack & Database Migrations

```bash
# เริ่มระบบทั้งหมด
docker compose up -d --build

# อัปเดต Schema ด้วย Alembic (ปัจจุบันอยู่ที่ 0035_sprint6_tailgating_health_edge)
docker exec sentinel-api alembic upgrade head
docker exec sentinel-api alembic check
```

## 2. Fast Frontend Asset Deployment (`Web-Manage`)

สำหรับงานแก้ไขฝั่ง Frontend อย่างเดียว สามารถ build และอัปเดตไฟล์เข้า container `sentinel-admin` ได้ทันทีโดยไม่ต้อง rebuild Docker image:

```powershell
Set-Location Web-Manage
npm run lint
npm run build
# รอให้ npm run build จบด้วย exit code 0 ก่อนเสมอ
docker cp dist/preview/browser/. sentinel-admin:/usr/share/nginx/html/
docker exec sentinel-admin nginx -s reload
```

## 3. Verification Commands

### Frontend (`Web-Manage/`)
```bash
npm run lint    # eslint "src/**/*.ts" "src/**/*.html"
npm run build   # Production Angular bundle
```

### Backend (`API-Fast/`)
```bash
ruff check .
python -m mypy --no-incremental
python -m pytest -q -p no:cacheprovider
```
