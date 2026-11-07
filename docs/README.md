# Project docs

- [SETUP](SETUP.md) — run the stack (local / Docker Desktop) + optional Face Core BFF
- [DEPLOY-SERVER](DEPLOY-SERVER.md) — คู่มือติดตั้งบนเซิร์ฟเวอร์ + seed mock data
- [SECRETS-REMEDIATION](SECRETS-REMEDIATION.md) — inventory ของ secret/PII ที่เคยอยู่ใน git, ขั้นตอน `git filter-repo`, key rotation checklist, re-clone notice
- **[KIOSK-CAPACITY-GUIDE](KIOSK-CAPACITY-GUIDE.md) — คู่มือความจุ: สรุปผลเทสทุกวิธี + สเป็คที่ควรใช้ (อ่านก่อน)**
- [KIOSK-LOADTEST](KIOSK-LOADTEST.md) — โหลดเทส WebSocket kiosk (local ก่อน แล้วชี้เซิร์ฟเวอร์)
- [KIOSK-LOADTEST-SATURATION](KIOSK-LOADTEST-SATURATION.md) — รอบ saturation: dual-API + เฟรมสมจริง + เกณฑ์ face-core; §4b ผลรอบ 2
- [KIOSK-LOADTEST-PERF2-TABLE](KIOSK-LOADTEST-PERF2-TABLE.md) — ตารางเพดานรอบ 2 (workers=3, det@320 in-memory): rush×3 16 จอ · rush×1 24 จอ · idle ≥32 จอ
- [KIOSK-LOADTEST-PERF3-TABLE](KIOSK-LOADTEST-PERF3-TABLE.md) — ตารางเพดานรอบ 3 (quad API `docker-compose.gpu-x2.yml`, whisper → GPU1): rush×3 24 จอ · rush×1 32 จอ · idle ≥48 จอ
- [KIOSK-LOADTEST-WORKERS2-CAPACITY](KIOSK-LOADTEST-WORKERS2-CAPACITY.md) — เพดาน dual GPU (workers=2) อัตราเต็ม (conservative)
- [EXEC-SUMMARY-KIOSK-CAPACITY](EXEC-SUMMARY-KIOSK-CAPACITY.md) — สรุปความจุคีออสสำหรับผู้บริหาร ([PDF](EXEC-SUMMARY-KIOSK-CAPACITY.pdf)) — **ตัวเลขปัจจุบันดู [KIOSK-CAPACITY-GUIDE](KIOSK-CAPACITY-GUIDE.md)**
- [KIOSK-CAPACITY-REPORT](KIOSK-CAPACITY-REPORT.md) — รายงานฉบับเต็ม: ไทม์ไลน์ทดสอบ 22–24 ก.ย., ค่าเฉลี่ย/p95, สาเหตุคอขวด, ข้อแนะนำ, ประมาณสเป็ค (รวมกรณี 10,000 คน) ([PDF](KIOSK-CAPACITY-REPORT.pdf))
- [KIOSK-LOADTEST-PERF4-TABLE](KIOSK-LOADTEST-PERF4-TABLE.md) — รอบ 4 hexa (3 process/GPU): เพดาน SLO vs saturation ไม่สน UX
- [KIOSK-LOADTEST-PERF5-TABLE](KIOSK-LOADTEST-PERF5-TABLE.md) — รอบ 5 dedupe cache บน quad: check-in ต่ำดีขึ้น แต่ rush×3 ยังไม่ถึง 32 จอ
- [FACE-CORE-IDENTIFY-CAPACITY](FACE-CORE-IDENTIFY-CAPACITY.md) — identify-only: baseline quad + **เพดานสุดท้ายหลังจูน (hexa w2: ×1 64/80 · ×3 48/64)** + HTTP ~20 conc / ~35 RPS · Face Core §6.6–§6.8 · [SATURATION §4g](KIOSK-LOADTEST-SATURATION.md)
- [ARCHITECTURE](ARCHITECTURE.md) — components, face flow, Face Core BFF topology
- [API](API.md) — DPU routes plus the Face Core calls the BFF makes
- [CURSOR-AGENT](CURSOR-AGENT.md) — Cursor rules & skills for agents
- [BACKLOG](BACKLOG.md) — unfinished Sprint#1 and hardening
- [PLAN-CLEANUP-REDESIGN](PLAN-CLEANUP-REDESIGN.md) — clean templates, redesign status, remaining work

Sibling vision hub: [`../face-core`](../face-core) — enable with `docker-compose.face-core.yml`.

## Agent entrypoints

| Kind | Path |
|------|------|
| Always-on rule | `.cursor/rules/dpu-project.mdc` |
| Web-Manage UI rule | `.cursor/rules/dpu-web-manage.mdc` |
| Face API rule | `.cursor/rules/dpu-face-api.mdc` |
| Docker rule | `.cursor/rules/dpu-docker.mdc` |
| Skills | `.cursor/skills/dpu-face-kiosk/`, `dpu-web-manage-ui/`, `dpu-docker-rebuild/` |
