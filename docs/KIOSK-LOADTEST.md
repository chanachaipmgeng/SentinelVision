# โหลดเทสหน้า Kiosk (local → server)

คู่มือนี้ใช้ชุดสคริปต์ใน [`scripts/kiosk-load/`](../scripts/kiosk-load/) เพื่อจำลองหลายจอ kiosk ผ่าน WebSocket `/face/ws/kiosk` รันจากเครื่อง local ก่อน แล้วค่อยชี้ URL เดียวกันไปยังเซิร์ฟเวอร์จริง

คอขวดอยู่ที่คิว GPU (InsightFace ในตัว หรือ Face Core BFF) ไม่ใช่หน้า Angular อย่ายิงแค่ GET หน้าเว็บ หรือ HTTP `check-in-walkby` เป็นเทสหลัก

เอกสารที่เกี่ยวข้อง: [SETUP.md](SETUP.md) · [ARCHITECTURE.md](ARCHITECTURE.md) · [API.md](API.md)

---

## 1. เตรียมสแตก local

```bash
# จากรากโปรเจกต์ — พอร์ตเริ่มต้น BFF/dev มักเป็น 8880 (ดู HTTP_PORT ใน .env)
curl -s http://localhost:8880/health
curl -s http://localhost:8880/ready

# Seed เดโม (รหัสทุกบัญชี: Password123!)
docker compose run --rm -v ./API-Fast:/app --entrypoint python api scripts/seed_demo_data.py --reset
```

บัญชีที่ใช้โหลดเทส: `admin` (บริษัท Company A)  
Company id เดโม: `11111111-1111-1111-1111-111111111111`  
Member emp1: `aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaa4`

ตรวจสอบว่า WS ผ่าน nginx ได้: `ws://localhost:8880/face/ws/kiosk`

---

## 2. ติดตั้งสคริปต์บนเครื่อง (venv)

ไม่ติดตั้ง InsightFace — ใช้แค่ `httpx` + `websockets`

```bash
cd scripts/kiosk-load
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# Linux / macOS
# source .venv/bin/activate

pip install -r requirements.txt

# รหัสผ่านไม่ฝังในไฟล์ — ใส่ผ่าน env
# Windows PowerShell
$env:KIOSK_LOAD_USER = "admin"
$env:KIOSK_LOAD_PASSWORD = "Password123!"
# Linux / macOS
# export KIOSK_LOAD_USER=admin
# export KIOSK_LOAD_PASSWORD='Password123!'
```

Seed ให้ `face_encoding` เป็นเวกเตอร์สังเคราะห์ identify ด้วยรูปจริงจะไม่ match ต้อง enroll รูปตัวอย่างก่อนด้วย `--prepare` (ดาวน์โหลดครั้งเดียวไป `.cache/` ที่ gitignore แล้ว)

```bash
python kiosk_load.py --prepare --profile idle --kiosks 1 --hold 5
```

---

## 3. ลำดับการทดสอบบน local

### 3.1 เทสฟังก์ชัน 1 จอ (สั้น)

```bash
python kiosk_load.py --profile idle --kiosks 1 --hold 15 --jsonl results-idle.jsonl
```

ควรเห็น `session` และ `detect` มีค่า p50/p95 และ `dropped_rate` ต่ำ

### 3.2 โปรไฟล์ idle แล้ว rush (เพิ่มจำนวนจอ)

เปิดเทอร์มินัลที่สองสำหรับโพลคิว:

```bash
python poll_queue.py --csv queue.csv
```

เทอร์มินัลแรก:

```bash
# กล้องว่าง / โหลด detect
python kiosk_load.py --profile idle --kiosks 1,2,4 --hold 60 --jsonl results-idle.jsonl --fail-on-slo

# ชั่วโมงเร่งด่วน: detect + identify + checkin
python kiosk_load.py --profile rush --kiosks 1,2,4 --hold 60 --jsonl results-rush.jsonl
```

ถ้ามี GPU บนโฮสต์: เปิด `nvidia-smi -l 1` คู่กัน

เปิดเบราว์เซอร์จริงหนึ่งแท็บที่ `http://localhost:8880/company/timestamp-face` (ล็อกอินแล้ว) ระหว่างที่สคริปต์วิ่ง — ดูว่ากรอบหน้ากระพริบหรือข้อความเช็คอินช้า

