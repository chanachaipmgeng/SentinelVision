# SentinelVision Enterprise API Contract & Integration Specifications (v4.0)

This document formalizes the enterprise-grade API contract, data envelopes, error taxonomy, multi-tenant security boundaries, and streaming protocols for **SentinelVision (DPU Attendance v4.0)**.

---

## 1. Global Conventions & Transport Standards

### 1.1 Base URL & Path Structure
- **Production Gateway:** Nginx Reverse Proxy running on port `80` (HTTP) or `443` (TLS/HTTPS).
- **Prefix Mounting:** All public routes are dual-mounted at the root level and under the standard enterprise prefix `/api/v1` (e.g., `POST /auth/login` and `POST /api/v1/auth/login`).
- **Encoding & Media:** JSON payloads must be UTF-8 encoded with `Content-Type: application/json`. File uploads must use `multipart/form-data`.

### 1.2 Mandatory Observability & Idempotency Headers
Every request and response in SentinelVision adheres to distributed tracing and idempotency invariants:

| Header | Direction | Description |
| :--- | :--- | :--- |
| `X-Request-Id` | Request / Response | Unique request UUID (e.g., `req_01j7...`). Injected by Nginx/FastAPI middleware if absent. |
| `traceparent` | Request / Response | W3C Distributed Tracing header (`00-<trace_id>-<span_id>-<trace_flags>`). |
| `Idempotency-Key` | Request (Mutating) | Client-provided UUID for critical mutations (e.g., `POST /timestamp/company/{id}`, employee imports). Replays within 24h return the cached first response. |
| `X-Sentinel-DR-Sig` | Request (Internal) | HMAC-SHA256 signature for cross-region replication (`/sentinel/dr/replicate`). |

---

## 2. Standardized Response Envelope & Pagination

### 2.1 Single Resource Response
Single resource endpoints return the serialized resource directly with standard HTTP status codes:
- `200 OK`: Request succeeded.
- `201 Created`: Resource successfully created.
- `204 No Content`: Successful deletion or mutation with no response body.

```json
{
  "id": "e3b0c442-98fc-1c14-9afb-4c767f13a45e",
  "name": "Headquarters Access Zone",
  "companyId": "00000000-0000-0000-0000-000000000001",
  "status": "ACTIVE",
  "createdAt": "2026-11-21T06:00:00Z"
}
```

### 2.2 Standard Pagination Query & Metadata
List endpoints on high-growth tables enforce bounded pagination using either offset-based parameters or cursor-based tokens:

**Query Parameters:**
- `page`: 1-based page index (default: `1`).
- `pageSize` (or `limit`): Items per page (default: `20`, maximum: `200`).
- `offset`: Zero-based item offset (legacy compatibility: `(page - 1) * pageSize`).

**Paginated Response Contract:**
```json
{
  "items": [
    { "id": "uuid-1", "name": "Item 1" },
    { "id": "uuid-2", "name": "Item 2" }
  ],
  "total": 142,
  "page": 1,
  "pageSize": 20,
  "totalPages": 8,
  "hasNext": true,
  "hasPrev": false
}
```

---

## 3. Standardized Error Taxonomy

When an operation fails (HTTP 4xx or 5xx), the response strictly returns the standard `ErrorResponse` schema. Raw Python stack traces are never exposed to clients (`AUTH_FAIL_FAST=true`).

### 3.1 Error Schema
```json
{
  "error": {
    "code": "AUTH_INVALID_CREDENTIALS",
    "message": "Invalid username or password.",
    "status": 401,
    "requestId": "d0b69c3d-740b-4d30-99fe-dc5dc51a0980",
    "details": []
  },
  "detail": "Invalid username or password."
}
```
*Note: `detail` is retained alongside `error.message` for backward compatibility with earlier API consumers.*

### 3.2 Canonical Error Codes

| HTTP Status | Error Code | Description |
| :--- | :--- | :--- |
| `400 Bad Request` | `VALIDATION_FAILED` | Pydantic schema validation failure or malformed payload. |
| `401 Unauthorized` | `AUTH_TOKEN_MISSING` | Missing or invalid `Authorization: Bearer <jwt>`. |
| `401 Unauthorized` | `AUTH_TOKEN_EXPIRED` | JWT has expired; client must rotate via `/auth/refresh`. |
| `401 Unauthorized` | `AUTH_TOKEN_REVOKED` | Token `jti` or session family has been invalidated. |
| `401 Unauthorized` | `MFA_REQUIRED` | TOTP 2FA code is required (`totpCode`). |
| `403 Forbidden` | `TENANCY_VIOLATION` | Cross-company access attempted (`assert_company_access`). |
| `403 Forbidden` | `PERMISSION_DENIED` | Caller lacks the requisite RBAC permission code. |
| `403 Forbidden` | `KIOSK_SCOPE_VIOLATION` | Terminal token (`typ="kiosk"`) attempted admin route mutation. |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | Target entity does not exist or has been soft-deleted. |
| `409 Conflict` | `RESOURCE_CONFLICT` | Unique constraint violation or duplicate key. |
| `422 Unprocessable`| `QUALITY_CHECK_FAILED` | Biometric image failed pre-flight sharpness/brightness gate. |
| `429 Too Many Req`| `RATE_LIMITED` | In-process/Redis token bucket threshold exceeded. |
| `500 Server Error` | `INTERNAL_ERROR` | Unhandled server exception (logged with Request ID). |

---

## 4. Multi-Tenancy & Authentication Scoping

### 4.1 Strict Tenancy Invariant
1. All requests targeting company resources (`/company/{companyId}/*`, `/employees/*`, `/sentinel/*`) verify caller membership via `assert_company_access(db, member, companyId)`.
2. Super Admin (`ROLE_SYSTEM_ADMIN`) bypasses company tenancy checks for system-wide auditing and license management only.
3. Every soft-deletable entity query filters `Model.deletedAt.is_(None)`.

