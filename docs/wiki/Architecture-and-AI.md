# Architecture & AI Systems

[← กลับหน้าหลัก Wiki](Home.md)

## 1. ภาพรวมสแต็ก (Core Stack)

| เลเยอร์ | เทคโนโลยี | หน้าที่หลัก |
|---|---|---|
| **Gateway** | Nginx (`docker/nginx/`) | Reverse proxy บนพอร์ต 80, จัดการ CSP headers และโหลดบาลานซ์ Multi-GPU |
| **Backend** | FastAPI v4.0.0 (Python 3.11, async SQLAlchemy + `asyncpg`) | Business logic, Auth/RBAC/2FA/SSO, Face Pipeline, Outbox Webhooks, AI Copilot |
| **Biometric Engine** | InsightFace `buffalo_l` (512-d) / Face Core BFF | สกัดและเปรียบเทียบเวกเตอร์ใบหน้าผ่าน `run_on_face_gpu(...)` ไม่บล็อก Event Loop |
| **Database** | PostgreSQL 16 + `pgvector` HNSW | เก็บข้อมูลเชิงสัมพันธ์และ Vector Cosine Indexes (`face_encoding`, `sentinel_identity`) |
| **Frontend** | Angular 17 (`Web-Manage/`) | Admin Console, Security Command Center, HR/PDPA, Kiosk Stations, AI Copilot |

## 2. Browser Edge AI (`Web-Manage/public/`)

เนื่องจาก `Web-Manage/angular.json` ไม่รวม `**/models/**` ภายใต้ `src/assets` แอสเซตสำหรับรันโมเดล AI บนเบราว์เซอร์แบบ Same-Origin จึงถูกจัดเก็บใน `Web-Manage/public/` (เสิร์ฟที่ `/`):

- **`/mediapipe/*`** — `@mediapipe/tasks-vision` WASM สำหรับตรวจจับท่าทางมือบน Kiosk (`KioskGestureService` แบบ opt-in และ throttle ~4 Hz)
- **`/ort/*`** — `onnxruntime-web` WASM backend
- **`/models/*`** — `hand_landmarker.task` และโมเดล Silero VAD (`@ricky0123/vad-web`) สำหรับสั่งงานด้วยเสียงใน AI Copilot

สคริปต์ซิงค์แอสเซตใน `Web-Manage/package.json`:
```bash
npm run sync-mediapipe
npm run sync-ort
npm run fetch-hand-model
npm run fetch-silero-vad
```

> **CSP Requirement:** `docker/nginx/entrypoint/30-dpu-runtime.sh` ต้องกำหนด `'wasm-unsafe-eval'` ใน `script-src` และ `microphone=(self)` ใน `Permissions-Policy` เพื่อให้ Edge AI WASM และ Voice Input ทำงานได้โดยไม่ติดบล็อก

## 3. Security Investigation Graph & AI Copilot

- **Security Investigation Graph (`GET /sentinel/company/{companyId}/graph`):**
  - สร้างกราฟความสัมพันธ์ระดับบริษัทเชื่อมโยงกล้อง (`cameras`), โซนเข้า-ออก (`zones`), บุคคล (`identities`), และเหตุการณ์ (`incidents`) โดยบังคับ `assert_request_company_access`
- **AI Copilot (`app-ask-dock` → `POST /sentinel/company/{companyId}/assistant/chat`):**
  - สตรีมคำตอบแบบ Server-Sent Events (`event: status`, `event: token`)
  - รองรับการเปิด/ปิดเสียง (`Speak Orb` + Silero VAD)
  - เมื่อตั้งครบทั้ง `AI_CORE_URL` + `AI_CORE_API_KEY` จะเรียก **ai-core-service** (`/v1/llm/stream`) โดยยังฝัง `LIVE_COMPANY_SNAPSHOT` ในพรอมป์ของ Sentinel
  - ไม่ตั้ง ai-core → ใช้ Gemini ตรงผ่าน `GOOGLE_API_KEY`; ไม่มีคีย์ → Fallback สรุปข้อมูลสดจาก PostgreSQL ของบริษัทนั้น
  - Face / vision / YOLO / InsightFace ยังรันใน Sentinel (ยังไม่ cut over ไป ai-core)
