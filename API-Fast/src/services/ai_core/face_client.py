"""Sync HTTP client for ai-core-service face-inference (:8089)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ...config.settings import settings

logger = logging.getLogger(__name__)

_face_client: "SyncAiCoreFaceClient | None" = None


class SyncAiCoreFaceClient:
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout, connect=10.0),
            headers={"X-API-Key": api_key},
        )

    def close(self) -> None:
        self._client.close()

    def detect(self, image: bytes, *, filename: str = "frame.jpg") -> dict[str, Any]:
        files = {"file": (filename, image, "image/jpeg")}
        resp = self._client.post(f"{self.base_url}/v1/vision/face/detect", files=files)
        resp.raise_for_status()
        return resp.json()

    def embed(
        self,
        image: bytes,
        *,
        filename: str = "frame.jpg",
        max_faces: int = 1,
        pre_cropped: bool = False,
    ) -> dict[str, Any]:
        files = {"file": (filename, image, "image/jpeg")}
        data = {
            "maxFaces": str(max(1, int(max_faces))),
            "preCropped": "true" if pre_cropped else "false",
        }
        resp = self._client.post(
            f"{self.base_url}/v1/vision/face/embed",
            data=data,
            files=files,
        )
        resp.raise_for_status()
        return resp.json()

    def quality(
        self,
        image: bytes,
        *,
        filename: str = "frame.jpg",
        angle: str | None = None,
    ) -> dict[str, Any]:
        files = {"file": (filename, image, "image/jpeg")}
        data = {"angle": angle} if angle else None
        resp = self._client.post(
            f"{self.base_url}/v1/vision/face/quality",
            data=data,
            files=files,
        )
        resp.raise_for_status()
        return resp.json()

    def liveness(self, frames: list[bytes]) -> dict[str, Any]:
        files = [
            ("files", (f"f{i}.jpg", frame, "image/jpeg")) for i, frame in enumerate(frames)
        ]
        resp = self._client.post(f"{self.base_url}/v1/vision/face/liveness", files=files)
        resp.raise_for_status()
        return resp.json()


def get_face_ai_core_client() -> SyncAiCoreFaceClient:
    global _face_client
    url = (settings.AI_CORE_FACE_URL or "").strip()
    key = (settings.AI_CORE_API_KEY or "").strip()
    if not url or not key:
        raise RuntimeError("Face AI core client requested but AI_CORE_FACE_URL / AI_CORE_API_KEY empty")
    if _face_client is None:
        timeout = float(getattr(settings, "AI_CORE_FACE_TIMEOUT_SECONDS", 30.0) or 30.0)
        _face_client = SyncAiCoreFaceClient(url, key, timeout=timeout)
    return _face_client


def reset_face_ai_core_client() -> None:
    global _face_client
    if _face_client is not None:
        try:
            _face_client.close()
        except Exception:  # noqa: BLE001
            pass
    _face_client = None
