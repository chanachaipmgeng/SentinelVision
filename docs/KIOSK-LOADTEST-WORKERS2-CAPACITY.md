# Loadtest capacity (full rate) — FACE_GPU_WORKERS=2

> สรุปภาษาผู้บริหาร (ไม่เน้นเทคนิค): [EXEC-SUMMARY-KIOSK-CAPACITY.md](EXEC-SUMMARY-KIOSK-CAPACITY.md)

วัด **2026-09-23** บน `10.50.0.117` · จำลองคีออสอัตราเต็ม (detect ทุก ~90 ms ตาม UI, identify ≤2 / check-in ≤3 ค้างต่อจอ) · hold 30–35 s ต่อขั้น

## สภาพแวดล้อม

- URL: `http://10.50.0.117:8880` (`https://face-in.myhr.co.th` ยัง 502 — TLS ชี้พอร์ตผิด)
- GPUs: 2× Quadro RTX 5000 16 GB
- `FACE_DEVICES=cuda:0,cuda:1` · `FACE_GPU_WORKERS=2` · คิว local InsightFace
- SLO: session p95 ≤ 500 ms · detect p95 ≤ 550 ms · dropped ≤ 5%
- verdict: **OK** = ผ่าน SLO · **MARGIN** = เกิน SLO ไม่เกิน ~1.5× หรือ drop ≤15% · **FAIL** = พังชัด

## สรุปเพดาน (ประสิทธิภาพสูงสุดที่รับได้ภายใต้ SLO)

| โปรไฟล์ | ใช้ได้สูงสุด (OK) | เริ่มแย่ | เพดานฮาร์ด |
|---------|-------------------|----------|------------|
| idle × 3 คน/จอ | **12** จอ | 14 จอ (p95 565) | ~24 จอ (p95 ~1 s) |
| rush × 3 คน/จอ | **5** จอ | 6 จอ (p95 626 / drop 9%) | ~7+ จอ (drop ≥50%) |
| rush × 1 คน/จอ | **8** จอ | 9 จอ (drop 5.7%) | ~16+ จอ |

### คำแนะนำใช้งาน (deploy)

| สถานการณ์ | จำนวนจอแนะนำ | หมายเหตุ |
|-----------|--------------|----------|
| เร่งด่วน มีคนหนาแน่น (~3 คน/เฟรม) | **≤ 4 จอ** (เพดานเทส 5) | เหลือ headroom กัน spike |
| เร่งด่วน คนละคนต่อจอ | **≤ 8 จอ** | ที่ 9 จอ drop เริ่มเกิน 5% |
| กล้องว่าง / รอคน | **≤ 12 จอ** | idle detect อย่างเดียว |
| คิว GPU | `active` สูงสุด 2 = อิ่มทั้ง 2 worker | peak ~59 งาน/วินาที |

## Idle × 3 คน/จอ (อัตราเต็ม detect ~90 ms)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 6 | 3 | 161 ms | 320 ms | 0.0% | — | — | OK |
| 8 | 3 | 189 ms | 384 ms | 0.0% | — | — | OK |
| 10 | 3 | 227 ms | 444 ms | 0.0% | — | — | OK |
| 12 | 3 | 258 ms | 500 ms | 0.0% | — | — | OK |
| 14 | 3 | 297 ms | 565 ms | 0.0% | — | — | MARGIN |
| 16 | 3 | 314 ms | 616 ms | 0.0% | — | — | MARGIN |
| 20 | 3 | 407 ms | 759 ms | 0.0% | — | — | MARGIN |
| 24 | 3 | 545 ms | 1060 ms | 0.0% | — | — | FAIL |

## Rush × 3 คน/จอ (อัตราเต็ม UI caps)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 1 | 3 | 140 ms | 177 ms | 0.0% | 293 ms | 138 ms | OK |
| 2 | 3 | 147 ms | 297 ms | 0.7% | 393 ms | 166 ms | OK |
| 3 | 3 | 179 ms | 342 ms | 1.7% | 463 ms | 208 ms | OK |
| 4 | 3 | 208 ms | 446 ms | 1.5% | 459 ms | 240 ms | OK |
| 5 | 3 | 245 ms | 478 ms | 4.1% | 667 ms | 294 ms | OK |
| 6 | 3 | 278 ms | 626 ms | 9.4% | 704 ms | 371 ms | MARGIN |
| 7 | 3 | 407 ms | 1066 ms | 50.4% | 932 ms | 536 ms | FAIL |
| 8 | 3 | 561 ms | 1287 ms | 55.6% | 1166 ms | 676 ms | FAIL |
| 10 | 3 | 890 ms | 1712 ms | 53.1% | 1514 ms | 874 ms | FAIL |

## Rush × 1 คน/จอ

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 4 | 1 | 66 ms | 174 ms | 0.5% | 338 ms | 123 ms | OK |
| 6 | 1 | 74 ms | 204 ms | 1.5% | 391 ms | 150 ms | OK |
| 8 | 1 | 94 ms | 224 ms | 2.3% | 363 ms | 164 ms | OK |
| 9 | 1 | 128 ms | 266 ms | 5.7% | 534 ms | 215 ms | MARGIN |
| 10 | 1 | 187 ms | 379 ms | 12.1% | 631 ms | 268 ms | MARGIN |
| 12 | 1 | 164 ms | 415 ms | 22.4% | 572 ms | 236 ms | FAIL |
| 16 | 1 | 253 ms | 649 ms | 40.6% | 920 ms | 373 ms | FAIL |
| 20 | 1 | 436 ms | 1508 ms | 58.1% | 1426 ms | 839 ms | FAIL |

## คิว GPU ระหว่างเทส

- devices: `cuda:0,cuda:1` · workers: **2**
- max active: **2** (อิ่มทั้งคู่)
- max pending: **30**
- peak throughput: **~59 งาน/วินาที**
- samples: 1125

## วิธีสร้างรายงานซ้ำ

```powershell
cd scripts/kiosk-load
python summarize_capacity.py `
  --idle .cache/results-workers2-fullrate-idle.jsonl `
  --rush3 .cache/results-workers2-fullrate-rush3.jsonl `
  --rush1 .cache/results-workers2-fullrate-rush1.jsonl `
  --queue .cache/queue-workers2-fullrate.csv `
  --out ../../docs/KIOSK-LOADTEST-WORKERS2-CAPACITY.md
```

## ไฟล์ดิบ

- `scripts/kiosk-load/.cache/results-workers2-fullrate-idle.jsonl`
- `scripts/kiosk-load/.cache/results-workers2-fullrate-rush3.jsonl`
- `scripts/kiosk-load/.cache/results-workers2-fullrate-rush1.jsonl`
- `scripts/kiosk-load/.cache/queue-workers2-fullrate.csv`
- สคริปต์สรุป: `scripts/kiosk-load/summarize_capacity.py`