### 3.3 จังหวะที่สคริปต์จำลอง

| พฤติกรรม | ค่า |
|----------|-----|
| `detect` | ทุก ~90 ms ต่อจอ |
| `identify` (rush) | ห่างอย่างน้อย 1.2 s ต่อ track, ค้างได้สูงสุด 2 งานต่อจอ |
| `checkin` (rush) | ค้างได้สูงสุด 3 งานต่อจอ |
| `--faces-per-kiosk N` | mosaic N ใบหน้าในเฟรม detect + ยิง identify/check-in ตามเพดาน UI |
| พิกัด | `13.7563, 100.5018` (ใน geofence เดโม) |

ตัวอย่างหลายจอ × หลายคนต่อจอ:

```bash
# 2 จอ × 3 คน/จอ (identify≤2, checkin≤3 ตาม UI)
python kiosk_load.py --profile rush --kiosks 1,2 --faces-per-kiosk 3 --hold 45 --jsonl results-multi.jsonl
```

---

## 4. วิธีอ่านผล

### จาก `kiosk_load.py`

| ตัวชี้วัด | ความหมาย |
|-----------|----------|
| `session` p95 | เวลาถึง `session_ok` หลังส่ง JWT |
| `detect` p50 / p95 | RTT ของเฟรม detect |
| `detect` `dropped_rate` | สัดส่วนที่เซิร์ฟเวอร์ตอบ `dropped: true` เพราะคิวถึง `WS_QUEUE_BACKPRESSURE` (ค่าเริ่มต้น 32) |
| `identify` / `checkin` | RTT ของงานจับคู่ / ลงเวลา |
| `checkin` `checked_in` vs `duplicate` | คนเดิมภายใน ~300 s (`CHECK_IN_DEDUPE_SECONDS`) จะได้ `duplicate` — **อย่านับเป็นความเร็วของ GPU** |

`--fail-on-slo` จะ exit 1 เมื่อ (บนขั้นจำนวนจอสุดท้าย):

- `session` p95 > 500 ms
- `detect` p95 > 550 ms (ใกล้ `trackMissTtlMs` ของ UI — กรอบจะดับถ้าช้ากว่านี้)
- อัตรา `dropped` > 5%

### จาก `poll_queue.py`

| ฟิลด์ | ความหมาย |
|-------|----------|
| `pending` | งานค้างในคิว — ค้างสูงใกล้ 32 แปลว่าคิวอิ่ม |
| `active` | งานที่กำลังรัน — ควรใกล้จำนวน device ใน `FACE_DEVICES` |
| `completed` / `delta/s` | throughput จริง (งานเสร็จต่อวินาที) |
| `source` | `face-core` เมื่อ BFF; ไม่มีฟิลด์นี้หรือค่าอื่น = คิว local |

`GET /metrics` นับแค่ HTTP ไม่นับเฟรม WebSocket — ใช้ดูว่า API ยังตอบได้เท่านั้น อย่าใช้เป็นผลโหลดเทส kiosk

---

## 5. ผลอ้างอิงจาก local (ก่อนไป server)

สภาพแวดล้อมที่วัด (2026-09-22):

- สแตก `docker compose` + `docker-compose.gpu.yml`, `HTTP_PORT=8880`
- GPU 1 ใบ: `FACE_DEVICES=cuda:0` (RTX 5050 Laptop), คิว local InsightFace
- Seed เดโม + `--prepare` enroll emp1 ด้วยรูปตัวอย่าง
- hold 25–30 s ต่อขั้น; SLO: session p95 ≤ 500 ms, detect p95 ≤ 550 ms, dropped ≤ 5%

### สรุปความจุ

| โปรไฟล์ | ยังใช้ได้ | เริ่มแย่ (กรอบ/เช็คอินช้า) | พังชัด (drop / p95 พุ่ง) |
|---------|-----------|------------------------------|---------------------------|
| **idle** (detect) | ≤ **16** จอ | **24–32** | ≥ **48** |
| **rush** (detect+identify+checkin) | **1–2** จอ | **4** | ≥ **8–12** |

### Idle (detect)

| จอ | detect p95 | dropped |
|----|------------|---------|
| 1 | ~64 ms | 0% |
| 8 | ~91 ms | 0% |
| 16 | ~233 ms | 0% |
| 24 | ~376 ms | 0% |
| 32 | ~742 ms | 0% (เกิน trackMissTtl 550 ms) |
| 48 | ~776 ms | ~37% |
| 64 | ~893 ms | ~48% |

