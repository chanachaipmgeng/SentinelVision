from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Face Recognition Settings
    FACE_RECOGNITION_THRESHOLD: float = 0.5

    # Image Quality Settings
    IMAGE_BLUR_THRESHOLD: float = 100.0  # Lower is more blurry
    IMAGE_BRIGHTNESS_MIN: int = 50       # Range 0-255
    IMAGE_BRIGHTNESS_MAX: int = 200      # Range 0-255

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

# Create a single instance of the settings
settings = Settings()
