from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Cosine distance threshold for InsightFace (lower = stricter). Match if distance < threshold.
    FACE_RECOGNITION_THRESHOLD: float = 0.40

    # Multi-frame liveness: max cosine distance between frame embeddings (same person)
    LIVENESS_SAME_PERSON_MAX_DISTANCE: float = 0.35
    # Minimum bbox center movement (pixels) across frames to reject a static photo
    LIVENESS_MIN_BBOX_MOTION: float = 4.0

    # Image Quality Settings
    IMAGE_BLUR_THRESHOLD: float = 100.0
    IMAGE_BRIGHTNESS_MIN: int = 50
    IMAGE_BRIGHTNESS_MAX: int = 200

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
