from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status, UploadFile
from pathlib import Path
from uuid import UUID
import uuid
import shutil
from typing import List, Optional

from ..models.member import Member
from ..models.face_encoding import FaceEncoding
from ..models.company_employee import CompanyEmployee
from ..utils.face_engine import (
    generate_face_encoding,
    verify_liveness_and_get_encoding,
    extract_face_features,
)
from ..config.settings import settings
from ..controllers.employee_timestamp_controller import create_timestamp

UPLOAD_DIR = Path("./uploaded_images")


async def add_face(memberId: UUID, image_file: UploadFile, db: AsyncSession):
    """Create InsightFace embedding, store in pgvector, save enrolled image."""
    member = await db.get(Member, memberId)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / f"{uuid.uuid4()}.jpg"
    file_moved = False

    try:
        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)

        encoding = generate_face_encoding(str(temp_file_path))
        if encoding is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in the image.",
            )

        new_face_encoding = FaceEncoding(
            memberId=member.memberId,
            embedding=encoding,
        )
        db.add(new_face_encoding)
        await db.commit()
        await db.refresh(new_face_encoding)

        permanent_dir = Path("enrolled_images")
        permanent_dir.mkdir(exist_ok=True)
        permanent_path = permanent_dir / f"{new_face_encoding.faceEncodingId}.jpg"
        shutil.move(str(temp_file_path), permanent_path)
        file_moved = True

        return {
            "message": "New face encoding added successfully",
            "faceEncodingId": str(new_face_encoding.faceEncodingId),
        }

    except HTTPException:
        await db.rollback()
        raise
    except ValueError as ve:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        if not file_moved and temp_file_path.exists():
            temp_file_path.unlink()


async def _search_face_pgvector(
    db: AsyncSession, target_encoding: List[float], threshold: float
):
    """Nearest neighbor by cosine distance; return (faceEncodingId, memberId, distance) or None."""
    distance_expr = FaceEncoding.embedding.cosine_distance(target_encoding)
    stmt = (
        select(
            FaceEncoding.faceEncodingId,
            FaceEncoding.memberId,
            distance_expr.label("distance"),
        )
        .order_by(distance_expr)
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    if row is None:
        return None

    face_encoding_id, member_id, distance = row
    if distance is None or float(distance) >= threshold:
        return None
    return face_encoding_id, member_id, float(distance)


def _match_quality(distance: float, threshold: float) -> str:
    if float(distance) < threshold * 0.5:
        return "high"
    if float(distance) < threshold * 0.75:
        return "medium"
    return "low"


def _member_payload(member: Member) -> dict:
    first_name = member.firstName or ""
    last_name = member.lastName or ""
    full_name = f"{first_name} {last_name}".strip() or member.username
    picture_url = None
    if member.picture:
        picture_url = (
            member.picture
            if str(member.picture).startswith(("http://", "https://", "/"))
            else f"/images/{member.picture}"
        )
    return {
        "memberId": str(member.memberId),
        "username": member.username,
        "email": member.email,
        "firstName": member.firstName,
        "lastName": member.lastName,
        "fullName": full_name,
        "phoneNumber": member.phoneNumber,
        "picture": member.picture,
        "pictureUrl": picture_url,
    }


def _score_payload(
    face_encoding_id,
    matched_member_id,
    distance: float,
    threshold: float,
    *,
    liveness_passed: bool,
) -> dict:
    similarity = max(0.0, min(1.0, 1.0 - float(distance)))
    confidence_percent = round(similarity * 100.0, 2)
    margin = (
        max(0.0, (threshold - float(distance)) / threshold) if threshold > 0 else 0.0
    )
    return {
        "memberId": str(matched_member_id),
        "faceEncodingId": str(face_encoding_id),
        "distance": round(float(distance), 6),
        "threshold": threshold,
        "confidence": round(similarity, 6),
        "confidencePercent": confidence_percent,
        "matchMargin": round(margin, 4),
        "matchQuality": _match_quality(float(distance), threshold),
        "livenessPassed": liveness_passed,
        "enrolledImageUrl": f"/enrolled_images/{face_encoding_id}.jpg",
    }


async def _resolve_match_response(
    db: AsyncSession,
    target_encoding: List[float],
    *,
    liveness_passed: bool,
) -> dict:
    threshold = float(settings.FACE_RECOGNITION_THRESHOLD)
    match = await _search_face_pgvector(db, target_encoding, threshold=threshold)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face does not match any record.",
        )

    face_encoding_id, matched_member_id, distance = match
    print(
        f"pgvector match faceEncodingId={face_encoding_id} "
        f"memberId={matched_member_id} distance={distance:.4f}"
    )

    member = await db.get(Member, matched_member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matched member not found",
        )

    payload = _score_payload(
        face_encoding_id,
        matched_member_id,
        distance,
        threshold,
        liveness_passed=liveness_passed,
    )
    payload.update(
        {
            "message": "Face match found!",
            "matched": True,
            "member": _member_payload(member),
        }
    )
    return payload


async def _save_temp_frames(image_files: List[UploadFile]) -> List[str]:
    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    paths: List[str] = []
    for image_file in image_files:
        image_path = temp_dir / f"{uuid.uuid4()}.jpg"
        with image_path.open("wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        paths.append(str(image_path))
    return paths


def _cleanup_paths(paths: List[str]) -> None:
    for path in paths:
        p = Path(path)
        if p.exists():
            p.unlink()


async def check_face_emp(image_files: List[UploadFile], db: AsyncSession):
    """Liveness check + 1:N match via pgvector cosine distance."""
    if not image_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided for liveness check",
        )

    temp_image_paths: List[str] = []
    try:
        temp_image_paths = await _save_temp_frames(image_files)
        target_encoding = verify_liveness_and_get_encoding(temp_image_paths)
        return await _resolve_match_response(
            db, target_encoding, liveness_passed=True
        )
    except HTTPException:
        raise
    except (ValueError, RuntimeError) as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        _cleanup_paths(temp_image_paths)


