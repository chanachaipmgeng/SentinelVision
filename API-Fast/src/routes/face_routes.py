from fastapi import APIRouter, Depends, Request, UploadFile, File, Form, WebSocket
from ..security.deps import (
    assert_encoding_company_access,
    assert_member_company_access,
    assert_request_company_access,
    current_member_var,
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from ..config.database import get_db
from ..controllers.face_controller import (
    add_face,
    detect_faces_upload,
    check_face_emp,
    identify_face,
    check_in_face,
    check_in_face_walkby,
    get_encodings_for_member,
    delete_face_encoding,
    clear_member_face_encodings,
    verify_member_face,
    get_kiosk_attendance,
    proxy_enrolled_image,
)
from ..controllers.face_ws_controller import kiosk_websocket, face_core_queue_stats_route
from ..middlewares.face_auth import face_route_auth
from uuid import UUID

router = APIRouter()
_face_auth = Depends(face_route_auth)


@router.websocket("/ws/kiosk")
async def face_kiosk_ws(websocket: WebSocket):
    """Realtime kiosk stream: session → identify/checkin via GPU queue."""
    await kiosk_websocket(websocket)


@router.get("/enrolled-images/{faceEncodingId}")
async def enrolled_image_proxy_route(
    request: Request,
    faceEncodingId: UUID,
    companyId: UUID,
    db: AsyncSession = Depends(get_db),
    _auth=Depends(face_route_auth),
):
    """Proxy Face Core gated images for Web-Manage / kiosk preview."""
    await assert_request_company_access(request, db, companyId)
    await assert_encoding_company_access(request, db, faceEncodingId)
    return await proxy_enrolled_image(faceEncodingId, companyId)


@router.get("/queue-stats")
async def face_queue_stats(companyId: Optional[UUID] = None, _auth=_face_auth):
    return await face_core_queue_stats_route(companyId)


@router.get("/kiosk-attendance/{companyId}")
async def kiosk_attendance_route(
    companyId: UUID, db: AsyncSession = Depends(get_db), _auth=_face_auth
):
    """Today's checked-in roster for the face kiosk panel."""
    return await get_kiosk_attendance(companyId, db)


@router.post("/members/{memberId}/add-face")
async def add_face_route(
    request: Request,
    memberId: UUID,
    file: UploadFile = File(...),
    companyId: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    """Enroll one face. Optional ``companyId`` names the tenant that owns the encoding
    (required to disambiguate members employed by several companies)."""
    await assert_member_company_access(request, db, memberId)
    if companyId is not None:
        await assert_request_company_access(request, db, companyId)
    actor = getattr(request.state, "member", None) or current_member_var.get()
    return await add_face(memberId, file, db, company_id=companyId, actor=actor)


@router.post("/detect")
async def detect_faces_route(
    file: UploadFile = File(...),
    _auth=_face_auth,
):
    """Detection-only preview for admin enroll camera (no embedding)."""
    return await detect_faces_upload(file)


@router.post("/members/check-face-emp")
async def check_face_emp_route(
    request: Request,
    files: List[UploadFile] = File(...),
    companyId: UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    """1:N match within company only (no timestamp)."""
    await assert_request_company_access(request, db, companyId)
    return await check_face_emp(files, companyId, db)


@router.post("/members/identify")
async def identify_face_route(
    request: Request,
    file: UploadFile = File(...),
    companyId: UUID = Form(...),
    preCropped: str = Form("false"),
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    """Single-frame identify within company for live name overlay (no timestamp).

    Set form field ``preCropped=true`` when the client already sent a tight face
    crop from an Edge camera / Mini PC (skips server-side face detection).
    """
    await assert_request_company_access(request, db, companyId)
    pre_cropped = str(preCropped or "").strip().lower() in ("1", "true", "yes", "on")
    return await identify_face(file, companyId, db, pre_cropped=pre_cropped)


@router.post("/members/check-in")
async def check_in_face_route(
    request: Request,
    files: List[UploadFile] = File(...),
    companyId: UUID = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    note: Optional[str] = Form(None),
    punchType: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    """Secure mode: multi-frame liveness + match + timestamp."""
    await assert_request_company_access(request, db, companyId)
    return await check_in_face(
        files, companyId, latitude, longitude, db, note=note, punch_type=punchType
    )


@router.post("/members/check-in-walkby")
async def check_in_face_walkby_route(
    request: Request,
    files: List[UploadFile] = File(...),
    companyId: UUID = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    note: Optional[str] = Form(None),
    punchType: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    """Walk-by mode: 1–2 frames, no motion liveness (multi-person pass-through)."""
    await assert_request_company_access(request, db, companyId)
    return await check_in_face_walkby(
        files, companyId, latitude, longitude, db, note=note, punch_type=punchType
    )


@router.get("/members/{memberId}/encodings", response_model=List[dict])
async def get_encodings_route(
    request: Request,
    memberId: UUID,
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    await assert_member_company_access(request, db, memberId)
    return await get_encodings_for_member(memberId, db)


@router.post("/members/{memberId}/verify")
async def verify_member_face_route(
    request: Request,
    memberId: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    """Test-scan vs this member only — returns confidence %, no timestamp."""
    await assert_member_company_access(request, db, memberId)
    return await verify_member_face(memberId, file, db)


@router.delete("/members/{memberId}/encodings")
async def clear_member_encodings_route(
    request: Request,
    memberId: UUID,
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    """Clear all enrolled faces for one member."""
    await assert_member_company_access(request, db, memberId)
    return await clear_member_face_encodings(memberId, db)


@router.delete("/encodings/{faceEncodingId}")
async def delete_encoding_route(
    request: Request,
    faceEncodingId: UUID,
    db: AsyncSession = Depends(get_db),
    _auth=_face_auth,
):
    await assert_encoding_company_access(request, db, faceEncodingId)
    return await delete_face_encoding(faceEncodingId, db)