### Rush

| จอ | detect p95 | checkin p95 | dropped |
|----|------------|-------------|---------|
| 1 | ~227 ms | ~310 ms | 0% |
| 2 | ~446 ms | ~432 ms | 0% |
| 4 | ~1000 ms | ~1068 ms | 0% |
| 8 | ~2052 ms | ~2014 ms | 0% |
| 12 | ~2937 ms | ~3020 ms | ~46% |

ข้อสังเกต:

- `poll_queue` แสดง `active` ≈ 1 ตรงจำนวน GPU; throughput ประมาณ 30–50 งาน/วินาทีตอนอิ่ม
- rush ใช้หน้าคนเดิมซ้ำ → `duplicate` สูงภายใน `CHECK_IN_DEDUPE_SECONDS` — แยกจากเช็คอินที่เขียน timestamp จริง
- ตัวเลขนี้เป็น **ฐานอ้างอิง laptop 1 GPU** — บนเซิร์ฟเวอร์จริงให้รันชุดเดิมแล้วเทียบ ไม่สมมติว่าความจุเท่ากัน (GPU ต่างรุ่น / Face Core BFF / จำนวน `FACE_DEVICES`)

แผนรันบน server: เริ่ม idle `1,2,4` แล้ว rush `1,2` ก่อนค่อยเพิ่มเมื่อยังไม่เกิน SLO

---

## 5b. ผลบน `face-in.myhr.co.th` (baseline ก่อนจูนซอฟต์แวร์)

วัด 2026-09-23 จากโฮสต์ → `https://face-in.myhr.co.th` (JWT บริษัททดสอบ, `--faces-per-kiosk 3`, hold 30 s):

| โปรไฟล์ | ยังใช้ได้ | เริ่มแย่ (เกิน detect p95 550 ms) | พังชัด |
|---------|-----------|-------------------------------------|--------|
| **idle** | ≤ **16** จอ (p95 ~505 ms) | — | ยังไม่ drop ถึง 16 |
| **rush** | **1** จอ (p95 ~419 ms) | **2** จอ (p95 ~774 ms) | **4–6** จอ (1.6–2.5 s) |

`GET /face/queue-stats`: `workers=1`, `source` local (ไม่มี `devices` ใน build ที่วัด), `active` ≤ 1, throughput rush ~12 งาน/s, pending สูงสุด ~27 ที่ 6 จอ

ตรวจ CUDA บนเซิร์ฟเวอร์ (host nginx ดึง `/ready` ไป SPA — อย่าใช้โดเมนสำหรับ `/ready`):

```bash
docker logs dpu-api 2>&1 | grep -E "InsightFace|CUDAExecutionProvider|falling back to CPU"
nvidia-smi -L
# ระหว่างโหลดเทส: nvidia-smi -l 1  — util ควรขึ้น ถ้าติด 0% ตลอด = ยังไม่ใช้ GPU
```

---

## 5c. จูนหลายบริษัทบนเซิร์ฟเวอร์เดียว

ซอฟต์แวร์ (deploy แล้ว rebuild `api` + `admin`):

| การจูน | ผลที่คาด |
|--------|----------|
| Detect ใช้ `FACE_DETECT_DET_SIZE=320` + decode นอก GPU worker | เฟรม detect ถูกลง ~3× |
| Walk-by / identify→checkin cache (`FACE_IDENTIFY_CACHE_SECONDS`) | ลงเวลาเหลือ 1 รอบ GPU ต่อคนเมื่อ identify เพิ่งผ่าน |
| คิว priority `checkin > identify > detect` + round-robin ต่อบริษัท | บริษัทเล็กไม่ถูก starve; check-in ไม่รอ detect ของบริษัทอื่น |
| `FACE_DETECT_STALE_MS` + `WS_DETECT_MIN_INTERVAL_MS` ฝั่ง server | ทิ้งเฟรมเก่า / ผ่อนจอว่าง |
| Kiosk `nextCaptureInterval(queuePending)` + identify เฉพาะ track ที่ยังไม่มี label | ลดยิงซ้ำตอนคิวตัน |

ฮาร์ดแวร์ (`.env` แล้ว `docker compose ... up -d --build api`):