### 4.2 Terminal Token Isolation (`typ="kiosk"`)
Device tokens issued through one-time pairing codes (`POST /auth/kiosk/pair`) are restricted via `_is_kiosk_path_allowed` to:
- WebSocket Biometric Kiosk: `/face/ws/kiosk`
- Member Verification: `/face/members/{detect,identify,check-in,check-in-walkby,check-face-emp}`
- Attendance Status: `/face/kiosk-attendance/{companyId}`
- TTS Configuration: `/system/tts-settings`

Kiosk tokens are rejected (`403 Forbidden`) if attempting to create, update, or delete users, zones, shifts, or company settings.

---

## 5. Media & Biometric Image Quality Pre-flight

### 5.1 Enrollment File Constraints
- **Supported Formats:** JPEG (`image/jpeg`), PNG (`image/png`).
- **File Size Limit:** Maximum 10 MB per image.
- **Image Dimensions:** Minimum $100 \times 100\text{ px}$, Maximum $5000 \times 5000\text{ px}$.

### 5.2 Pre-flight Quality Criteria (`/face/check-quality`)
Before biometric embedding extraction (InsightFace `buffalo_l` 512-d), images undergo automated pre-flight quality scoring:
- **Brightness Score:** Mean face region luminance must be between $40.0$ and $220.0$.
- **Sharpness Score:** Laplacian variance must be $\ge 80.0$ (rejects motion and optical blur).
- **Face Ratio:** Face bounding box must occupy between $4\%$ and $85\%$ of the total frame area.
- **Pose Angle:** Head rotation proxies must be within $\pm 30.0^\circ$ for Yaw (horizontal), Pitch (vertical), and Roll (tilt).

---

## 6. Realtime WebSocket Protocol (`/face/ws/kiosk`)

The Kiosk WebSocket connection provides low-latency multi-person biometric detection, tracking, and check-in streaming with strictly enforced tenant limits and JWT lifecycle verification.

### 6.1 Handshake, Authentication & Guardrails
Immediately upon WebSocket connection acceptance, the server issues a ready banner:
```json
// Server -> Client
{
  "type": "ready",
  "message": "Send session then identify/checkin frames",
  "faceCoreEnabled": false,
  "authTimeoutSeconds": 10.0,
  "queue": { "pending": 0, "active": 0 }
}
```

The client **must** authenticate within `authTimeoutSeconds` (default 10s) by sending a `session` message:
```json
// Client -> Server
{
  "type": "session",
  "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "token": "<kiosk_or_admin_jwt_token>",
  "stationMode": "ATTENDANCE",
  "zoneId": "zone-uuid-or-none",
  "latitude": 13.7563,
  "longitude": 100.5018
}
```

Upon verification of JWT validity, tenant match, and concurrency slots (`WS_KIOSK_MAX_CONN_PER_IP = 16`, `WS_KIOSK_MAX_CONN_PER_COMPANY = 64`), the server confirms:
```json
// Server -> Client
{
  "type": "session_ok",
  "companyId": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "companyCode": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "deviceId": "uuid-device-id",
  "stationMode": "ATTENDANCE",
  "zoneId": "zone-uuid-or-none",
  "queue": { "pending": 0, "active": 0 }
}
```

If session authentication fails, times out, or violates concurrency limits, the server emits `{"type": "error", "code": "...", "detail": "..."}` and immediately closes the connection with code `1008 Policy Violation` (e.g. `unauthenticated`, `auth_timeout`, `invalid_session`, `too_many_connections`).

### 6.2 Heartbeat, Keepalive & Token Expiration
- **Ping / Pong:** Client sends `{"type": "ping"}`. Server replies `{"type": "pong", "queue": { ... }}`.
- **Device Heartbeat:** Paired kiosks transmit telemetry:
```json
// Client -> Server
{
  "type": "heartbeat",
  "fingerprint": "client-fp-hash",
  "appVersion": "4.0.0",
  "config": {}
}

// Server -> Client
{
  "type": "heartbeat_ok",
  "deviceId": "uuid-device-id",
  "heartbeatAt": "2026-11-21T12:00:00Z"
}
```
- **Token Expiry Notice:** When $< 300$ seconds remain before JWT expiration, the server automatically emits `{"type": "token_expiring"}` so the client can refresh tokens asynchronously before disconnect. When expired, subsequent frames yield `{"type": "error", "code": "token_expired"}`.

### 6.3 Frame Evaluation & Match Dispatch
```json
// Client -> Server: Binary JPEG frame or Base64 payload
{
  "type": "detect",
  "frame": "data:image/jpeg;base64,...",
  "requestId": "req-101"
}

// Server -> Client: Match / Tracking Result
{
  "type": "detected",
  "requestId": "req-101",
  "faces": [
    {
      "trackingId": 101,
      "bbox": [120, 80, 340, 360],
      "matched": true,
      "identityType": "EMPLOYEE",
      "displayName": "Chanachai P.",
      "confidence": 0.942,
      "liveness": "PASSED"
    }
  ]
}
```

---

## 7. AI Copilot SSE Streaming Protocol

Endpoint: `POST /sentinel/company/{companyId}/assistant/chat` (Server-Sent Events)

### 7.1 Request Payload
```json
{
  "message": "Summarize security incidents on Floor 2 over the last 24 hours.",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "How can I assist you with SentinelVision?" }
  ]
}
```

### 7.2 Event Stream Format
```
event: token
data: {"delta": "Over the past 24 hours, "}

event: token
data: {"delta": "one Watchlist POI match was detected on Floor 2."}

event: done
data: {"metrics": {"tokens": 42, "latencyMs": 312}}
```
