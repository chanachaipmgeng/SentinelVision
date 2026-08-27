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

    # Soft dedupe: skip creating another timestamp for same employee within this window (0 = off)
    CHECK_IN_DEDUPE_SECONDS: int = 300

    # Phase-3 GPU queue: parallel InsightFace workers (1 recommended for single GPU)
    FACE_GPU_WORKERS: int = 1
    FACE_GPU_QUEUE_SIZE: int = 64

    # InsightFace / ONNX device: "cuda:0" (default, AI_VISION-style) or "cpu"
    FACE_DEVICE: str = "cuda:0"

    # Image Quality Settings — measured on face crop when available
    IMAGE_BLUR_THRESHOLD: float = 20.0
    IMAGE_BRIGHTNESS_MIN: int = 40
    IMAGE_BRIGHTNESS_MAX: int = 220

    # Face Core microservice (BFF mode)
    FACE_CORE_ENABLED: bool = False
    FACE_CORE_URL: str = "http://host.docker.internal:8081"
    FACE_CORE_API_KEY: str = ""
    FACE_CORE_TIMEOUT_SECONDS: float = 120.0


settings = Settings()