```bash
# การ์ดสองใบ
FACE_DEVICES=cuda:0,cuda:1
FACE_GPU_WORKERS=2

# ทดลองซ้อน worker 2 บนการ์ดเดียว (เฉพาะเมื่อ nvidia-smi util < ~60% หลังจูนซอฟต์แวร์)
# FACE_DEVICES=cuda:0
# FACE_GPU_WORKERS=2
```

หลัง deploy ให้วัดซ้ำ:

```bash
python poll_queue.py --base-url $env:KIOSK_LOAD_BASE_URL --csv queue-post-tune.csv
python kiosk_load.py --faces-per-kiosk 3 --profile idle --kiosks 8,16,32 --hold 30 --jsonl results-idle-post.jsonl
python kiosk_load.py --faces-per-kiosk 3 --profile rush --kiosks 2,4,8,16 --hold 30 --jsonl results-rush-post.jsonl
# Fairness: สองเทอร์มินัล คนละ company-id พร้อมกัน (rush --kiosks 4)
```

เป้าหลังจูนซอฟต์แวร์บน 1 GPU: rush ~8–12 จอ; + GPU ใบที่ 2: ~16–24 จอ

หน่วยทดสอบคิว (ไม่ต้องมี GPU): `cd API-Fast && pytest tests/test_face_gpu_queue.py` — ตรวจ priority / round-robin / stale drop

**สถานะ remasure บน face-in หลังจูน:** ต้อง `git pull` + rebuild `api` และ `admin` บน `10.50.0.117` ก่อน แล้วรันคำสั่งด้านบน เทียบกับ baseline ใน §5b (ไฟล์อ้างอิง: `scripts/kiosk-load/.cache/results-face-in-{idle,rush}.jsonl`, `queue-face-in-both.csv`)

### ผลวัดซ้ำ 2026-09-23 (หลัง pull — ยัง workers=1)

ชี้ `http://10.50.0.117:8880` เพราะ `https://face-in.myhr.co.th` ยัง 502 (host TLS ชี้พอร์ตผิด / nginx ใน compose ฟัง `8880`)

| สภาพ | ค่า |
|------|-----|
| `queue-stats` | `workers=1`, ไม่มี `devices` / `pendingByKind` |
| log api | `Face GPU queue started workers=1 queue_size=64` (ยังไม่เห็น log แบบ `devices=...`) |
| poll | `active` ≤ 1 ตลอด |

**Idle** (3 คน/จอ, hold 30s) vs baseline §5b

| จอ | baseline detect p95 | รอบนี้ | หมายเหตุ |
|----|---------------------|--------|----------|
| 8 | (ไม่วัดใน §5b; ใกล้ ๆ 309 ที่ 8 จอเดิม) | **415 ms** | ยังใต้ 550 |
| 16 | ~505 ms | **805 ms** | แย่ลง / เกิน SLO |
| 32 | — | **2034 ms** | ไม่ไหว |

**Rush** (3 คน/จอ) vs baseline

| จอ | baseline detect p95 | รอบนี้ | หมายเหตุ |
|----|---------------------|--------|----------|
| 2 | ~774 ms | **~4.5 s** | แย่ลงชัด |
| 4 | ~1.6 s | **~8.2 s** | คิวตัน |
| 8–16 | — | 16–18 s+ | ไม่ใช้งานได้ |

สรุป: การ์ดสองใบ / โค้ดจูน **ยังไม่ทำงานใน runtime** — ต้องตั้ง `.env` + rebuild ให้ `workers≥2` และให้ log มี `devices=` ก่อนวัดซ้ำอีกรอบ

### ผลวัดซ้ำ 2026-09-23 (หลังตั้ง dual GPU + rebuild)

ชี้ `http://10.50.0.117:8880` · โฮสต์มี **2× Quadro RTX 5000 16 GB** · `.env`: `FACE_DEVICES=cuda:0,cuda:1` · `FACE_GPU_WORKERS=2`

| สภาพ | ค่า |
|------|-----|
| log api | `Face GPU queue started workers=2 … devices=['cuda:0', 'cuda:1']` |
| `queue-stats` | `devices=cuda:0,cuda:1`, `active` สูงสุด **2** |
| nvidia-smi ระหว่างโหลด | GPU0 util สูงสุด ~87% / mem ~15 GB · GPU1 util สูงสุด ~71% / mem ~12 GB |

