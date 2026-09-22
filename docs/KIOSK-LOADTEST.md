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
