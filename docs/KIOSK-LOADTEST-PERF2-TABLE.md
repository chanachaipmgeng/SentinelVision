# Perf round 2 — dual API workers=3 + det@320 in-memory identify

## สภาพแวดล้อม

- Host: `10.50.0.117` · URL: `http://10.50.0.117:8880`
- GPUs: 2× Quadro RTX 5000 16 GB
- Dual API: `dpu-api` (GPU0) + `dpu-api-gpu1` (GPU1) · `FACE_GPU_WORKERS=3` each
- Client: realistic frames (1280 px, JPEG q70) · detect interval 90 ms
- SLO: session p95 ≤ 500 ms · detect p95 ≤ 550 ms · dropped ≤ 5%
- Code: 9d407e2d (perf round 2: det@320 + in-memory identify/check-in, FACE_FAST_EMBED_DETECT=true)
- Host metrics: GPU0/GPU1 SM avg ~11% (max 31–35%) · api CPU avg ~150% per process (p95 ~250%) while busy

## สรุปเพดาน (SLO: detect p95 ≤ 550 ms, drop ≤ 5%)

| โปรไฟล์ | ใช้ได้สูงสุด (OK) | เริ่มแย่ |
|---------|-------------------|----------|
| idle × 3 คน/จอ | **32** จอ | — จอ |
| rush × 3 คน/จอ | **16** จอ | — จอ |
| rush × 1 คน/จอ | **24** จอ | — จอ |

### คำแนะนำใช้งาน

- ชั่วโมงเร่งด่วน (identify + check-in, ~3 คนในเฟรม): **ไม่เกิน 16 จอพร้อมกัน**
- กล้องว่าง / detect อย่างเดียว: ได้ถึงประมาณ **32 จอ**
- rush คนเดียวต่อจอ: ได้ถึงประมาณ **24 จอ**

## Idle × 3 คน/จอ (อัตราเต็ม detect ~90 ms)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 4 | 3 | 38 ms | 43 ms | 0.0% | — | — | OK |
| 8 | 3 | 44 ms | 58 ms | 0.0% | — | — | OK |
| 12 | 3 | 45 ms | 57 ms | 0.0% | — | — | OK |
| 16 | 3 | 49 ms | 62 ms | 0.0% | — | — | OK |
| 24 | 3 | 61 ms | 117 ms | 0.0% | — | — | OK |
| 32 | 3 | 66 ms | 113 ms | 0.0% | — | — | OK |

## Rush × 3 คน/จอ (อัตราเต็ม UI caps)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 4 | 3 | 55 ms | 90 ms | 0.4% | 187 ms | 135 ms | OK |
| 6 | 3 | 65 ms | 120 ms | 0.0% | 214 ms | 155 ms | OK |
| 8 | 3 | 78 ms | 141 ms | 0.0% | 228 ms | 176 ms | OK |
| 12 | 3 | 130 ms | 263 ms | 0.1% | 387 ms | 375 ms | OK |
| 16 | 3 | 182 ms | 299 ms | 0.0% | 484 ms | 459 ms | OK |

## Rush × 1 คน/จอ

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 4 | 1 | 49 ms | 61 ms | 0.0% | 113 ms | 86 ms | OK |
| 8 | 1 | 62 ms | 89 ms | 0.0% | 156 ms | 138 ms | OK |
| 12 | 1 | 88 ms | 144 ms | 0.0% | 206 ms | 188 ms | OK |
| 16 | 1 | 153 ms | 251 ms | 0.0% | 329 ms | 295 ms | OK |
| 24 | 1 | 237 ms | 381 ms | 0.2% | 459 ms | 451 ms | OK |

## ไฟล์ดิบ

- `scripts/kiosk-load/.cache/results-perf2-idle.jsonl`
- `scripts/kiosk-load/.cache/results-perf2-rush3.jsonl`
- `scripts/kiosk-load/.cache/results-perf2-rush1.jsonl`
