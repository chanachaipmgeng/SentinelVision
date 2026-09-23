# Perf round 3 — quad API (2 process/GPU) workers=3, whisper moved to GPU1

## สภาพแวดล้อม

- Host: `10.50.0.117` · URL: `http://10.50.0.117:8880`
- GPUs: 2× Quadro RTX 5000 16 GB
- Dual API: `dpu-api` (GPU0) + `dpu-api-gpu1` (GPU1) · `FACE_GPU_WORKERS=3` each
- Client: realistic frames (1280 px, JPEG q70) · detect interval 90 ms
- SLO: session p95 ≤ 500 ms · detect p95 ≤ 550 ms · dropped ≤ 5%
- Layout: docker-compose.gpu-x2.yml → dpu-api + dpu-api-gpu0b (GPU0), dpu-api-gpu1 + dpu-api-gpu1b (GPU1); nginx default.quad-gpu.conf (4 upstreams)
- Code: 9d407e2d · whisper_server pinned CUDA_VISIBLE_DEVICES=1
- Host metrics: GPU SM avg ~16%/ใบ (max 39%) · API CPU ~120% ต่อ process ×4 (รวม ~480%) while busy · host 32 cores
- A/B workers=2 บนควอด: rush×3 16 จอ 365 ms · 24 จอ 509 ms · rush×1 32 จอ 497 ms — ไม่ต่างจาก workers=3 (noise)

## สรุปเพดาน (SLO: detect p95 ≤ 550 ms, drop ≤ 5%)

| โปรไฟล์ | ใช้ได้สูงสุด (OK) | เริ่มแย่ |
|---------|-------------------|----------|
| idle × 3 คน/จอ | **48** จอ | — จอ |
| rush × 3 คน/จอ | **24** จอ | 32 จอ |
| rush × 1 คน/จอ | **32** จอ | 48 จอ |

### คำแนะนำใช้งาน

- ชั่วโมงเร่งด่วน (identify + check-in, ~3 คนในเฟรม): **ไม่เกิน 24 จอพร้อมกัน**
- กล้องว่าง / detect อย่างเดียว: ได้ถึงประมาณ **48 จอ**
- rush คนเดียวต่อจอ: ได้ถึงประมาณ **32 จอ**

## Idle × 3 คน/จอ (อัตราเต็ม detect ~90 ms)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 16 | 3 | 56 ms | 72 ms | 0.4% | — | — | OK |
| 32 | 3 | 68 ms | 124 ms | 0.1% | — | — | OK |
| 48 | 3 | 97 ms | 173 ms | 0.0% | — | — | OK |

## Rush × 3 คน/จอ (อัตราเต็ม UI caps)

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 8 | 3 | 67 ms | 120 ms | 0.3% | 223 ms | 158 ms | OK |
| 16 | 3 | 225 ms | 383 ms | 0.0% | 452 ms | 384 ms | OK |
| 24 | 3 | 311 ms | 514 ms | 0.0% | 614 ms | 548 ms | OK |
| 32 | 3 | 483 ms | 740 ms | 0.0% | 806 ms | 779 ms | MARGIN |

## Rush × 1 คน/จอ

| จอ | faces | detect p50 | detect p95 | drop | identify p95 | checkin p95 | verdict |
|----|-------|------------|------------|------|--------------|-------------|---------|
| 16 | 1 | 107 ms | 179 ms | 0.0% | 244 ms | 212 ms | OK |
| 24 | 1 | 176 ms | 307 ms | 0.0% | 336 ms | 333 ms | OK |
| 32 | 1 | 251 ms | 429 ms | 0.0% | 465 ms | 471 ms | OK |
| 48 | 1 | 523 ms | 817 ms | 0.0% | 730 ms | 844 ms | MARGIN |

## ไฟล์ดิบ

- `scripts/kiosk-load/.cache/results-perf3-idle.jsonl`
- `scripts/kiosk-load/.cache/results-perf3-rush3.jsonl`
- `scripts/kiosk-load/.cache/results-perf3-rush1.jsonl`
