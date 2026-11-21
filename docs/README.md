# Project docs

- **[SentinelVision Wiki](wiki/Home.md)** — วิกิสรุประบบ, สถาปัตยกรรม Edge AI / Copilot, UI Shell & Scan Stations, และ Operations
- [GEMINI.md](../GEMINI.md) — กฎสถาปัตยกรรม, ความปลอดภัย, Performance, UI/UX และมาตรฐานวิศวกรรม SentinelVision v4.0
- [SENTINELVISION-ROADMAP](SENTINELVISION-ROADMAP.md) — แผนแม่บทและสถาปัตยกรรม SentinelVision (Phase 1–10 Enterprise)
- [USER-MANUAL-SENTINELVISION](USER-MANUAL-SENTINELVISION.md) — คู่มือการใช้งานระบบ SentinelVision ([PDF](SentinelVision_User_Manual.pdf))
- [RUNBOOK](RUNBOOK.md) — คู่มือดูแลระบบ (RPO/RTO, GPU, Face Core, Alembic)
- [SETUP](SETUP.md) — run the stack (local / Docker Desktop) + optional Face Core BFF
- [DEPLOY-SERVER](DEPLOY-SERVER.md) — คู่มือติดตั้งบนเซิร์ฟเวอร์ + seed mock data
- [SECRETS-REMEDIATION](SECRETS-REMEDIATION.md) — inventory ของ secret/PII ที่เคยอยู่ใน git, ขั้นตอน `git filter-repo`, key rotation checklist, re-clone notice
- **[KIOSK-CAPACITY-GUIDE](KIOSK-CAPACITY-GUIDE.md) — คู่มือความจุ: สรุปผลเทสทุกวิธี + สเป็คที่ควรใช้ (อ่านก่อน)**
- [KIOSK-LOADTEST](KIOSK-LOADTEST.md) — โหลดเทส WebSocket kiosk (local ก่อน แล้วชี้เซิร์ฟเวอร์)
- [KIOSK-LOADTEST-SATURATION](KIOSK-LOADTEST-SATURATION.md) — รอบ saturation: dual-API + เฟรมสมจริง + เกณฑ์ face-core; §4b ผลรอบ 2
- [EXEC-SUMMARY-KIOSK-CAPACITY](EXEC-SUMMARY-KIOSK-CAPACITY.md) — สรุปความจุคีออสสำหรับผู้บริหาร ([PDF](EXEC-SUMMARY-KIOSK-CAPACITY.pdf)) — **ตัวเลขปัจจุบันดู [KIOSK-CAPACITY-GUIDE](KIOSK-CAPACITY-GUIDE.md)**
- [KIOSK-CAPACITY-REPORT](KIOSK-CAPACITY-REPORT.md) — รายงานฉบับเต็ม: ไทม์ไลน์ทดสอบ 22–24 ก.ย., ค่าเฉลี่ย/p95, สาเหตุคอขวด, ข้อแนะนำ, ประมาณสเป็ค (รวมกรณี 10,000 คน) ([PDF](KIOSK-CAPACITY-REPORT.pdf))
- [FACE-CORE-IDENTIFY-CAPACITY](FACE-CORE-IDENTIFY-CAPACITY.md) — identify-only: baseline quad + **เพดานสุดท้ายหลังจูน (hexa w2: ×1 64/80 · ×3 48/64)** + HTTP ~20 conc / ~35 RPS · Face Core §6.6–§6.8 · [SATURATION §4g](KIOSK-LOADTEST-SATURATION.md)
- [ARCHITECTURE](ARCHITECTURE.md) — components, face flow, Face Core BFF topology, Enterprise architecture & testing
- [API](API.md) — DPU routes plus the Face Core calls the BFF makes
- [API_CONTRACT](API_CONTRACT.md) — Enterprise API contract (envelopes, error taxonomy, pagination, kiosk isolation)
- [UAT-SIGNOFF-v6.4.0](UAT-SIGNOFF-v6.4.0.md) — รายงานตรวจรับและผลทดสอบ Playwright E2E ครบทุกโมดูล (23/23 passed) สำหรับส่งมอบ `v6.4.0`

Sibling vision hub: [`../face-core`](../face-core) — enable with `docker-compose.face-core.yml`.

## Agent Rules & Engineering Standards

- **Project Rules (Root)**: [`../GEMINI.md`](../GEMINI.md) — กฎหลักสำหรับ AI Agent และวิศวกร (Multi-tenancy, Active Identity Filtering, Kiosk Token Isolation, PDPA PII Masking, Asyncio/GPU Non-blocking, Alembic, Nginx Gateway, และ Verification Commands)
- **Frontend Scoped Rules**: [`../Web-Manage/GEMINI.md`](../Web-Manage/GEMINI.md) — กฎเฉพาะฝั่ง Angular/CSS (`::picker-icon`, Hero LCP Contrast, Telemetry Truthfulness, Thai Typography, Role-gated Self-Service, FAB Clearance)
