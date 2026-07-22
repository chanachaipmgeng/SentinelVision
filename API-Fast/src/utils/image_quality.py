import cv2
import numpy as np
from typing import Optional, Tuple, Union

from ..config.settings import settings


def check_image_quality(
    image_path: str,
    bbox: Optional[Union[np.ndarray, list]] = None,
) -> Tuple[bool, str]:
    """
    Brightness + blur (Laplacian variance).

    When ``bbox`` [x1,y1,x2,y2] is provided, metrics use the face crop
    (webcam full-frames often fail blur because soft backgrounds dominate).
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            return False, "Could not read the image file."

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        region = _face_region(gray, bbox) if bbox is not None else gray
        if region.size == 0:
            return False, "Face region is empty."

        brightness = float(region.mean())
        if not (settings.IMAGE_BRIGHTNESS_MIN <= brightness <= settings.IMAGE_BRIGHTNESS_MAX):
            return (
                False,
                f"Image brightness ({brightness:.2f}) is outside the acceptable range "
                f"({settings.IMAGE_BRIGHTNESS_MIN}-{settings.IMAGE_BRIGHTNESS_MAX}).",
            )

        blur_value = float(cv2.Laplacian(region, cv2.CV_64F).var())
        if blur_value < settings.IMAGE_BLUR_THRESHOLD:
            return (
                False,
                f"Image is too blurry (Blur value: {blur_value:.2f}, "
                f"Threshold: {settings.IMAGE_BLUR_THRESHOLD}).",
            )

        return True, "Image quality is good."

    except Exception as e:
        return False, f"An error occurred during image quality check: {str(e)}"


def _face_region(gray: np.ndarray, bbox: Union[np.ndarray, list]) -> np.ndarray:
    h, w = gray.shape[:2]
    x1, y1, x2, y2 = [float(v) for v in bbox[:4]]
    bw = max(1.0, x2 - x1)
    bh = max(1.0, y2 - y1)
    pad_x = bw * 0.15
    pad_y = bh * 0.15
    left = max(0, int(x1 - pad_x))
    top = max(0, int(y1 - pad_y))
    right = min(w, int(x2 + pad_x))
    bottom = min(h, int(y2 + pad_y))
    if right <= left or bottom <= top:
        return gray
    return gray[top:bottom, left:right]
