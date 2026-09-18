# คู่มือติดตั้งบนเซิร์ฟเวอร์ (Deploy Server)

คู่มือนี้สำหรับ clone โปรเจกต์จาก GitLab แล้วรันด้วย Docker รวมถึงการใส่ **mock / demo data**

ที่เก็บโค้ด:

```text
https://mygitplus.myhr.co.th/chanachai.o/facescan-timeattendance.git
```

เอกสารที่เกี่ยวข้อง: [SETUP.md](SETUP.md) (รันบนเครื่องพัฒนา) · [ARCHITECTURE.md](ARCHITECTURE.md) · [API.md](API.md)

---

## สารบัญ

1. [สิ่งที่ต้องมีบนเซิร์ฟเวอร์](#1-สิ่งที่ต้องมีบนเซิร์ฟเวอร์)
2. [Clone โปรเจกต์](#2-clone-โปรเจกต์)
3. [ตั้งค่า environment](#3-ตั้งค่า-environment)
4. [Build และเปิดระบบ](#4-build-และเปิดระบบ)
5. [Seed mock / demo data](#5-seed-mock--demo-data)
6. [เข้าใช้งานและบัญชีทดสอบ](#6-เข้าใช้งานและบัญชีทดสอบ)
7. [นำเข้าพนักงาน (Excel + รูป)](#7-นำเข้าพนักงาน-excel--รูป)
8. [อัปเดตโค้ด / คำสั่งใช้บ่อย](#8-อัปเดตโค้ด--คำสั่งใช้บ่อย)
9. [แก้ปัญหาเบื้องต้น](#9-แก้ปัญหาเบื้องต้น)

---

## 1. สิ่งที่ต้องมีบนเซิร์ฟเวอร์

| รายการ | จำเป็น | หมายเหตุ |
|--------|--------|----------|
| Docker Engine + Compose v2 | ใช่ | `docker compose version` |
| Git | ใช่ | clone จาก GitLab |
| พอร์ต HTTP (ค่าเริ่มต้น 80) | ใช่ | เปิด firewall ตามต้องการ |
| NVIDIA Driver + Container Toolkit | ถ้าใช้ GPU | แนะนำสำหรับ InsightFace |
| CPU-only | ได้ | ช้ากว่า GPU แต่รันได้ |

ตรวจบนเซิร์ฟเวอร์:

```bash
docker --version
docker compose version
git --version
nvidia-smi   # เฉพาะเครื่องที่มี GPU
```

---

## 2. Clone โปรเจกต์

```bash
sudo mkdir -p /opt
cd /opt
sudo git clone https://mygitplus.myhr.co.th/chanachai.o/facescan-timeattendance.git
sudo chown -R "$USER:$USER" facescan-timeattendance
cd facescan-timeattendance
```

ถ้า GitLab ต้องการ login:

```bash
git clone https://<username>@mygitplus.myhr.co.th/chanachai.o/facescan-timeattendance.git
```

---

## 3. ตั้งค่า environment

```bash
cp .env.example .env
nano .env
```

### ตัวแปรสำคัญ

| ตัวแปร | ตัวอย่าง | ความหมาย |
|--------|----------|----------|
| `POSTGRES_USER` | `dpu` | ชื่อ user DB |
| `POSTGRES_PASSWORD` | เปลี่ยนจากค่าเริ่มต้น | รหัส DB |
| `POSTGRES_DB` | `dpu` | ชื่อฐานข้อมูล |
| `HTTP_PORT` | `80` | พอร์ต nginx ฝั่งโฮสต์ |
| `SECRET_KEY` | สตริงสุ่มยาว | ใช้ใน production ต้องเปลี่ยน |
| `FACE_DEVICE` | `cuda:0` หรือ `cpu` | อุปกรณ์รัน InsightFace |
| `FACE_RECOGNITION_THRESHOLD` | `0.40` | ค่า cosine distance (ต่ำ = เข้ม) |
| `CHECK_IN_DEDUPE_SECONDS` | `300` | กันลงเวลาซ้ำ (วินาที) · `0` = ปิด |
| `IMAGE_BLUR_THRESHOLD` | `20.0` | เกณฑ์ blur ตอน enroll ที่คีออส / เพิ่มใบหน้า |
| `IMAGE_BLUR_THRESHOLD_IMPORT` | `0` | เกณฑ์ blur ตอน import Excel+ZIP · **`0` = ไม่ตัดรูปเบลอจากระบบอื่น** (ยังต้องเจอใบหน้า) |

ตัวอย่าง `.env` สำหรับ production เบื้องต้น:

```env
POSTGRES_USER=dpu
POSTGRES_PASSWORD=ใส่รหัสแข็งแรง
POSTGRES_DB=dpu
HTTP_PORT=80
SECRET_KEY=ใส่ค่าสุ่มยาวอย่างน้อย-32-ตัวอักษร
FACE_DEVICE=cuda:0
FACE_RECOGNITION_THRESHOLD=0.40
IMAGE_BLUR_THRESHOLD=20.0
IMAGE_BLUR_THRESHOLD_IMPORT=0
IMAGE_BRIGHTNESS_MIN=40
IMAGE_BRIGHTNESS_MAX=220
```

ไม่มี GPU ให้ตั้ง:

```env
FACE_DEVICE=cpu
```

---

## 4. Build และเปิดระบบ

ครั้งแรกจะใช้เวลานาน (ดาวน์โหลด image / build Angular / เตรียม InsightFace)

### 4.1 มี GPU (แนะนำ)

```bash
cd /opt/facescan-timeattendance
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

### 4.2 ไม่มี GPU (CPU)

```bash
cd /opt/facescan-timeattendance
# ตรวจว่าใน .env มี FACE_DEVICE=cpu
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build
```

### 4.3 ตรวจสถานะ

```bash
docker compose ps
docker compose logs -f api
```

กด `Ctrl+C` เมื่อ API พร้อม (healthcheck ผ่าน)

บริการหลักที่ขึ้น:

| Container (โดยประมาณ) | หน้าที่ |
|----------------------|---------|
| `dpu-db` | PostgreSQL + pgvector |
| `dpu-api` | FastAPI + InsightFace |
| `dpu-admin` | Web Admin + face kiosk (Angular) |
| `dpu-nginx` | Gateway พอร์ต `HTTP_PORT` |

---

## 5. Seed mock / demo data

หลัง stack ขึ้นแล้ว ให้ใส่ข้อมูลทดลอง (บริษัท, แผนก, พนักงาน, ตำแหน่ง, สถานที่, timestamp ตัวอย่าง ฯลฯ)

### 5.1 Seed อย่างเดียว (แนะนำ)

```bash
cd /opt/facescan-timeattendance

docker compose run --rm \
  -v "$(pwd)/API-Fast:/app" \
  --entrypoint python \
  api scripts/seed_demo_data.py --reset
```

`--reset` = **ล้างตารางแอปแล้วใส่ข้อมูล demo ใหม่** (ใช้เมื่อต้องการเริ่ม demo สะอาด)

ถ้าไม่ต้องการล้างทั้งก้อน (รันซ้ำแบบเติม) ให้ตัด `--reset` ออก — โดยทั่วไปตอนติดตั้งครั้งแรกให้ใช้ `--reset`

### 5.2 Seed + smoke test

```bash
cd /opt/facescan-timeattendance
chmod +x scripts/seed-and-test.sh
./scripts/seed-and-test.sh --reset
```

### 5.3 หมายเหตุเรื่องใบหน้า

- Seed จะใส่ **face embedding จำลอง** เพื่อให้โครงสร้างตารางครบ
- **ไม่ใช่ใบหน้าคนจริง** — ตอนใช้งานจริงต้องลงทะเบียนใบหน้าใหม่จาก Admin
- หลังย้ายจากระบบ `face_recognition` เก่า (128-d) ต้อง enroll ใหม่ทั้งหมด

---

## 6. เข้าใช้งานและบัญชีทดสอบ

แทน `<SERVER_IP>` ด้วย IP หรือโดเมนของเซิร์ฟเวอร์

| URL | บริการ |
|-----|--------|
| `http://<SERVER_IP>/` | Admin (Web-Manage) |
| `http://<SERVER_IP>/company/timestamp-face` | Kiosk ลงเวลาด้วยใบหน้า |
| `http://<SERVER_IP>/docs` | API Swagger / OpenAPI |
| `http://<SERVER_IP>/face/queue-stats` | สถานะคิว GPU (ถ้าเปิดใช้) |

### บัญชี demo หลัง seed

รหัสผ่านทุกบัญชี: **`Password123!`**

| Username | บทบาทโดยประมาณ | บริษัท |
|----------|----------------|--------|
| `sysadmin` | Admin ระบบ | — |
| `admin` | Admin บริษัท | Company A |
| `boss` | หัวหน้า | Company A |
| `emp1` | พนักงาน | Company A |
| `emp2` | พนักงาน | Company A |
| `emp3` | พนักงาน | Company A |
| `admin_b` | Admin บริษัท | Company B |
| `boss_b` | หัวหน้า | Company B |
| `staff1` / `staff2` | พนักงาน | Company B |

หน้า kiosk ลงเวลา (หลัง login เลือกบริษัท):

```text
http://<SERVER_IP>/#/company/timestamp-face
```

จัดการพนักงาน / ลงทะเบียนใบหน้า:

```text
http://<SERVER_IP>/#/company/company-emp
```

---

## 7. นำเข้าพนักงาน (Excel + รูป)

หน้าพนักงานบริษัท → ดาวน์โหลดเทมเพลต → กรอกชีต `Employees` → อัปโหลด `.xlsx` และถ้ามีรูปให้แนบ ZIP

API:

- `GET /employees/company/{companyId}/import-template`
- `POST /employees/company/{companyId}/import` (multipart `file` = Excel, `photos` = ZIP)

### เกณฑ์รูปใบหน้า

| ทาง | ตัวแปร | ค่าเริ่มต้น | ความหมาย |
|-----|--------|-------------|----------|
| คีออส / เพิ่มใบหน้าทีละคน | `IMAGE_BLUR_THRESHOLD` | `20.0` | ตัดรูปเบลอ |
| Import Excel+ZIP จากระบบอื่น | `IMAGE_BLUR_THRESHOLD_IMPORT` | `0` | **`0` = ไม่ตัดรูปเบลอ** (ยังต้องเจอใบหน้า) |

บนเซิร์ฟเวอร์หลัง `git pull` ให้มีใน `.env`:

```env
IMAGE_BLUR_THRESHOLD=20.0
IMAGE_BLUR_THRESHOLD_IMPORT=0
```

แล้ว rebuild:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build api nginx
```

ตรวจค่าใน container:

```bash
docker exec dpu-api python -c "from src.config.settings import settings; print(settings.IMAGE_BLUR_THRESHOLD, settings.IMAGE_BLUR_THRESHOLD_IMPORT)"
```

ต้องได้ `20.0 0.0`

### Import ซ้ำไฟล์เดิม

- อีเมลที่**ยังไม่มีในบริษัท** → สร้างใหม่ และลงทะเบียนใบหน้าได้
- อีเมลที่**มีอยู่แล้ว** → แถวนั้นเป็น error `Member is already registered in this company` ไม่แก้ข้อมูลเดิม และไม่ลองลงใบหน้าใหม่อีก
- แถวที่ fail จะไม่ทำให้แถวถัดไปพังทั้งไฟล์

### ไฟล์ใหญ่ (413 Request Entity Too Large)

`dpu-nginx` รับได้ถึง 500MB และ `/employees/.../import` timeout 1 ชั่วโมง

ถ้าเข้าผ่าน **HTTPS** (เช่น `https://face-in.myhr.co.th`) nginx ฝั่ง TLS ด้านนอกมักยังเป็น 1MB — วางไฟล์นี้แล้ว reload:

```bash
sudo cp docker/nginx/host-upload-limit.conf /etc/nginx/conf.d/dpu-upload-limit.conf
sudo nginx -t && sudo systemctl reload nginx
```

ตัวอย่าง site TLS ทั้งไฟล์อยู่ที่ `docker/nginx/tls-edge.example.conf`

---

## 8. อัปเดตโค้ด / คำสั่งใช้บ่อย

### อัปเดตจาก Git แล้ว rebuild

```bash
cd /opt/facescan-timeattendance
git pull

# GPU
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

# หรือ CPU
# docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build
```

### Log / สถานะ

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f admin nginx
```

### หยุดบริการ

```bash
docker compose down
```

### หยุดและลบ volume DB (ข้อมูลหายทั้งหมด)

```bash
docker compose down -v
```

หลัง `down -v` ต้อง `up --build` ใหม่ แล้ว seed อีกครั้ง

### Seed ใหม่หลังล้าง DB

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
docker compose run --rm \
  -v "$(pwd)/API-Fast:/app" \
  --entrypoint python \
  api scripts/seed_demo_data.py --reset
```

---

## 9. แก้ปัญหาเบื้องต้น

| อาการ | แนวทางตรวจ |
|-------|------------|
| เปิดเว็บไม่ได้ | `docker compose ps` ดูว่า `nginx` / `admin` Up หรือยัง · ตรวจ firewall พอร์ต `HTTP_PORT` |
| API 502 | `docker compose logs api` · restart nginx หลัง recreate api: `docker compose up -d --build nginx` |
| Upload / import พนักงานได้ 413 Request Entity Too Large | nginx ค่าเริ่มต้นรับได้แค่ 1m · วาง `docker/nginx/host-upload-limit.conf` เป็น `/etc/nginx/conf.d/dpu-upload-limit.conf` บน **nginx ฝั่ง TLS ด้านนอก** แล้ว `nginx -t && nginx -s reload` · rebuild `dpu-nginx` ด้วย (`client_max_body_size 500m`) |
| Seed ไม่ติด | API ต้อง healthy ก่อน · ดู log จากคำสั่ง `docker compose run ... seed_demo_data.py` |
| Face / enroll ที่คีออสบอก blur | แสงสว่างพอ · เกณฑ์คีออสคือ `IMAGE_BLUR_THRESHOLD` (ค่าเริ่มต้น 20) |
| Import พนักงานรูปจากระบบอื่นถูกตัด blur / แถวถัดไปพัง `greenlet_spawn` | ตั้ง `IMAGE_BLUR_THRESHOLD_IMPORT=0` ใน `.env` แล้ว rebuild `api` (+ `nginx` ถ้าอัปเดต timeout) · คีออสยังใช้เกณฑ์ 20 อยู่ |
| Build API ล้มเหลว `onnxruntime-gpu` No matching distribution | ดึงโค้ดล่าสุด (`git pull`) — โปรเจกต์ใช้ `onnxruntime-gpu==1.21.0` แล้ว (1.20.1 ถูกลบจาก PyPI) |
| ไม่มี GPU / CUDA error | ใช้ `docker-compose.cpu.yml` และ `FACE_DEVICE=cpu` |
| Login ไม่ได้หลัง seed | ใช้ username ในตารางด้านบน + รหัส `Password123!` |
| Git pull ไม่ได้ | ตรวจสิทธิ์ GitLab / credential บนเซิร์ฟเวอร์ |

---

## สรุปขั้นตอนสั้น (checklist)

```bash
# 1) clone
cd /opt && git clone https://mygitplus.myhr.co.th/chanachai.o/facescan-timeattendance.git
cd facescan-timeattendance

# 2) env
cp .env.example .env
# แก้ SECRET_KEY / รหัส DB / FACE_DEVICE

# 3) up (เลือก GPU หรือ CPU)
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

# 4) seed
docker compose run --rm \
  -v "$(pwd)/API-Fast:/app" \
  --entrypoint python \
  api scripts/seed_demo_data.py --reset

# 5) เปิดเบราว์เซอร์
# http://<SERVER_IP>/   login: admin / Password123!
```

---

*อัปเดตล่าสุดให้สอดคล้องกับ Docker stack: `db` · `api` · `admin` · `nginx`*

## 10. Deploy ร่วมกับ Face Core (BFF)

Production ที่ใช้ GPU 2 ใบให้ Face Core ถือ vision และ DPU เป็น BFF (CPU)

1. Clone `research/face-core` ไว้ข้าง ๆ repo นี้ (`/opt/face-core` และ `/opt/facescan-timeattendance`)
2. สร้าง network `docker network create face-net`
3. ตั้ง `SECRET_KEY` (DPU), `BOOTSTRAP_API_KEY` (face-core), `FACE_CORE_API_KEY` (ค่าเดียวกัน) ให้ยาวอย่างน้อย 16–32 ตัวอักษร
4. รัน `scripts/deploy-stack.sh` — ขึ้น face-core ก่อน (dual GPU + Redis) แล้วรอ `/v1/ready` จากนั้นขึ้น DPU ด้วย `docker-compose.face-core.yml` แล้วรอ `/ready`
5. ย้ายใบหน้าที่ enroll ไว้ใน DPU: `FACE_CORE_API_KEY=... scripts/migrate-faces.sh` ก่อนสลับ overlay ถ้ายังรันโหมด local อยู่ ไฟล์ mapping อยู่ที่ `backups/migration_mapping.json`
6. Rollback: เอา `-f docker-compose.face-core.yml` ออก แถว `face_encoding` ใน DPU ยังอยู่เพราะสคริปต์ migrate ไม่ลบ