async def identify_face(image_file: UploadFile, db: AsyncSession):
    """Fast 1:N identify from a single frame (no liveness) for live overlay labels."""
    temp_image_paths: List[str] = []
    try:
        temp_image_paths = await _save_temp_frames([image_file])
        features = extract_face_features(temp_image_paths[0], require_quality=False)
        if features is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in the image.",
            )
        target_encoding, _bbox = features
        return await _resolve_match_response(
            db, target_encoding, liveness_passed=False
        )
    except HTTPException:
        raise
    except (ValueError, RuntimeError) as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        _cleanup_paths(temp_image_paths)


def _persist_photo_from_path(source_path: str) -> str:
    UPLOAD_DIR.mkdir(exist_ok=True)
    filename = f"{uuid.uuid4()}.jpg"
    dest = UPLOAD_DIR / filename
    shutil.copyfile(source_path, dest)
    return filename


def _employee_brief(company_employee: CompanyEmployee) -> dict:
    member = company_employee.member
    first_name = (member.firstName if member else "") or ""
    last_name = (member.lastName if member else "") or ""
    full_name = f"{first_name} {last_name}".strip() or (
        member.username if member else "-"
    )
    dept = company_employee.department
    pos = company_employee.position
    return {
        "company_employeeId": str(company_employee.company_employeeId),
        "employeeId": company_employee.employeeId,
        "fullName": full_name,
        "department": (dept.thName if dept else None) or (dept.engName if dept else None),
        "position": (pos.thName if pos else None) or (pos.engName if pos else None),
        "member": _member_payload(member) if member else None,
    }


async def check_in_face(
    image_files: List[UploadFile],
    companyId: UUID,
    latitude: float,
    longitude: float,
    db: AsyncSession,
    note: Optional[str] = None,
):
    """
    One-shot kiosk check-in: multi-frame liveness + match + save photo + timestamp.
    """
    if not image_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided for check-in",
        )

    temp_image_paths: List[str] = []
    try:
        temp_image_paths = await _save_temp_frames(image_files)
        target_encoding = verify_liveness_and_get_encoding(temp_image_paths)
        match_payload = await _resolve_match_response(
            db, target_encoding, liveness_passed=True
        )

        member_id = UUID(match_payload["memberId"])
        result = await db.execute(
            select(CompanyEmployee)
            .where(
                CompanyEmployee.memberId == member_id,
                CompanyEmployee.companyId == companyId,
            )
            .options(
                selectinload(CompanyEmployee.member),
                selectinload(CompanyEmployee.position),
                selectinload(CompanyEmployee.department),
            )
        )
        company_employee = result.scalar_one_or_none()
        if not company_employee:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Matched face is not an employee of this company.",
            )

        mid_path = temp_image_paths[len(temp_image_paths) // 2]
        photo_filename = _persist_photo_from_path(mid_path)

        check_in_note = (note or "").strip() or "Face kiosk auto check-in"
        timestamp = await create_timestamp(
            {
                "company_employeeId": company_employee.company_employeeId,
                "latitude": latitude,
                "longitude": longitude,
                "photoTimestamp": photo_filename,
                "note": check_in_note,
            },
            companyId,
            db,
        )

        ts_type = timestamp.get("timestampType")
        ts_type_value = getattr(ts_type, "value", ts_type)
        is_warning = int(ts_type_value) == 0

        return {
            **match_payload,
            "message": "Check-in saved"
            if not is_warning
            else "Check-in saved (outside area)",
            "checkedIn": True,
            "isWarning": is_warning,
            "employee": _employee_brief(company_employee),
            "timestamp": {
                "timestampId": str(timestamp["timestampId"]),
                "timestamp": timestamp["timestamp"],
                "timestampType": ts_type_value,
                "locationName": timestamp.get("locationName"),
                "latitude": timestamp.get("latitude"),
                "longitude": timestamp.get("longitude"),
                "photoTimestamp": timestamp.get("photoTimestamp"),
                "photoUrl": f"/images/{photo_filename}",
                "approvalStatus": timestamp.get("approvalStatus"),
                "note": timestamp.get("note"),
            },
        }

    except HTTPException:
        raise
    except (ValueError, RuntimeError) as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        _cleanup_paths(temp_image_paths)


async def get_encodings_for_member(memberId: UUID, db: AsyncSession):
    """List enrolled encodings for a member (metadata + image URL)."""
    stmt = select(FaceEncoding).where(FaceEncoding.memberId == memberId)
    result = await db.execute(stmt)
    encodings = result.scalars().all()

    return [
        {
            "faceEncodingId": str(enc.faceEncodingId),
            "memberId": str(enc.memberId),
            "createdAt": enc.createdAt,
            "imageUrl": f"/enrolled_images/{enc.faceEncodingId}.jpg",
        }
        for enc in encodings
    ]


async def delete_face_encoding(faceEncodingId: UUID, db: AsyncSession):
    """Delete one face encoding row and its enrolled image."""
    encoding_record = await db.get(FaceEncoding, faceEncodingId)
    if not encoding_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Face encoding not found"
        )

    await db.delete(encoding_record)
    await db.commit()

    try:
        image_path = Path(f"enrolled_images/{faceEncodingId}.jpg")
        if image_path.exists():
            image_path.unlink()
    except Exception as e:
        print(f"Error deleting image file {image_path}: {e}")

    return {"message": "Face encoding deleted successfully"}
