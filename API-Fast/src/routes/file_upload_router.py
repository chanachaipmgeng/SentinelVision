"""Tenant-scoped image upload and authenticated media serving (/images, /enrolled_images, /api/get-image)."""
from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..config.settings import settings
from ..models.company import Company
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import EmployeeTimestamp
from ..models.face_encoding import FaceEncoding
from ..models.member import Member
from ..models.rbac import MemberRoleAssignment
from ..models.sentinel import SentinelIdentity, SentinelIncidentLog
from ..models.site_floor import SiteFloor
from ..security.deps import (
    assert_request_company_access,
    current_kiosk_company_var,
    current_member_var,
    get_current_member,
)
from ..services import rbac_service
from ..services.storage_service import (
    ROOTS,
    generate_presigned_url,
    read_image_bytes_async,
    store_image_bytes_async,
)

router = APIRouter(dependencies=[Depends(get_current_member)])
media_router = APIRouter()

UPLOAD_DIR = ROOTS["uploaded_images"]
UPLOAD_DIR.mkdir(exist_ok=True)
ENROLLED_DIR = ROOTS["enrolled_images"]
ENROLLED_DIR.mkdir(exist_ok=True)
_ALLOWED = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png"}
_MAX = int(settings.UPLOAD_MAX_BYTES)


def _safe_rel_parts(raw_path: str) -> tuple[Optional[UUID], str]:
    clean = (raw_path or "").replace("\\", "/").strip("/")
    if not clean:
        raise HTTPException(status_code=400, detail="Invalid filename")
    parts = [p for p in clean.split("/") if p]
    if not parts or any(p in {".", ".."} for p in parts):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if len(parts) == 1:
        return None, parts[0]
    if len(parts) == 2:
        try:
            cid = UUID(parts[0])
            return cid, parts[1]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid media path") from None
    raise HTTPException(status_code=400, detail="Invalid media path")


def _safe_name(filename: str) -> str:
    _, name = _safe_rel_parts(filename)
    return name


def _sniff(content: bytes) -> str:
    if len(content) < 8 or len(content) > _MAX:
        raise HTTPException(status_code=400, detail="Invalid image size")
    for magic, ext in _ALLOWED.items():
        if content.startswith(magic):
            return ext
    raise HTTPException(status_code=400, detail="Only JPEG and PNG image files are allowed")


async def _caller_company_scope(request: Request, db: AsyncSession) -> tuple[bool, set[UUID]]:
    """Return (is_unrestricted_system_admin, allowed_company_ids)."""
    kiosk_cid = getattr(request.state, "kiosk_company_id", None) or current_kiosk_company_var.get()
    if kiosk_cid is not None:
        return False, {UUID(str(kiosk_cid))}

    member: Optional[Member] = getattr(request.state, "member", None) or current_member_var.get()
    if member is None:
        raise HTTPException(status_code=401, detail="Authorization required")
    if rbac_service.is_system_admin_member(member):
        return True, set()

    emp_rows = (
        await db.execute(
            select(CompanyEmployee.companyId).where(
                CompanyEmployee.memberId == member.memberId,
                CompanyEmployee.deletedAt.is_(None),
            )
        )
    ).scalars().all()
    role_rows = (
        await db.execute(
            select(MemberRoleAssignment.companyId).where(
                MemberRoleAssignment.memberId == member.memberId,
                MemberRoleAssignment.companyId.isnot(None),
            )
        )
    ).scalars().all()
    allowed = {c for c in emp_rows if c is not None} | {c for c in role_rows if c is not None}
    return False, allowed


async def _owning_companies_for_legacy_file(
    db: AsyncSession, folder: str, filename: str
) -> set[UUID]:
    """Resolve owning companyId(s) for legacy flat filenames stored in DB columns."""
    owners: set[UUID] = set()
    if folder == "enrolled_images":
        rows = (
            await db.execute(
                select(FaceEncoding.companyId).where(
                    or_(
                        FaceEncoding.imagePath == filename,
                        FaceEncoding.imagePath.like(f"%/{filename}"),
                    )
                )
            )
        ).scalars().all()
        owners.update(c for c in rows if c is not None)
        return owners

    # uploaded_images: punch photos, incident snapshots, watchlist portraits, floor plans, logos.
    patterns = (filename, f"%/{filename}")
    for _model_cls, cid_col, col in (
        (EmployeeTimestamp, EmployeeTimestamp.companyId, EmployeeTimestamp.photoTimestamp),
        (SentinelIncidentLog, SentinelIncidentLog.companyId, SentinelIncidentLog.snapshotUrl),
        (SentinelIdentity, SentinelIdentity.companyId, SentinelIdentity.pictureUrl),
        (SiteFloor, SiteFloor.companyId, SiteFloor.imageUrl),
        (Company, Company.companyId, Company.picture),
    ):
        rows = (
            await db.execute(
                select(cid_col).where(or_(col == patterns[0], col.like(patterns[1])))
            )
        ).scalars().all()
        owners.update(c for c in rows if c is not None)
    return owners