**Idle** (3 คน/จอ, hold 30s) vs รอบ workers=1 ด้านบน

| จอ | workers=1 detect p95 | dual GPU | หมายเหตุ |
|----|----------------------|----------|----------|
| 8 | 415 ms | **352 ms** | ดีขึ้น |
| 16 | 805 ms | **606 ms** | ดีขึ้น (ยังเกิน SLO 550 นิด) |
| 32 | 2034 ms | **1063 ms** | ดีขึ้น ~2× |

**Rush** (3 คน/จอ) vs รอบ workers=1

| จอ | workers=1 detect p95 | dual GPU | หมายเหตุ |
|----|----------------------|----------|----------|
| 2 | ~4.5 s | **288 ms** | ใต้ SLO |
| 4 | ~8.2 s | **447 ms** | ใต้ SLO |
| 8 | 16 s+ | **1296 ms** | ดีขึ้นมาก แต่เกิน SLO / drop ~56% |
| 16 | 16–18 s+ | **2478 ms** | ยังไม่ไหวใช้งานจริง |

สรุปใช้งาน: **rush สบายที่ 2–4 จอ (3 คน/จอ)**; idle ~8–16 จอ · ไฟล์: `results-dual-retest-{idle,rush}.jsonl`, `queue-dual-retest.csv`

รายงาน capacity แบบละเอียด (อัตราเต็ม, workers=2): **[KIOSK-LOADTEST-WORKERS2-CAPACITY.md](KIOSK-LOADTEST-WORKERS2-CAPACITY.md)** — เพดาน SLO: idle ×3 = **12 จอ**, rush ×3 = **5 จอ**, rush ×1 = **8 จอ**

### ผล saturation 2026-09-23 (dual API + เฟรมสมจริง)

หลังพบว่า GPU1 ว่างจริง (device ไม่ถูก pin) และ process เดียวติด GIL จึงแยกเป็น `dpu-api` / `dpu-api-gpu1` + nginx `least_conn` และย่อเฟรมเทสให้เท่า kiosk จริง (~1280 px, q70)

| โปรไฟล์ | เพดาน SLO (รอบ saturation) |
|---------|----------------------------|
| idle ×3 | **24 จอ** |
| rush ×3 | **6 จอ** (MARGIN ที่ 8–12) |
| rush ×1 | **12 จอ** (MARGIN ที่ 16) |

รายละเอียด + เกณฑ์ตัดสิน face-core: **[KIOSK-LOADTEST-SATURATION.md](KIOSK-LOADTEST-SATURATION.md)**

รัน dual-GPU stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
# ตรวจ: dpu-api, dpu-api-gpu1, nginx (mount default.dual-gpu.conf)
```

Loadgen บน server (ตัด LAN/Windows ออก):

คอนเทนเนอร์ `loadgen` รันเป็น uid `10001` (non-root). ไดเรกทอรีผลบนโฮสต์
`scripts/kiosk-load/.cache/results` ต้องเขียนได้โดย uid 10001
(เช่น `mkdir -p scripts/kiosk-load/.cache/results && chown -R 10001:10001 scripts/kiosk-load/.cache`).

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml \
  -f docker-compose.loadtest.yml --profile loadtest run --rm \
  -e KIOSK_LOAD_USER=... -e KIOSK_LOAD_PASSWORD=... \
  loadgen --profile idle --kiosks 1,4,8 --hold 20 --jsonl /results/idle.jsonl
```

Checklist บนเซิร์ฟเวอร์:

```bash
# 1) ใน .env
grep -E 'FACE_DEVICE|FACE_DEVICES|FACE_GPU|HTTP_PORT' .env
# ควรมี:
# FACE_DEVICES=cuda:0,cuda:1
# FACE_GPU_WORKERS=2
# HTTP_PORT=80   # ถ้า host TLS proxy ไปที่ :80 — หรือชี้ proxy ไป :8880

# 2) ยืนยันการ์ด
sudo nvidia-smi -L

# 3) rebuild ให้ได้โค้ดใหม่ (อย่าแค่ recreate image เก่า)
sudo docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build api admin nginx

# 4) ตรวจ
sudo docker logs dpu-api 2>&1 | grep -E 'Face GPU queue|InsightFace|CUDA'
# ต้องเห็น workers=2 และ CUDAExecutionProvider / devices=['cuda:0','cuda:1']
```

