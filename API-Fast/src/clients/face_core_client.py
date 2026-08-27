"""Async HTTP client for Face Core microservice."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Literal, Optional, Union

import httpx
from fastapi import HTTPException, UploadFile, status

from ..config.settings import settings

IdentifyMode = Literal["fast", "walkby", "secure"]

_client: Optional["FaceCoreClient"] = None


class FaceCoreClient:
    def __init__(self, base_url: str, api_key: str, *, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.is_success:
            return
        detail = response.text
        try:
            body = response.json()
            detail = body.get("detail", detail)
        except Exception:
            pass
        code = response.status_code
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

    async def ensure_company(self, company_code: str, display_name: Optional[str] = None) -> dict:
        params = {}
        if display_name:
            params["displayName"] = display_name
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.put(
                f"{self.base_url}/v1/companies/{company_code}",
                headers=self._headers(),
                params=params,
            )
            self._raise_for_status(r)
            return r.json()

    async def enroll(
        self,
        company_code: str,
        subject_id: str,
        file_path: Union[str, Path],
        *,
        filename: str = "face.jpg",
    ) -> dict:
        path = Path(file_path)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with path.open("rb") as fh:
                r = await client.post(
                    f"{self.base_url}/v1/companies/{company_code}/subjects/{subject_id}/faces",
                    headers=self._headers(),
                    files={"file": (filename, fh, "image/jpeg")},
                )
            self._raise_for_status(r)
            return r.json()

    async def identify(
        self,
        company_code: str,
        file_paths: List[Union[str, Path]],
        mode: IdentifyMode = "fast",
    ) -> dict:
        files = []
        handles = []
        try:
            for i, p in enumerate(file_paths):
                fh = open(p, "rb")
                handles.append(fh)
                files.append(("files", (f"frame{i}.jpg", fh, "image/jpeg")))
            data = {"companyCode": company_code, "mode": mode}
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.base_url}/v1/identify",
                    headers=self._headers(),
                    data=data,
                    files=files,
                )
                self._raise_for_status(r)
                return r.json()
        finally:
            for h in handles:
                h.close()

    async def verify(
        self,
        company_code: str,
        subject_id: str,
        file_path: Union[str, Path],
    ) -> dict:
        path = Path(file_path)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            with path.open("rb") as fh:
                r = await client.post(
                    f"{self.base_url}/v1/verify",
                    headers=self._headers(),
                    data={"companyCode": company_code, "subjectId": subject_id},
                    files={"file": ("probe.jpg", fh, "image/jpeg")},
                )
            self._raise_for_status(r)
            return r.json()

    async def list_faces(
        self, company_code: str, subject_id: str
    ) -> List[dict]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"{self.base_url}/v1/companies/{company_code}/subjects/{subject_id}/faces",
                headers=self._headers(),
            )
            self._raise_for_status(r)
            return r.json()

    async def delete_face(self, face_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.delete(
                f"{self.base_url}/v1/faces/{face_id}",
                headers=self._headers(),
            )
            self._raise_for_status(r)
            return r.json()

    async def clear_subject_faces(self, company_code: str, subject_id: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.delete(
                f"{self.base_url}/v1/companies/{company_code}/subjects/{subject_id}/faces",
                headers=self._headers(),
            )
            self._raise_for_status(r)
            return r.json()

    async def detect(self, image_bytes: bytes) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.base_url}/v1/detect",
                headers=self._headers(),
                files={"file": ("frame.jpg", image_bytes, "image/jpeg")},
            )
            self._raise_for_status(r)
            return r.json()

    async def queue_stats(self, company_code: Optional[str] = None) -> dict:
        params = {}
        if company_code:
            params["companyCode"] = company_code
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"{self.base_url}/v1/queue-stats",
                headers=self._headers(),
                params=params,
            )
            self._raise_for_status(r)
            return r.json()


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