def _resolve_local_path(folder: str, path_cid: Optional[UUID], filename: str) -> Path:
    root = ROOTS[folder].resolve()
    candidates = (
        [root / str(path_cid) / filename, root / filename]
        if path_cid is not None
        else [root / filename]
    )
    for cand in candidates:
        resolved = cand.resolve()
        if root not in resolved.parents and resolved != root:
            raise HTTPException(status_code=400, detail="Invalid filename")
        if resolved.is_file():
            return resolved
    return candidates[0].resolve()


async def _authorize_and_resolve(
    request: Request,
    db: AsyncSession,
    folder: str,
    raw_path: str,
) -> tuple[Path, str]:
    path_cid, filename = _safe_rel_parts(raw_path)
    is_sys, allowed = await _caller_company_scope(request, db)
    if not is_sys:
        if path_cid is not None:
            if path_cid not in allowed:
                raise HTTPException(status_code=403, detail="Forbidden: cross-tenant media access")
        else:
            owners = await _owning_companies_for_legacy_file(db, folder, filename)
            if not owners or not (owners & allowed):
                raise HTTPException(status_code=403, detail="Forbidden: media belongs to another tenant")
    resolved = _resolve_local_path(folder, path_cid, filename)
    return resolved, filename


async def _save_bytes(content: bytes, *, company_id: Optional[UUID] = None) -> JSONResponse:
    ext = _sniff(content)
    new_filename = f"{uuid4()}{ext}"
    mime = "image/png" if ext == ".png" else "image/jpeg"
    if company_id is not None:
        rel_dir = UPLOAD_DIR / str(company_id)

        def _write_tenant() -> None:
            rel_dir.mkdir(parents=True, exist_ok=True)
            (rel_dir / new_filename).write_bytes(content)

        await asyncio.to_thread(_write_tenant)
        await store_image_bytes_async("uploaded_images", f"{company_id}_{new_filename}", content, content_type=mime)
        url_path = f"/images/{company_id}/{new_filename}"
        presigned = generate_presigned_url("uploaded_images", f"{company_id}_{new_filename}")
    else:
        await store_image_bytes_async("uploaded_images", new_filename, content, content_type=mime)
        url_path = f"/images/{new_filename}"
        presigned = generate_presigned_url("uploaded_images", new_filename)
    return JSONResponse(
        status_code=200,
        content={
            "message": "File uploaded successfully",
            "filename": new_filename,
            "path": url_path,
            "presignedUrl": presigned,
        },
    )


@router.post("/upload-image")
@router.post("/upload-image/")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    companyId: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if companyId is not None:
        await assert_request_company_access(request, db, companyId)
    content = await file.read(_MAX + 1)
    if len(content) > _MAX:
        raise HTTPException(status_code=400, detail="Invalid image size")
    return await _save_bytes(content, company_id=companyId)


@router.post("/upload-image-base64")
@router.post("/upload-image-base64/")
async def upload_image_base64(
    request: Request,
    base64_image: str = Form(...),
    companyId: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if companyId is not None:
        await assert_request_company_access(request, db, companyId)
    raw = base64_image
    if raw.startswith("data:image/jpeg;base64,"):
        raw = raw.split(",", 1)[1]
    elif raw.startswith("data:image/png;base64,"):
        raw = raw.split(",", 1)[1]
    else:
        raise HTTPException(status_code=400, detail="Unsupported image format")
    try:
        content = base64.b64decode(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 string") from None
    return await _save_bytes(content, company_id=companyId)


@router.get("/get-image/{filename:path}")
async def get_image(
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    path, safe_name = await _authorize_and_resolve(request, db, "uploaded_images", filename)
    media = "image/png" if path.suffix == ".png" else "image/jpeg"
    if path.is_file():
        return FileResponse(
            path,
            media_type=media,
            filename=path.name,
            headers={"Cache-Control": "private, max-age=300"},
        )
    data = await read_image_bytes_async("uploaded_images", safe_name)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type=media, headers={"Cache-Control": "private, max-age=300"})


@router.get("/get-image-base64/{filename:path}")
async def get_image_base64(
    filename: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    path, safe_name = await _authorize_and_resolve(request, db, "uploaded_images", filename)
    data = await asyncio.to_thread(path.read_bytes) if path.is_file() else await read_image_bytes_async("uploaded_images", safe_name)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    encoded = base64.b64encode(data).decode("utf-8")
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return JSONResponse(
        content={"filename": path.name, "mime_type": mime, "data": f"data:{mime};base64,{encoded}"}
    )


@media_router.get("/images/{file_path:path}", tags=["Media"])
async def serve_uploaded_image(
    file_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    path, safe_name = await _authorize_and_resolve(request, db, "uploaded_images", file_path)
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    if path.is_file():
        return FileResponse(path, media_type=media, headers={"Cache-Control": "private, max-age=300"})
    data = await read_image_bytes_async("uploaded_images", safe_name)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type=media, headers={"Cache-Control": "private, max-age=300"})


@media_router.get("/enrolled_images/{file_path:path}", tags=["Media"])
async def serve_enrolled_image(
    file_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    path, safe_name = await _authorize_and_resolve(request, db, "enrolled_images", file_path)
    media = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    if path.is_file():
        return FileResponse(path, media_type=media, headers={"Cache-Control": "private, max-age=300"})
    data = await read_image_bytes_async("enrolled_images", safe_name)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type=media, headers={"Cache-Control": "private, max-age=300"})
