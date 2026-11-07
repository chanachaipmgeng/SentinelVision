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

    # Soft dedupe: skip creating another timestamp for same employee within this window (0 = off)
    CHECK_IN_DEDUPE_SECONDS: int = 300

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
    # Negative-cache TTL for the revocation lookup (seconds). Revocations propagate to other
    # replicas within this window.
    AUTH_REVOCATION_CACHE_SECONDS: int = 30
    AUTH_REVOCATION_PURGE_SECONDS: int = 3600
    OIDC_ISSUER: str = ""
    OIDC_CLIENT_ID: str = ""
    CORS_ORIGINS: str = (
        "http://localhost,http://127.0.0.1,http://localhost:80,http://127.0.0.1:80,"
        "http://localhost:4200,http://localhost:4201,http://127.0.0.1:4200,"
        "http://127.0.0.1:4201,https://face-in.myhr.co.th,http://face-in.myhr.co.th"
    )
    AUTH_FAIL_FAST: bool = True
    MAX_FAILED_LOGINS: int = 5
    LOCKOUT_MINUTES: int = 15

    # Ops
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True
    EXPOSE_API_DOCS: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    HNSW_EF_SEARCH: int = 40

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

    # Phase-5 Cloud Storage (Local / S3 / MinIO)
    STORAGE_BACKEND: str = "local"
    IMAGE_RETENTION_DAYS: int = 90
    TEMP_RETENTION_HOURS: int = 24
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
    LINE_CHANNEL_ACCESS_TOKEN: str = ""
    NOTIFY_POLL_SECONDS: int = 30
    SERVICE_NOTIFY_TOKEN: str = ""
    WEBHOOK_SIGNING_SECRET: str = ""

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    def face_device_list(self) -> list[str]:
        raw = (self.FACE_DEVICES or "").strip() or (self.FACE_DEVICE or "cuda:0")
        return [p.strip() for p in raw.split(",") if p.strip()]


settings = Settings()
