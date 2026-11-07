from pathlib import Path
from uuid import uuid4
import base64
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse, FileResponse, Response

from ..config.settings import settings
from ..security.deps import get_current_member
from ..services.storage_service import (
    generate_presigned_url,
    read_image_bytes,
    store_image_bytes,
)

router = APIRouter(dependencies=[Depends(get_current_member)])

UPLOAD_DIR = Path("./uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)
_ALLOWED = {b"\xff\xd8\xff": ".jpg", b"\x89PNG": ".png"}
_MAX = int(settings.UPLOAD_MAX_BYTES)


def _safe_name(filename: str) -> str:
    name = Path(filename or "").name
    if not name or name in {".", ".."} or ".." in name.replace("\\", "/"):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return name


def _sniff(content: bytes) -> str:
    if len(content) < 8 or len(content) > _MAX:
        raise HTTPException(status_code=400, detail="Invalid image size")
    for magic, ext in _ALLOWED.items():
        if content.startswith(magic):
            return ext
    raise HTTPException(status_code=400, detail="Only JPEG and PNG image files are allowed")


async def _save_bytes(content: bytes) -> JSONResponse:
    ext = _sniff(content)
    new_filename = f"{uuid4()}{ext}"
    mime = "image/png" if ext == ".png" else "image/jpeg"
    store_image_bytes("uploaded_images", new_filename, content, content_type=mime)
    presigned = generate_presigned_url("uploaded_images", new_filename)
    return JSONResponse(
        status_code=200,
        content={
            "message": "File uploaded successfully",
            "filename": new_filename,
            "path": f"/images/{new_filename}",
            "presignedUrl": presigned,
        },
    )


@router.post("/upload-image")
@router.post("/upload-image/")
async def upload_image(file: UploadFile = File(...)):
    content = await file.read()
    return await _save_bytes(content)


@router.post("/upload-image-base64")
@router.post("/upload-image-base64/")
async def upload_image_base64(base64_image: str = Form(...)):
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
        raise HTTPException(status_code=400, detail="Invalid base64 string")
    return await _save_bytes(content)


def _resolve_local(filename: str) -> Path:
    safe = _safe_name(filename)
    path = (UPLOAD_DIR / safe).resolve()
    if UPLOAD_DIR.resolve() not in path.parents and path != UPLOAD_DIR.resolve():
        raise HTTPException(status_code=400, detail="Invalid filename")
    return path


@router.get("/get-image/{filename}")
async def get_image(filename: str):
    path = _resolve_local(filename)
    media = "image/png" if path.suffix == ".png" else "image/jpeg"
    if path.is_file():
        return FileResponse(path, media_type=media, filename=path.name)
    data = read_image_bytes("uploaded_images", path.name)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    return Response(content=data, media_type=media)


@router.get("/get-image-base64/{filename}")
async def get_image_base64(filename: str):
    path = _resolve_local(filename)
    data = read_image_bytes("uploaded_images", path.name)
    if data is None:
        raise HTTPException(status_code=404, detail="Image not found")
    encoded = base64.b64encode(data).decode("utf-8")
    mime = "image/png" if path.suffix == ".png" else "image/jpeg"
    return JSONResponse(
        content={"filename": path.name, "mime_type": mime, "data": f"data:{mime};base64,{encoded}"}
    )
