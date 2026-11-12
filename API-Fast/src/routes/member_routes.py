from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from ..config.database import get_db
from ..clients.face_core_client import face_core_enabled
from ..controllers.face_controller import clear_member_face_encodings
from ..controllers.member_controller import (
    get_users,
    get_user_by_id,
    create_user,
    update_user,
    delete_user,
)
from ..middlewares.auth_middleware import authenticate_jwt  # Middleware for token authentication
from ..models.face_encoding import FaceEncoding
from ..models.member import Member
from ..schemas.member_schema import MemberCreate, MemberResponse, MemberUpdate
from ..services import pdpa_service
from ..services.rbac_service import is_system_admin_member
from ..services.storage_service import delete_stored_image

router = APIRouter()

SYSTEM_CONSENT_POLICY_KEY = pdpa_service.SYSTEM_CONSENT_POLICY_KEY


async def _load_system_admin_member(db: AsyncSession, member_id: UUID) -> Member:
    member = await db.get(Member, member_id)
    if not member or getattr(member, "deletedAt", None) is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if not is_system_admin_member(member):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system admin members support this consent endpoint",
        )
    return member


async def _clear_local_face_encodings(db: AsyncSession, member_id: UUID) -> int:
    enc_result = await db.execute(
        select(FaceEncoding).where(FaceEncoding.memberId == member_id)
    )
    encodings = list(enc_result.scalars().all())
    removed_ids: list[str] = []
    for enc in encodings:
        removed_ids.append(str(enc.faceEncodingId))
        await db.delete(enc)
    for enc_id in removed_ids:
        try:
            delete_stored_image("enrolled_images", f"{enc_id}.jpg")
        except Exception:
            pass
    return len(removed_ids)


async def _system_gallery_encoding_counts(
    db: AsyncSession, member_ids: list[UUID]
) -> dict[UUID, int]:
    """Count local system-gallery encodings (companyId IS NULL) per member."""
    if not member_ids:
        return {}
    result = await db.execute(
        select(FaceEncoding.memberId, func.count())
        .where(
            FaceEncoding.memberId.in_(member_ids),
            FaceEncoding.companyId.is_(None),
        )
        .group_by(FaceEncoding.memberId)
    )
    return {row[0]: int(row[1]) for row in result.all()}


def _member_response(member: Member, face_count: int = 0) -> MemberResponse:
    return MemberResponse.model_validate(member).model_copy(
        update={"faceEncodingCount": face_count}
    )


@router.get("", response_model=List[MemberResponse])
async def get_members(
    includeDeleted: bool = False,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    members = await get_users(db, include_deleted=includeDeleted)
    counts = await _system_gallery_encoding_counts(
        db, [m.memberId for m in members]
    )
    return [_member_response(m, counts.get(m.memberId, 0)) for m in members]


@router.get("/pdpa/consent-policy")
async def get_system_consent_policy(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt),
):
    """PDPA consent text for system-admin console face login (gallery key ``system``)."""
    return await pdpa_service.ensure_consent_policy(db, SYSTEM_CONSENT_POLICY_KEY)


@router.get("/{memberId}", response_model=MemberResponse)
async def get_member(
    memberId: str,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    member = await get_user_by_id(UUID(memberId), db)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    counts = await _system_gallery_encoding_counts(db, [member.memberId])
    return _member_response(member, counts.get(member.memberId, 0))

@router.post("", response_model=MemberResponse)
async def create_new_member(
    member: MemberCreate,
    db: AsyncSession = Depends(get_db),
):
    created = await create_user(member, db)
    return _member_response(created, 0)

@router.put("/{memberId}", response_model=MemberResponse)
async def update_existing_member(
    memberId: str, 
    member_update: MemberUpdate, 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    updated = await update_user(UUID(memberId), member_update, db)
    counts = await _system_gallery_encoding_counts(db, [updated.memberId])
    return _member_response(updated, counts.get(updated.memberId, 0))

@router.delete("/{memberId}")
async def delete_existing_member(
    memberId: str, 
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(authenticate_jwt)  # Validate JWT token
):
    return await delete_user(UUID(memberId), db)


@router.post("/{memberId}/biometric-consent")
async def grant_system_admin_biometric_consent(
    memberId: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """PDPA biometric consent for system admins (no company scope)."""
    member = await _load_system_admin_member(db, memberId)
    body = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    locale = str((body or {}).get("locale") or "th")
    return await pdpa_service.record_biometric_consent(
        db, member, SYSTEM_CONSENT_POLICY_KEY, locale=locale
    )


@router.delete("/{memberId}/biometric-consent")
async def revoke_system_admin_biometric_consent(
    memberId: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Revoke console face-login consent and wipe local (and Face Core) encodings."""
    member = await _load_system_admin_member(db, memberId)

    deleted = 0
    if face_core_enabled():
        try:
            cleared = await clear_member_face_encodings(memberId, db)
            if isinstance(cleared, dict):
                deleted = int(cleared.get("deleted", 0) or 0)
        except HTTPException:
            raise
        except Exception:
            deleted = 0

    # Face-login gallery is always local for role 99 — ensure those rows are gone.
    deleted += await _clear_local_face_encodings(db, memberId)

    member.biometricConsentAt = None
    member.biometricConsentVersion = None
    member.biometricConsentText = None
    await db.commit()
    return {
        "memberId": str(memberId),
        "biometricConsentAt": None,
        "hasConsent": False,
        "deletedEncodings": deleted,
        "consentCleared": True,
    }
