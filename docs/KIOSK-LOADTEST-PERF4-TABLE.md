# Perf round 4 — hexa API (3 process/GPU) workers=3 · saturation / ไม่สน UX

## สภาพแวดล้อม

- Host: `10.50.0.117` · URL: `http://10.50.0.117:8880`
- GPUs: 2× Quadro RTX 5000 16 GB · 32 core · 436 GB RAM
- Layout: `docker-compose.gpu.yml` + `gpu-x2.yml` + `gpu-x3.yml`
  - GPU0: `dpu-api` + `dpu-api-gpu0b` + `dpu-api-gpu0c`
  - GPU1: `dpu-api-gpu1` + `dpu-api-gpu1b` + `dpu-api-gpu1c`
  - nginx: `default.hexa-gpu.conf` (6 upstreams, `least_conn`)
- `FACE_GPU_WORKERS=3` → รวม **18 GPU worker threads** (9/การ์ด)
- Client: เฟรมสมจริง 1280 px JPEG q70 · detect ทุก ~90 ms · ไม่มี motion gating
- วัด: 24 ก.ย. 2026 ~01:14–01:37 (UTC+7)
- Host metrics (ช่วง busy, SM>5%): GPU0/1 SM avg ~21% (max ~46–48%) · CPU ต่อ process avg ~75–90% (max ~150–245%) · VRAM ~1.8–2.0 GB/process (~5.5–5.7 GB/การ์ด)

## สองนิยามเพดาน

| นิยาม | เกณฑ์ | ใช้เมื่อ |
|-------|--------|---------|
| **UX / SLO** | detect p95 ≤ 550 ms · drop ≤ 5% · session errors ≈ 0 | ติดตั้งจริง |
| **Saturation / ไม่สน UX** | ระบบยังตอบ (drop ≈ 0) แม้ latency 1–2 วินาที; หยุดเมื่อ WS session พังจำนวนมาก | หาขีดจำกัดฮาร์ดแวร์ |

## สรุปเทียบรอบ 3 (quad = 4 process) vs รอบ 4 (hexa = 6 process)

| โปรไฟล์ | Quad SLO OK | Hexa SLO OK | Hexa saturation (ยังไม่พัง) | ข้อสังเกต |
|---------|-------------|-------------|------------------------------|-----------|
| idle ×3 | 48 จอ | **≥ 96 จอ** (112+ เริ่มมี session error) | **~160 จอ** detect ยัง ~506 ms แต่ session พัง ~15% | hexa ชนะชัด — กระจาย GIL/WS |
| rush ×3 | **24 จอ** (514 ms) | **16 จอ** (321 ms); 24 = 674 ms FAIL | 56 จอ p95 ~1.6–1.8 s, drop 0% | hexa **แย่กว่า** quad ที่ UX |
| rush ×1 | **32 จอ** (429 ms) | **~24–32 จอ** (24=405 OK; 32≈544 ขอบ) | 80 จอ p95 ~1.8 s, drop 0% | hexa ไม่ช่วย / แย่ลงเล็กน้อย |

**สรุปสั้น:** เพิ่มเป็น 3 process/GPU ช่วยจอว่างจำนวนมาก แต่ในชั่วโมงเร่งด่วน (identify+check-in) latency แย่ลงเพราะแย่ง GPU + DB มากขึ้น — **ถ้าสนใจ UX ให้คง quad; ถ้าอยากดันจำนวนจอว่างสูงสุด ค่อยใช้ hexa**

## Idle × 3 คน/จอ

| จอ | detect p50 | detect p95 | drop | session errors | verdict (SLO) |
|----|------------|------------|------|----------------|---------------|
| 32 | 65 ms | 119 ms | 0.2% | 0 | OK |
| 48 | 98 ms | 178 ms | 0.0% | 0 | OK |
| 64 | 161 ms | 305 ms | 0.0% | 0 | OK |
| 80 | 165 ms | 295 ms | 0.0% | 0 | OK |
| 96 | 198 ms | 352 ms | 0.0% | 0 | OK |
| 112 | 229 ms | 416 ms | 0.0% | 5 / 112 | OK* (handshake เริ่มพัง) |
| 128 | 257 ms | 465 ms | 0.0% | 6 / 128 | OK* |
| 160 | 285 ms | 506 ms | 0.0% | 25 / 160 | OK* / sat ceiling |

\* detect ของ session ที่เปิดได้ยังผ่าน SLO แต่ `Invalid session payload` เพิ่มตามจำนวนจอ → เพดานจริงของ concurrent WS ≈ **96–112 จอ**

## Rush × 3 คน/จอ

| จอ | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|------------|------------|------|--------------|-------------|---------|
| 16 | 197 ms | 321 ms | 0.6% | 417 ms | 334 ms | OK |
| 24 | 446 ms | 674 ms | 0.0% | 748 ms | 660 ms | FAIL (vs quad OK 514) |
| 32 | 592 ms | 871 ms | 0.0% | 947 ms | 827 ms | FAIL |
| 40 | 922 ms | 1249 ms | 0.0% | 1145 ms | 1273 ms | FAIL |
| 48 | 1272 ms | 1605 ms | 0.0% | 1584 ms | 1598 ms | FAIL |
| 56 | 1316–1460 ms | 1631–1823 ms | 0.0% | 1436–1762 ms | 1667–1802 ms | FAIL / sat |

ที่ 56 จอ: identify/check-in error สูงขึ้น แต่ **ยังไม่ทิ้งเฟรม detect** — ระบบช้า ไม่พัง

## Rush × 1 คน/จอ

| จอ | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|------------|------------|------|--------------|-------------|---------|
| 24 | 225 ms | 405 ms | 0.0% | 447 ms | 432 ms | OK |
| 32 | 295 ms | 544 ms | 0.0% | 567 ms | 571 ms | OK (ขอบ; quad ดีกว่าที่ 429) |
| 48 | 643 ms | 964 ms | 0.0% | 803 ms | 930 ms | FAIL |
| 64 | 1054 ms | 1389 ms | 0.0% | 1099 ms | 1379 ms | FAIL |
| 80 | 1477 ms | 1767 ms | 0.0% | 1209 ms | 1659 ms | FAIL / sat |

## ข้อแนะนำ

1. **Production / เร่งด่วน:** ถอยกลับเป็น **quad (2 process/GPU)** — rush×3 ได้ 24 จอที่ UX ดีกว่า
2. **ทดลองจำนวนจอว่างสูงสุดบนเครื่องนี้:** hexa รองรับ idle ~**96 จอ** แบบลื่น; เกิน 112 ต้องทน session fail
3. **ไม่สน UX เลย:** เครื่องนี้ยัง “รับงาน” ได้ถึง ~**56 จอ rush×3** หรือ ~**80 จอ rush×1** ที่ latency 1.5–1.8 s (drop 0%) — ไม่แนะนำใช้งานจริง
4. อย่าเพิ่มเป็น 4 process/GPU โดยไม่วัด — rush น่าจะแย่ลงอีก; ถ้าจะดันต่อแนะนำลด `FACE_GPU_WORKERS` เป็น 2 พร้อม hexa แล้ว A/B
5. คอขวดถัดไปที่ saturation: **WS session accept + DB/check-in** ไม่ใช่ GPU (SM ยัง ~21%)

## ไฟล์ดิบ

- `scripts/kiosk-load/.cache/results-hexa-idle.jsonl`
- `scripts/kiosk-load/.cache/results-hexa-rush3.jsonl`
- `scripts/kiosk-load/.cache/results-hexa-rush1.jsonl`
- `scripts/kiosk-load/.cache/hostmetrics-hexa.csv`
