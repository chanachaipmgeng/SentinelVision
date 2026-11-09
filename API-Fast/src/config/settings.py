from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Cosine distance threshold for InsightFace (lower = stricter). Match if distance < threshold.
    FACE_RECOGNITION_THRESHOLD: float = 0.40

    # Multi-frame liveness: max cosine distance between frame embeddings (same person)
    LIVENESS_SAME_PERSON_MAX_DISTANCE: float = 0.35
    # Minimum bbox center movement (pixels) across frames to reject a static photo
    LIVENESS_MIN_BBOX_MOTION: float = 4.0

    # Phase-4 Single-Frame Passive Anti-Spoofing (YCrCb chrominance + screen glare / Moiré check)
    FACE_ANTISPOOF_ENABLED: bool = True
    FACE_ANTISPOOF_MIN_CHROMA_STD: float = 2.0
    FACE_ANTISPOOF_MAX_SPECULAR_RATIO: float = 0.22

    # D8 PAD (MiniFASNet-compatible ONNX). Empty = heuristic only. See docs/FACE-PAD.md.
    FACE_PAD_MODEL_PATH: str = ""
    FACE_PAD_MIN_LIVE_SCORE: float = 0.80
    FACE_PAD_FAIL_CLOSED: bool = True
    # Embedding pack / model pin stored on FaceEncoding.modelVersion at enroll.
    FACE_MODEL_VERSION: str = "buffalo_l"
    # Enrollment quality gate (face ratio / pose / sharpness) on add-face.
    ENROLL_QUALITY_GATE_ENABLED: bool = True
    ENROLL_MIN_FACE_RATIO: float = 0.08
    ENROLL_MAX_YAW_DEG: float = 25.0
    ENROLL_MAX_ROLL_DEG: float = 20.0
    ENROLL_MIN_SHARPNESS: float = 25.0

    # D7 app rate limits (per IP / minute). 0 disables. Complements nginx limit_req.
    REDIS_URL: str = ""
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 20
    RATE_LIMIT_IDENTIFY_PER_MINUTE: int = 120
    RATE_LIMIT_IMPORT_PER_MINUTE: int = 10
    # D6 Idempotency-Key TTL for punch create + import-jobs.
    IDEMPOTENCY_TTL_SECONDS: int = 86400

    # Soft dedupe: skip creating another timestamp for same employee within this window (0 = off)
    CHECK_IN_DEDUPE_SECONDS: int = 300
    # F1: open sentinel incident dedupe window (same company/identity/eventType/zone)
    SENTINEL_INCIDENT_DEDUPE_SECONDS: int = 300

    # Phase-3 GPU queue: parallel InsightFace workers (1 recommended for single GPU)
    FACE_GPU_WORKERS: int = 1
    FACE_GPU_QUEUE_SIZE: int = 64

    # InsightFace / ONNX device: "cuda:0" (default, AI_VISION-style) or "cpu"
    FACE_DEVICE: str = "cuda:0"

    # Image Quality Settings — measured on face crop when available
    IMAGE_BLUR_THRESHOLD: float = 20.0
    # Excel import of photos from other systems. 0 = skip blur reject (face still required).
    IMAGE_BLUR_THRESHOLD_IMPORT: float = 0.0
    IMAGE_BRIGHTNESS_MIN: int = 40
    IMAGE_BRIGHTNESS_MAX: int = 220

    # Face Core microservice (BFF mode)
    FACE_CORE_ENABLED: bool = False
    FACE_CORE_URL: str = "http://host.docker.internal:8081"
    FACE_CORE_API_KEY: str = ""
    FACE_CORE_TIMEOUT_SECONDS: float = 120.0

    # When true, /face/* HTTP routes require JWT. WS session must carry the same token.
    FACE_ROUTES_REQUIRE_JWT: bool = True

    # Auth & Enterprise OIDC SSO
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    # Device-scoped kiosk token (short, refreshable) + kiosk refresh token lifetime.
    KIOSK_TOKEN_EXPIRE_HOURS: int = 12
    KIOSK_REFRESH_EXPIRE_DAYS: int = 30
    # One-time pairing code shown to the admin; the kiosk exchanges it at /auth/kiosk/pair.
    KIOSK_PAIRING_CODE_TTL_MINUTES: int = 10
    KIOSK_PAIR_MAX_ATTEMPTS_PER_MINUTE: int = 10
    # Deprecated: accept `?token=` in the query string. Leaks tokens into access logs; off by default.
    AUTH_ALLOW_QUERY_TOKEN: bool = False
    # Browser session: httpOnly refresh cookie + double-submit CSRF (E4).
    AUTH_REFRESH_COOKIE_NAME: str = "dpu_refresh"
    AUTH_CSRF_COOKIE_NAME: str = "dpu_csrf"
    AUTH_CSRF_HEADER: str = "X-CSRF-Token"
    # Secure cookies when not running a local/dev APP_ENV.
    AUTH_COOKIE_SECURE: bool | None = None
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    # When true (or APP_ENV=development), /auth/send-reset-password may echo resetToken for QA.
    AUTH_EXPOSE_RESET_TOKEN: bool = False
    # Negative-cache TTL for the revocation lookup (seconds). Revocations propagate to other
    # replicas within this window.
    AUTH_REVOCATION_CACHE_SECONDS: int = 30
    AUTH_REVOCATION_PURGE_SECONDS: int = 3600
    # OIDC SSO relying party (Authorization Code + PKCE). Fail-fast when enabled but incomplete.
    OIDC_ENABLED: bool = False
    OIDC_ISSUER: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = ""
    OIDC_SCOPES: str = "openid profile email"
    OIDC_HTTP_TIMEOUT_SECONDS: float = 10.0
    OIDC_JWKS_CACHE_SECONDS: int = 3600
    OIDC_LOGIN_TXN_TTL_SECONDS: int = 600
    OIDC_CLOCK_SKEW_SECONDS: int = 60
    CORS_ORIGINS: str = (
        "http://localhost,http://127.0.0.1,http://localhost:80,http://127.0.0.1:80,"
        "http://localhost:4200,http://localhost:4201,http://127.0.0.1:4200,"
        "http://127.0.0.1:4201,https://face-in.myhr.co.th,http://face-in.myhr.co.th"
    )
    AUTH_FAIL_FAST: bool = True
    # production (default) = weak SECRET_KEY / example DB password abort startup;
    # development = DB password only warns. See security/startup_checks.py.
    APP_ENV: str = "production"
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15

    # Database schema (Alembic is the single source of truth; see docs/RUNBOOK.md)
    # Run `alembic upgrade head` inside the API process before serving. Off by default: run the
    # migration as a separate step (`alembic upgrade head` / scripts/migrate.sh) so multi-replica
    # deployments do not race and a failed migration does not take the API down with it.
    MIGRATE_ON_STARTUP: bool = False
    # /ready returns 503 (`schema_out_of_date`) while alembic_version != head. Set false to only log.
    REQUIRE_SCHEMA_HEAD: bool = True

    # Ops
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    EXPOSE_API_DOCS: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    HNSW_EF_SEARCH: int = 40
    # OpenTelemetry tracing (B6). Off unless an OTLP endpoint is set; the standard OTEL_* env
    # names are honoured by the SDK too, these only document the knobs and allow .env usage.
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""
    OTEL_EXPORTER_OTLP_PROTOCOL: str = "http/protobuf"
    OTEL_SERVICE_NAME: str = ""

    # Background jobs (B7). The outbox dispatcher, attendance cutoff, storage retention,
    # sentinel expiry, revocation purge and employee import processing run in the separate
    # `worker` service (`python -m src.worker`). Set RUN_BACKGROUND_JOBS_IN_API=true for a
    # single-container dev setup to run the same loops inside the API process instead.
    RUN_BACKGROUND_JOBS_IN_API: bool = False
    WORKER_ID: str = ""
    WORKER_JOBS: str = "outbox,retention,imports,attendance_summary"
    WORKER_METRICS_PORT: int = 9108
    WORKER_RETENTION_INTERVAL_SECONDS: int = 3600
    WORKER_IMPORT_POLL_SECONDS: int = 2
    # C1 nightly attendance_daily recompute (default 6h; hooks cover same-day punches).
    WORKER_ATTENDANCE_SUMMARY_INTERVAL_SECONDS: int = 21600
    # A running import whose heartbeat is older than this is considered orphaned (worker died).
    WORKER_IMPORT_LEASE_SECONDS: int = 900
    WORKER_SHUTDOWN_GRACE_SECONDS: int = 30
    # Directory (shared volume between api and worker) holding uploaded import files per job.
    IMPORT_JOB_DIR: str = "import_jobs"
    IMPORT_JOB_RETENTION_DAYS: int = 7

    # Multi-GPU. Comma list; worker i uses devices[i % len].
    FACE_DEVICES: str = ""
    FACE_DETECT_DET_SIZE: int = 320
    FACE_EMBED_DET_SIZE: int = 640
    WS_DETECT_MIN_INTERVAL_MS: int = 80
    WS_QUEUE_BACKPRESSURE: int = 32
    # Drop detect jobs that waited longer than this (ms) — stale boxes are useless.
    FACE_DETECT_STALE_MS: int = 400
    # Reuse identify embedding for walk-by check-in on the same WS track.
    FACE_IDENTIFY_CACHE_SECONDS: float = 3.0
    # WS identify/check-in: detect at FACE_DETECT_DET_SIZE then embed (skip 640 det).
    FACE_FAST_EMBED_DETECT: bool = True

    # Kiosk WebSocket hardening. A socket that has not completed a valid `session`
    # within this many seconds is closed (1008). Any non-`session` message before
    # auth also closes the socket, so unauthenticated clients never reach the GPU.
    WS_KIOSK_AUTH_TIMEOUT_SECONDS: float = 5.0
    # Per-process concurrent kiosk sockets per client IP / per company (0 = unlimited).
    # nginx `limit_conn` on /face/ws/ is the gateway-level counterpart (see docker/nginx).
    WS_KIOSK_MAX_CONN_PER_IP: int = 16
    WS_KIOSK_MAX_CONN_PER_COMPANY: int = 64

    # Phase-5 Cloud Storage (Local / S3 / MinIO)
    STORAGE_BACKEND: str = "local"
    IMAGE_RETENTION_DAYS: int = 90
    # Global fallback for incident_* evidence; primary policy is PDPA incidentSnapshotDays.
    INCIDENT_SNAPSHOT_RETENTION_DAYS: int = 90
    # Event/continuous clips — separate from punch-photo policy (Phase 4B).
    VIDEO_CLIP_RETENTION_DAYS: int = 30
    TEMP_RETENTION_HOURS: int = 24
    # Event clip window: 5s pre-roll / 10s post-roll around incident time.
    VIDEO_CLIP_PRE_SECONDS: int = 5
    VIDEO_CLIP_POST_SECONDS: int = 10
    VIDEO_CLIP_FFMPEG_BIN: str = "ffmpeg"
    VIDEO_CLIP_FFMPEG_TIMEOUT_SECONDS: int = 90
    UPLOAD_MAX_BYTES: int = 8 * 1024 * 1024
    S3_ENDPOINT_URL: str = ""
    S3_REGION: str = "ap-southeast-1"
    S3_BUCKET: str = "dpu-attendance"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_PRESIGN_EXPIRES_SECONDS: int = 3600

    # Notifications & Signed Payroll Webhooks
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True
    # LINE Messaging API (push). Replaces discontinued LINE Notify.
    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    LINE_MESSAGING_API_BASE: str = "https://api.line.me/v2/bot"
    # Fernet key for secrets inside notification_outbox.payload (url-safe 32-byte key).
    # Generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    OUTBOX_ENCRYPTION_KEY: str = ""
    NOTIFY_POLL_SECONDS: int = 30
    SERVICE_NOTIFY_TOKEN: str = ""
    WEBHOOK_SIGNING_SECRET: str = ""

    # Phase 3 CCTV / MediaMTX
    MEDIAMTX_ENABLED: bool = True
    MEDIAMTX_API_URL: str = "http://mediamtx:9997"
    MEDIAMTX_WHEP_BASE_PATH: str = "/mediamtx"
    MEDIAMTX_HLS_BASE_PATH: str = "/mediamtx-hls"
    MEDIAMTX_RTSP_PUBLISH_URL: str = "rtsp://mediamtx:8554"
    # Shared with the mediamtx container (compose volume mediamtx_recordings).
    MEDIAMTX_RECORDINGS_DIR: str = "/recordings"
    # Internal HLS base for ffmpeg clip cut (docker network, not browser path).
    MEDIAMTX_HLS_INTERNAL_URL: str = "http://mediamtx:8888"

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def face_device_list(self) -> list[str]:
        raw = (self.FACE_DEVICES or "").strip() or (self.FACE_DEVICE or "cuda:0")
        return [p.strip() for p in raw.split(",") if p.strip()]


settings = Settings()
