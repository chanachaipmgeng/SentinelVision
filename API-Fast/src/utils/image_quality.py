import cv2
from typing import Tuple
from ..config.settings import settings

def check_image_quality(image_path: str) -> Tuple[bool, str]:
    """
    Checks the quality of an image based on brightness and blurriness.

    Args:
        image_path: The path to the image file.

    Returns:
        A tuple containing a boolean (True if quality is good) and a message string.
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            return False, "Could not read the image file."

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 1. Brightness Check
        brightness = gray.mean()
        if not (settings.IMAGE_BRIGHTNESS_MIN <= brightness <= settings.IMAGE_BRIGHTNESS_MAX):
            return False, f"Image brightness ({brightness:.2f}) is outside the acceptable range ({settings.IMAGE_BRIGHTNESS_MIN}-{settings.IMAGE_BRIGHTNESS_MAX})."

        # 2. Blur Check (Variance of Laplacian)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_value < settings.IMAGE_BLUR_THRESHOLD:
            return False, f"Image is too blurry (Blur value: {blur_value:.2f}, Threshold: {settings.IMAGE_BLUR_THRESHOLD})."

        return True, "Image quality is good."

    except Exception as e:
        return False, f"An error occurred during image quality check: {str(e)}"
