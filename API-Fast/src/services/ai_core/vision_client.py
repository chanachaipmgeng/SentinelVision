"""Sync HTTP client for ai-core-service vision-inference (:8090)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ...config.settings import settings

logger = logging.getLogger(__name__)

_vision_client: "SyncAiCoreVisionClient | None" = None


class SyncAiCoreVisionClient:
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"X-API-Key": api_key},
        )

    def close(self) -> None:
        self._client.close()

    def detect(
        self,
        image: bytes,
        *,
        filename: str = "frame.jpg",
        model_id: str | None = None,
        confidence: float | None = None,
        iou: float | None = None,
        imgsz: int | None = None,
        classes: str | None = None,
    ) -> dict[str, Any]:
        files = {"file": (filename, image, "image/jpeg")}
        data: dict[str, str] = {}
        if model_id:
            data["modelId"] = model_id
        if confidence is not None:
            data["confidence"] = str(confidence)
        if iou is not None:
            data["iou"] = str(iou)
        if imgsz is not None:
            data["imgsz"] = str(imgsz)
        if classes:
            data["classes"] = classes
        resp = self._client.post(
            f"{self.base_url}/v1/vision/detect",
            data=data or None,
            files=files,
        )
        resp.raise_for_status()
        return resp.json()


def get_vision_ai_core_client() -> SyncAiCoreVisionClient:
    global _vision_client
    url = (settings.AI_CORE_VISION_URL or "").strip()
    key = (settings.AI_CORE_API_KEY or "").strip()
    if not url or not key:
        raise RuntimeError(
            "Vision AI core client requested but AI_CORE_VISION_URL / AI_CORE_API_KEY empty"
        )
    if _vision_client is None:
        timeout = float(getattr(settings, "AI_CORE_VISION_TIMEOUT_SECONDS", 30.0) or 30.0)
        _vision_client = SyncAiCoreVisionClient(url, key, timeout=timeout)
    return _vision_client


def reset_vision_ai_core_client() -> None:
    global _vision_client
    if _vision_client is not None:
        try:
            _vision_client.close()
        except Exception:  # noqa: BLE001
            pass
    _vision_client = None