---

## 6. ก่อนชี้เซิร์ฟเวอร์จริง

ชุดสคริปต์เดิม เปลี่ยนแค่ URL และบัญชี:

```bash
$env:KIOSK_LOAD_USER = "<company-admin-test>"
$env:KIOSK_LOAD_PASSWORD = "<from-secret-store>"
$env:KIOSK_LOAD_BASE_URL = "https://attendance.example.com"

python kiosk_load.py --prepare `
  --company-id "<test-company-uuid>" `
  --member-id "<test-member-uuid>" `
  --profile idle --kiosks 1 --hold 10

python poll_queue.py --base-url $env:KIOSK_LOAD_BASE_URL --csv queue-prod.csv

python kiosk_load.py --profile rush --kiosks 1,2 --hold 60 `
  --company-id "<test-company-uuid>" `
  --jsonl results-prod.jsonl
```

ข้อควรระวัง:

1. ใช้ **บริษัททดสอบ** และบัญชีทดสอบเท่านั้น — อย่าใช้รหัสเดโมบน production
2. **อย่ารันตอนมีพนักงานลงเวลาจริง** — `checkin` เขียน timestamp และรูป punch จริง
3. คนเดิมจะได้ `duplicate: true` ภายในหน้าต่าง dedupe — แยกรายงานจากเช็คอินที่บันทึกใหม่
4. เริ่มจากจำนวนจอน้อย แล้วค่อยเพิ่มเมื่อ `pending` ยังไม่ค้างที่เพดาน backpressure
5. ผ่าน HTTPS ใช้ `https://...` — สคริปต์แปลงเป็น `wss://.../face/ws/kiosk` เอง

---

## 7. แก้ปัญหาเบื้องต้น

| อาการ | ตรวจ |
|-------|------|
| `Set KIOSK_LOAD_USER...` | ยังไม่ได้ใส่ env |
| login 401 | seed แล้วหรือยัง · รหัส `Password123!` บน local |
| `session failed` / Invalid token | JWT หมดอายุ · รันใหม่ให้ login อีกครั้ง |
| detect ไม่มี faces | รูปแคชเสีย — ลบ `scripts/kiosk-load/.cache/` แล้ว `--prepare` ใหม่ |
| identify ไม่ match | ลืม `--prepare` หรือ member คนละบริษัท |
| checkin error GPS | พิกัด `0,0` — ใช้ค่าเริ่มต้นของสคริปต์หรือส่ง `--lat` / `--lon` |
| `face_core_down` | Face Core ล่ม / circuit เปิด — ดู `/ready` และ log ของ face-core |
| pending สูงตลอด | ลดจำนวนจอ หรือเพิ่ม GPU (`FACE_DEVICES`) |
| 502 หลัง recreate container | rebuild/restart nginx (DNS upstream) |

Smoke เฟรมเดียวภายใน compose (ไม่ใช่โหลดเทส): `API-Fast/scripts/smoke_ws_kiosk.py`

---

## 8. People counting GPU gate (Phase 6D)

People counting ใช้ **YOLOv8n ONNX บน onnxruntime-gpu ในเลนคนละคิวกับ InsightFace** (`WORKER_PEOPLE_*`) และจะ pause เมื่อ kiosk pending ≥ `WORKER_PEOPLE_PAUSE_WHEN_KIOSK_PENDING` (default 4). ค่าเริ่มต้น `peopleEnabled=false` จนกว่าจะวาด ROI บนกล้อง

**เกณฑ์ที่ล็อกไว้:** kiosk checkin+identify p95 ถดถอยไม่เกิน **≤10%** เมื่อเปิด people

```bash
# เอกสารเกตอย่างเดียว
python scripts/kiosk-load/people_gpu_sizing.py --dry-doc

# เทียบ baseline vs people (ต้องมีโหลด kiosk พร้อมกัน)
$env:KIOSK_LOAD_USER = "admin"
$env:KIOSK_LOAD_PASSWORD = "Password123!"
python scripts/kiosk-load/people_gpu_sizing.py --base-url http://localhost:8880 --hold 90 --phase compare

# ดาวน์โหลด/export น้ำหนัก YOLO (ครั้งเดียว)
python scripts/download_yolov8n_onnx.py --out API-Fast/models/yolov8n.onnx
```

Exit code `2` = gate fail (regression > 10%).
