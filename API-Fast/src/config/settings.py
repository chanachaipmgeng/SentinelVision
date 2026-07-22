from pydantic_settings import BaseSettings


class Settings(BaseSettings):
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
    # (Laplacian variance; lower = allow blurrier webcam frames)
    IMAGE_BLUR_THRESHOLD: float = 20.0
    IMAGE_BRIGHTNESS_MIN: int = 40
    IMAGE_BRIGHTNESS_MAX: int = 220

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
