# Perf round 5 — check-in dedupe cache + hexa w2 A/B + gated client

## สภาพแวดล้อม

- Host: `10.50.0.117` · URL: `http://10.50.0.117:8880`
- โค้ด: in-process check-in dedupe cache ([`checkin_dedupe_cache.py`](../API-Fast/src/utils/checkin_dedupe_cache.py))
- Loadgen: เพิ่ม `--detect-interval-ms` · หน้าบ้านปรับ `KIOSK_STATIC_WITH_FACES_MS` 600→**800**, `KIOSK_TRACKING_LOCKED_MS` 180→**220**
- วัด: 24 ก.ย. 2026 ~01:57–02:44 (UTC+7)
- Production ท้ายรอบ: **quad + `FACE_GPU_WORKERS=3`** (ถอยจาก hexa แล้ว)

## สรุปผู้บริหาร

| คำถาม | คำตอบ |
|-------|--------|
| Dedupe cache ช่วยไหม? | ช่วยที่โหลดต่ำ (check-in p95 ~63–84 ms) แต่ **ไม่ดันเพดาน rush×3 full-rate** |
| hexa + workers=2 ดีกว่า quad ไหม? | **ไม่** — rush×3 ที่ 24 ยัง FAIL (663 ms) และแย่กว่า PERF3 |
| คีออสจริง (motion gate ~600 ms) รับได้เท่าไร? | rush×3 **32 จอ OK** · rush×1 **48 จอ OK** |
| ติดตั้งแนะนำ (full-rate ตารางอนุรักษ์) | rush×3 **≤24** · rush×1 **≤32** (ตาม PERF3) |
| ติดตั้งถ้าเชื่อ motion gating | rush×3 **≤28–32** · rush×1 **≤40–48** |

## 5A — Quad + dedupe cache (full-rate 90 ms)

เทียบ [PERF3](KIOSK-LOADTEST-PERF3-TABLE.md):

| โปรไฟล์ | PERF3 | PERF5A |
|---------|-------|--------|
| smoke check-in p95 (duplicate) | ~135 ms | **63 ms** |
| rush×3 16 | 383 OK | 407 OK |
| rush×3 24 | **514 OK** | 790 FAIL (cold/หลัง recreate) |
| rush×3 32 | 740 FAIL | 856 FAIL |
| rush×1 32 | 429 OK | 501 OK |

→ ไม่ถึงเป้า 32 จอ full-rate

## 5B — Hexa + `FACE_GPU_WORKERS=2` (full-rate)

| โปรไฟล์ | detect p95 | verdict vs PERF3 |
|---------|------------|------------------|
| rush×3 16 | 474 ms (drop 6.2%) | MARGIN/แย่กว่า |
| rush×3 24 | 663 ms | FAIL (PERF3 OK 514) |
| rush×3 32 | 793 ms | FAIL |
| rush×1 24 | 498 ms | OK |
| rush×1 32 | 1742 ms | FAIL (PERF3 OK 429) |

**เก็บ production = quad w3** — hexa+w2 ไม่ชนะ

## 5C — Quad w3 + detect-interval 600 ms (จำลอง static-scene gating)

| โปรไฟล์ | จอ | detect p95 | drop | identify p95 | checkin p95 | verdict |
|---------|----|------------|------|--------------|-------------|---------|
| rush×3 | 24 | 766 ms | 0.9% | 761 ms | 726 ms | FAIL* (ขั้นแรกยังอุ่นเครื่อง) |
| rush×3 | **32** | **425 ms** | 0.0% | 627 ms | 638 ms | **OK** |
| rush×3 | 40 | 725 ms | 0.0% | 1100 ms | 1055 ms | FAIL |
| rush×1 | **32** | **189 ms** | 0.0% | 254 ms | 256 ms | **OK** |
| rush×1 | **48** | **399 ms** | 0.0% | 482 ms | 537 ms | **OK** |

\* ขั้น 24 จอเป็นขั้นแรกหลัง recreate — ใช้ขั้น 32 ที่อุ่นแล้วเป็นตัวเลขหลัก

## ข้อแนะนำสุดท้ายรอบ 5

1. คง **quad + workers=3 + dedupe cache** บนเซิร์ฟเวอร์
2. ตารางอนุรักษ์ (loadgen 90 ms): เร่งด่วน ≤24 จอ / คนละจอ ≤32
3. ตารางคีออสจริง (gating ~600–800 ms): เร่งด่วนได้ถึง **~32 จอ** / คนละจอ **~48 จอ**
4. อย่าใช้ hexa เป็น production จนกว่าจะมีหลักฐานใหม่ที่ชนะ quad ที่ rush×3 24

## ไฟล์ดิบ

- `scripts/kiosk-load/.cache/results-perf5-*.jsonl`
- `scripts/kiosk-load/.cache/results-perf5b-*.jsonl`
- `scripts/kiosk-load/.cache/results-perf5c-*-gated.jsonl`
