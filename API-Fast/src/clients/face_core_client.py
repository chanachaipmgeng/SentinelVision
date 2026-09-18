"""Thin FastAPI adapter over face-core SDK (install sdk/python or sibling path)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Literal, Optional, Union

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

    IdentifyMode = _SdkIdentifyMode  # noqa: F811
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


class FaceCoreClient:
    """Wraps SDK client; maps FaceCoreError → HTTPException for FastAPI routes."""

    def __init__(self, base_url: str, api_key: str, *, timeout: float = 120.0):
        if _SdkClient is None:
            raise RuntimeError(
                "face_core SDK is not installed; set FACE_CORE_ENABLED=false "
                "or mount face-core/sdk/python"
            )
        self._inner = _SdkClient(base_url, api_key, timeout=timeout)

    async def ensure_company(self, company_code: str, display_name: Optional[str] = None) -> dict:
        try:
            return await self._inner.ensure_company(company_code, display_name=display_name)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def enroll(
        self,
        company_code: str,
        subject_id: str,
        file_path: Union[str, Path],
        *,
        filename: str = "face.jpg",
    ) -> dict:
        try:
            return await self._inner.enroll(
                company_code, subject_id, file_path, filename=filename
            )
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def identify(
        self,
        company_code: str,
        file_paths: List[Union[str, Path]],
        mode: IdentifyMode = "fast",
    ) -> dict:
        try:
            return await self._inner.identify(company_code, file_paths, mode=mode)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def verify(
        self,
        company_code: str,
        subject_id: str,
        file_path: Union[str, Path],
    ) -> dict:
        try:
            return await self._inner.verify(company_code, subject_id, file_path)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def list_faces(self, company_code: str, subject_id: str) -> List[dict]:
        try:
            return await self._inner.list_faces(company_code, subject_id)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def fetch_face_image(self, company_code: str, face_id: str) -> bytes:
        try:
            return await self._inner.fetch_face_image(company_code, face_id)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def delete_face(self, face_id: str) -> dict:
        try:
            return await self._inner.delete_face(face_id)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def clear_subject_faces(self, company_code: str, subject_id: str) -> dict:
        try:
            return await self._inner.clear_subject_faces(company_code, subject_id)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def detect(self, image_bytes: bytes) -> dict:
        try:
            return await self._inner.detect(image_bytes)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise

    async def queue_stats(self, company_code: Optional[str] = None) -> dict:
        try:
            return await self._inner.queue_stats(company_code=company_code)
        except FaceCoreError as exc:
            _raise_http(exc)
            raise


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
    return bool(settings.FACE_CORE_ENABLED and settings.FACE_CORE_API_KEY)


def bff_enrolled_image_url(face_id: str, company_id) -> str:
    """Browser-safe proxy path when Face Core stores enrolled JPEGs."""
    return f"/face/enrolled-images/{face_id}?companyId={company_id}"
