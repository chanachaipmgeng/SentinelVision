"""Thin FastAPI adapter over face-core SDK (install sdk/python or sibling path)."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Awaitable, Callable, List, Literal, Optional, TypeVar, Union

import httpx
from fastapi import HTTPException, status

from ..config.settings import settings

IdentifyMode = Literal["fast", "walkby", "secure"]


def _add_face_core_sdk_to_path() -> None:
    """Locate sibling face-core/sdk/python without assuming repo depth.

    Docker copies API-Fast to /app (too shallow for parents[4]). Dev trees
    keep dpu-project next to face-core — walk parents until that dir exists.
    """
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "face-core" / "sdk" / "python"
        if candidate.is_dir() and str(candidate) not in sys.path:
            sys.path.insert(0, str(candidate))
            return


_add_face_core_sdk_to_path()

try:
    from face_core.client import FaceCoreClient as _SdkClient
    from face_core.client import FaceCoreError, IdentifyMode as _SdkIdentifyMode

    IdentifyMode = _SdkIdentifyMode  # type: ignore[misc]  # noqa: F811
except ImportError as _import_err:
    _SdkClient = None  # type: ignore[assignment,misc]

    class FaceCoreError(Exception):  # type: ignore[no-redef]
        def __init__(self, detail: str = "", status_code: int = 502):
            super().__init__(detail)
            self.detail = detail
            self.status_code = status_code

    if settings.FACE_CORE_ENABLED:
        raise ImportError(
            "face_core SDK not found. pip install ../../../face-core/sdk/python "
            "or set PYTHONPATH to face-core/sdk/python"
        ) from _import_err

_client: Optional["FaceCoreClient"] = None
_fail_streak = 0
_open_until = 0.0
_T = TypeVar("_T")
_WEAK_KEYS = {"", "dev-face-core-key-change-me", "change-me", "changeme"}


def assert_face_core_configured() -> None:
    """Fail fast when BFF mode is on but the API key is missing or still the placeholder."""
    if not settings.FACE_CORE_ENABLED:
        return
    key = (settings.FACE_CORE_API_KEY or "").strip()
    if key in _WEAK_KEYS or len(key) < 16:
        raise RuntimeError(
            "FACE_CORE_ENABLED requires FACE_CORE_API_KEY (at least 16 characters, not the placeholder)"
        )


def face_core_circuit_open() -> bool:
    return time.monotonic() < _open_until


def _raise_http(exc: FaceCoreError) -> None:
    code = exc.status_code
    detail = exc.detail
    if code == 401:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)
    if code == 403:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
    if code == 404:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    if code == 429:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)
    if code == 504:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=detail)
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Face Core error ({code}): {detail}",
    )


async def _guarded(factory: Callable[[], Awaitable[_T]], *, retry: bool) -> _T:
    """One retry for idempotent calls, then open a short circuit so kiosks see face_core_down."""
    global _fail_streak, _open_until
    if time.monotonic() < _open_until:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="face_core_down")
    last: Optional[BaseException] = None
    attempts = 2 if retry else 1
    for i in range(attempts):
        try:
            result = await factory()
            _fail_streak = 0
            return result
        except FaceCoreError as exc:
            last = exc
            if exc.status_code < 500 or i == attempts - 1:
                break
        except Exception as exc:
            last = exc
            if i == attempts - 1:
                break
    _fail_streak += 1
    if _fail_streak >= 3:
        _open_until = time.monotonic() + 15
        _fail_streak = 0
    if isinstance(last, FaceCoreError) and last.status_code < 500:
        _raise_http(last)
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="face_core_down")


class FaceCoreClient:
    """Wraps SDK client; maps FaceCoreError → HTTPException for FastAPI routes."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 120.0):
        if _SdkClient is None:
            raise RuntimeError(
                "face_core SDK is not installed; set FACE_CORE_ENABLED=false "
                "or bake face-core/sdk/python into the image"
            )
        self._inner = _SdkClient(base_url, api_key, timeout=timeout)

    async def ensure_company(self, company_code: str, display_name: Optional[str] = None) -> dict:
        return await _guarded(
            lambda: self._inner.ensure_company(company_code, display_name=display_name),
            retry=True,
        )

    async def enroll(
        self,
        company_code: str,
        subject_id: str,
        file_path: Union[str, Path],
        *,
        filename: str = "face.jpg",
    ) -> dict:
        return await _guarded(
            lambda: self._inner.enroll(company_code, subject_id, file_path, filename=filename),
            retry=False,
        )

    async def identify(
        self,
        company_code: str,
        file_paths: List[Union[str, Path]],
        mode: IdentifyMode = "fast",
    ) -> dict:
        return await _guarded(
            lambda: self._inner.identify(company_code, file_paths, mode=mode),
            retry=True,
        )

    async def verify(
        self,
        company_code: str,
        subject_id: str,
        file_path: Union[str, Path],
    ) -> dict:
        return await _guarded(
            lambda: self._inner.verify(company_code, subject_id, file_path),
            retry=True,
        )

    async def list_faces(self, company_code: str, subject_id: str) -> List[dict]:
        return await _guarded(
            lambda: self._inner.list_faces(company_code, subject_id),
            retry=True,
        )

    async def fetch_face_image(self, company_code: str, face_id: str) -> bytes:
        return await _guarded(
            lambda: self._inner.fetch_face_image(company_code, face_id),
            retry=True,
        )

    async def delete_face(self, face_id: str) -> dict:
        return await _guarded(lambda: self._inner.delete_face(face_id), retry=False)

    async def clear_subject_faces(self, company_code: str, subject_id: str) -> dict:
        return await _guarded(
            lambda: self._inner.clear_subject_faces(company_code, subject_id),
            retry=False,
        )

    async def detect(self, image_bytes: bytes) -> dict:
        return await _guarded(lambda: self._inner.detect(image_bytes), retry=True)

    async def queue_stats(self, company_code: Optional[str] = None) -> dict:
        return await _guarded(
            lambda: self._inner.queue_stats(company_code=company_code),
            retry=True,
        )


def get_face_core_client() -> FaceCoreClient:
    global _client
    if _client is None:
        if not settings.FACE_CORE_API_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="FACE_CORE_API_KEY is not configured",
            )
        _client = FaceCoreClient(
            settings.FACE_CORE_URL.rstrip("/"),
            settings.FACE_CORE_API_KEY,
            timeout=float(settings.FACE_CORE_TIMEOUT_SECONDS),
        )
    return _client


def face_core_enabled() -> bool:
    key = (settings.FACE_CORE_API_KEY or "").strip()
    return bool(settings.FACE_CORE_ENABLED and key and key not in _WEAK_KEYS)


async def ping_face_core() -> dict:
    url = settings.FACE_CORE_URL.rstrip("/") + "/v1/health"
    async with httpx.AsyncClient(timeout=3.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            return {"status": "ok"}
        return body


def bff_enrolled_image_url(face_id: str, company_id) -> str:
    """Browser-safe proxy path when Face Core stores enrolled JPEGs."""
    return f"/face/enrolled-images/{face_id}?companyId={company_id}"
