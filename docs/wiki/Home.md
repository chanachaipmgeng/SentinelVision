# SentinelVision Wiki

ยินดีต้อนรับสู่คลังความรู้และเอกสารระบบ **SentinelVision v4.0.0** (Unified Biometric Identity, Attendance, Access Control, Watchlist & Smart Events Platform)

## สารบัญวิกิ (Wiki Pages)

1. **[Architecture & AI Systems](Architecture-and-AI.md)**
   - โครงสร้างระบบ Backend (`API-Fast/`), Frontend (`Web-Manage/`), Nginx Gateway (`docker/nginx/`)
   - Dual `pgvector` HNSW Pipeline (`face_encoding` + `sentinel_identity`)
   - Browser Edge AI (`Web-Manage/public/`: MediaPipe Hand Gesture, ONNX Runtime Web, Silero VAD)
   - AI Copilot (`app-ask-dock` SSE) และ Security Investigation Graph (`/sentinel/company/{companyId}/graph`)
2. **[UI Shell, Dual-Rail Sidebar & Modular Scan Stations](UI-Shell-and-Scan-Stations.md)**
   - VaultX Obsidian Glass Design System และ Dark/Light Theme Tokens
   - Two-Column Dual-Rail Sidebar (`17.5rem` Desktop + Off-Canvas Drawer `< 992px`)
   - 6 Modular Kiosk Scan Stations (`/company/scan/:stationMode`) และ Scan Hub (`/company/scan-hub`)
3. **[Operations, Migrations & Deployment](Operations-and-Deployment.md)**
   - การรัน Docker Compose (Single / Dual / Quad GPU), Nginx CSP (`'wasm-unsafe-eval'`, `microphone=(self)`)
   - Alembic Migrations (`0001`–`0035_sprint6_tailgating_health_edge`)
   - Fast Static Asset Deployment สำหรับ `Web-Manage` และการตรวจสอบ Lint / Type-check / Test

## เอกสารอ้างอิงหลักใน Repo

- [README.md](../../README.md) — ภาพรวมระบบและ Quick Start
- [GEMINI.md](../../GEMINI.md) — กฎสถาปัตยกรรมและมาตรฐานวิศวกรรม Enterprise
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) — สถาปัตยกรรมระบบฉบับเต็ม
- [docs/API.md](../API.md) — สรุป REST & WebSocket Endpoints
- [docs/USER-MANUAL-SENTINELVISION.md](../USER-MANUAL-SENTINELVISION.md) — คู่มือผู้ใช้งาน
- [docs/RUNBOOK.md](../RUNBOOK.md) — คู่มือปฏิบัติการและการกู้คืนระบบ
