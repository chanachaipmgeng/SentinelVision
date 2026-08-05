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
7. [อัปเดตโค้ด / คำสั่งใช้บ่อย](#7-อัปเดตโค้ด--คำสั่งใช้บ่อย)
8. [แก้ปัญหาเบื้องต้น](#8-แก้ปัญหาเบื้องต้น)

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
| `IMAGE_BLUR_THRESHOLD` | `20.0` | เกณฑ์ blur ตอน enroll |

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
| `dpu-admin` | Web Admin (Angular) |
| `dpu-mobile` | Web Mobile (Angular) |
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
- **ไม่ใช่ใบหน้าคนจริง** — ตอนใช้งานจริงต้องลงทะเบียนใบหน้าใหม่จาก Admin หรือ Mobile
- หลังย้ายจากระบบ `face_recognition` เก่า (128-d) ต้อง enroll ใหม่ทั้งหมด

---

## 6. เข้าใช้งานและบัญชีทดสอบ

แทน `<SERVER_IP>` ด้วย IP หรือโดเมนของเซิร์ฟเวอร์

| URL | บริการ |
|-----|--------|
| `http://<SERVER_IP>/` | Admin (Web-Manage) |
| `http://<SERVER_IP>/mobile/` | Mobile |
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

## 7. อัปเดตโค้ด / คำสั่งใช้บ่อย

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

## 8. แก้ปัญหาเบื้องต้น

| อาการ | แนวทางตรวจ |
|-------|------------|
| เปิดเว็บไม่ได้ | `docker compose ps` ดูว่า `nginx` / `admin` Up หรือยัง · ตรวจ firewall พอร์ต `HTTP_PORT` |
| API 502 | `docker compose logs api` · restart nginx หลัง recreate api: `docker compose up -d --build nginx` |
| Upload ได้ 413 Request Entity Too Large | เพิ่ม `client_max_body_size 100m;` ใน **nginx ฝั่ง TLS ด้านนอก** (ค่าเริ่มต้นมักเป็น 1m) แล้ว `nginx -s reload` · rebuild `dpu-nginx` ด้วย |
| Seed ไม่ติด | API ต้อง healthy ก่อน · ดู log จากคำสั่ง `docker compose run ... seed_demo_data.py` |
| Face / enroll บอก blur | แสงสว่างพอ · เกณฑ์อยู่ใน `.env` (`IMAGE_BLUR_THRESHOLD`) |
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

*อัปเดตล่าสุดให้สอดคล้องกับ Docker stack: `db` · `api` · `admin` · `mobile` · `nginx`*
