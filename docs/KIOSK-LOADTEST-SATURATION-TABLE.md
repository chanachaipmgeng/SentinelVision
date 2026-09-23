# Saturation capacity — dual API (GPU0+GPU1) workers=2 each

## สภาพแวดล้อม

- Host: `10.50.0.117` · URL: `http://10.50.0.117:8880`
- GPUs: 2× Quadro RTX 5000 16 GB
- `FACE_DEVICES=cuda:0,cuda:1` · `FACE_GPU_WORKERS=2`
- Client: full-rate kiosk sim (detect interval 90 ms, UI identify/check-in caps)
- SLO: session p95 ≤ 500 ms · detect p95 ≤ 550 ms · dropped ≤ 5%

## สรุปเพดาน (SLO: detect p95 ≤ 550 ms, drop ≤ 5%)

| โปรไฟล์ | ใช้ได้สูงสุด (OK) | เริ่มแย่ |
|---------|-------------------|----------|
| idle × 3 คน/จอ | **24** จอ | — จอ |
| rush × 3 คน/จอ | **6** จอ | 8 จอ |
| rush × 1 คน/จอ | **12** จอ | 16 จอ |

### คำแนะนำใช้งาน

- ชั่วโมงเร่งด่วน (identify + check-in, ~3 คนในเฟรม): **ไม่เกิน 6 จอพร้อมกัน**
- กล้องว่าง / detect อย่างเดียว: ได้ถึงประมาณ **24 จอ**
- rush คนเดียวต่อจอ: ได้ถึงประมาณ **12 จอ**

## Idle × 3 คน/จอ (อัตราเต็ม detect ~90 ms)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 4 | 3 | 44 ms | 50 ms | 0.3% | — | — | OK |
| 8 | 3 | 49 ms | 61 ms | 0.0% | — | — | OK |
| 12 | 3 | 45 ms | 56 ms | 0.0% | — | — | OK |
| 16 | 3 | 50 ms | 63 ms | 0.0% | — | — | OK |
| 24 | 3 | 58 ms | 85 ms | 0.0% | — | — | OK |

## Rush × 3 คน/จอ (อัตราเต็ม UI caps)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 4 | 3 | 49 ms | 181 ms | 0.5% | 326 ms | 110 ms | OK |
| 6 | 3 | 61 ms | 206 ms | 1.3% | 359 ms | 135 ms | OK |
| 8 | 3 | 98 ms | 290 ms | 6.1% | 656 ms | 153 ms | MARGIN |
| 12 | 3 | 193 ms | 434 ms | 8.3% | 737 ms | 223 ms | MARGIN |
| 16 | 3 | 140 ms | 780 ms | 56.6% | 1125 ms | 450 ms | FAIL |

## Rush × 1 คน/จอ

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 4 | 1 | 51 ms | 92 ms | 0.0% | 218 ms | 72 ms | OK |
| 8 | 1 | 57 ms | 143 ms | 0.2% | 273 ms | 119 ms | OK |
| 12 | 1 | 77 ms | 235 ms | 1.5% | 433 ms | 152 ms | OK |
| 16 | 1 | 113 ms | 263 ms | 5.0% | 449 ms | 202 ms | MARGIN |

## ไฟล์ดิบ

- `scripts/kiosk-load/.cache/results-sat-after-idle.jsonl`
- `scripts/kiosk-load/.cache/results-sat-after-rush3.jsonl`
- `scripts/kiosk-load/.cache/results-sat-after-rush1.jsonl`
