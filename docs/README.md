# Project docs

- [SETUP](SETUP.md) — run the stack (local / Docker Desktop) + optional Face Core BFF
- [DEPLOY-SERVER](DEPLOY-SERVER.md) — คู่มือติดตั้งบนเซิร์ฟเวอร์ + seed mock data
- [KIOSK-LOADTEST](KIOSK-LOADTEST.md) — โหลดเทส WebSocket kiosk (local ก่อน แล้วชี้เซิร์ฟเวอร์)
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
