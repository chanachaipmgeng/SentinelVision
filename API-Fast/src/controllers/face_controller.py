from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status, UploadFile
from pathlib import Path
from uuid import UUID
from datetime import datetime, timedelta, timezone
import uuid
import shutil
from typing import List, Optional

from ..models.member import Member, StatusType as MemberStatus
from ..models.face_encoding import FaceEncoding
from ..models.company_employee import CompanyEmployee
from ..models.employee_timestamp import EmployeeTimestamp, TimestampType
from ..utils.face_engine import (
    generate_face_encoding,
    verify_liveness_and_get_encoding,
    get_walkby_encoding,
    extract_face_features,
)
from ..utils.face_gpu_queue import run_on_face_gpu
from ..config.settings import settings
from ..controllers.employee_timestamp_controller import create_timestamp
from ..clients.face_core_client import face_core_enabled, get_face_core_client

UPLOAD_DIR = Path("./uploaded_images")


def _company_code(company_id: UUID) -> str:
    return str(company_id)


async def _member_company_ids(db: AsyncSession, member_id: UUID) -> List[UUID]:
    result = await db.execute(
        select(CompanyEmployee.companyId).where(CompanyEmployee.memberId == member_id)
    )
    return [row[0] for row in result.all()]


async def _face_core_identify(
    company_id: UUID,
    file_paths: List[str],
    mode: str,
) -> dict:
    client = get_face_core_client()
    code = _company_code(company_id)
    await client.ensure_company(code)
    try:
        return await client.identify(code, file_paths, mode=mode)  # type: ignore[arg-type]
    except HTTPException as he:
        if he.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Face does not match any employee in this company.",
            ) from he
        raise


async def _enrich_face_core_match(
    db: AsyncSession,
    company_id: UUID,
    fc: dict,
    *,
    message: str = "Face match found!",
) -> dict:
    if not fc.get("matched"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face does not match any employee in this company.",
        )

    subject_id = fc.get("subjectId")
    if not subject_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face does not match any employee in this company.",
        )

    member_id = UUID(str(subject_id))
    member = await db.get(Member, member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Matched member not found",
        )

    emp_row = await db.execute(
        select(CompanyEmployee.company_employeeId)
        .where(
            CompanyEmployee.memberId == member_id,
            CompanyEmployee.companyId == company_id,
        )
        .limit(1)
    )
    if emp_row.first() is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face does not match any employee in this company.",
        )

    face_id = fc.get("faceId")
    return {
        "memberId": str(member_id),
        "faceEncodingId": str(face_id) if face_id else None,
        "distance": fc.get("distance"),
        "threshold": fc.get("threshold", settings.FACE_RECOGNITION_THRESHOLD),
        "confidence": fc.get("confidence"),
        "confidencePercent": fc.get("confidencePercent"),
        "matchMargin": fc.get("matchMargin"),
        "matchQuality": fc.get("matchQuality"),
        "livenessPassed": fc.get("livenessPassed", False),
        "enrolledImageUrl": fc.get("enrolledImageUrl")
        or (f"/enrolled_images/{face_id}.jpg" if face_id else None),
        "message": message,
        "matched": True,
        "member": _member_payload(member),
    }


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

        if face_core_enabled():
            company_ids = await _member_company_ids(db, memberId)
            if not company_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Member is not linked to any company; cannot enroll face.",
                )
            client = get_face_core_client()
            subject_id = str(memberId)
            first_face_id: Optional[str] = None
            for company_id in company_ids:
                code = _company_code(company_id)
                await client.ensure_company(code)
                enrolled = await client.enroll(code, subject_id, temp_file_path)
                if first_face_id is None:
                    first_face_id = enrolled.get("faceId")
            return {
                "message": "New face encoding added successfully",
                "faceEncodingId": first_face_id,
            }

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
    db: AsyncSession,
    target_encoding: List[float],
    threshold: float,
    *,
    companyId: Optional[UUID] = None,
):
    """
    Nearest neighbor by cosine distance within optional company scope.
    When companyId is set, only encodings of that company's employees are searched.
    """
    distance_expr = FaceEncoding.embedding.cosine_distance(target_encoding)
    stmt = select(
        FaceEncoding.faceEncodingId,
        FaceEncoding.memberId,
        distance_expr.label("distance"),
    )
    if companyId is not None:
        company_member_ids = select(CompanyEmployee.memberId).where(
            CompanyEmployee.companyId == companyId
        )
        stmt = stmt.where(FaceEncoding.memberId.in_(company_member_ids))
    stmt = stmt.order_by(distance_expr).limit(1)
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
    companyId: Optional[UUID] = None,
) -> dict:
    threshold = float(settings.FACE_RECOGNITION_THRESHOLD)
    match = await _search_face_pgvector(
        db, target_encoding, threshold=threshold, companyId=companyId
    )
    if not match:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Face does not match any employee in this company."
                if companyId is not None
                else "Face does not match any record."
            ),
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


async def check_face_emp(
    image_files: List[UploadFile], companyId: UUID, db: AsyncSession
):
    """Liveness check + 1:N match within company via pgvector cosine distance."""
    if not image_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided for liveness check",
        )

    temp_image_paths: List[str] = []
    try:
        temp_image_paths = await _save_temp_frames(image_files)
        if face_core_enabled():
            fc = await _face_core_identify(companyId, temp_image_paths, "secure")
            return await _enrich_face_core_match(db, companyId, fc)
        target_encoding = verify_liveness_and_get_encoding(temp_image_paths)
        return await _resolve_match_response(
            db,
            target_encoding,
            liveness_passed=True,
            companyId=companyId,
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


async def identify_face(
    image_file: UploadFile, companyId: UUID, db: AsyncSession
):
    """Fast 1:N identify within company from a single frame (no liveness)."""
    temp_image_paths: List[str] = []
    try:
        temp_image_paths = await _save_temp_frames([image_file])
        if face_core_enabled():
            fc = await _face_core_identify(companyId, temp_image_paths, "fast")
            return await _enrich_face_core_match(db, companyId, fc)
        features = await run_on_face_gpu(
            lambda p=temp_image_paths[0]: extract_face_features(p, require_quality=False)
        )
        if features is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No face detected in the image.",
            )
        target_encoding, _bbox = features
        return await _resolve_match_response(
            db,
            target_encoding,
            liveness_passed=False,
            companyId=companyId,
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


async def _finalize_check_in(
    *,
    db: AsyncSession,
    companyId: UUID,
    latitude: float,
    longitude: float,
    note: Optional[str],
    photo_source_path: str,
    liveness_passed: bool,
    mode: str,
    default_note: str,
    target_encoding: Optional[List[float]] = None,
    match_payload: Optional[dict] = None,
) -> dict:
    if match_payload is None:
        if target_encoding is None:
            raise ValueError("target_encoding or match_payload is required")
        match_payload = await _resolve_match_response(
            db,
            target_encoding,
            liveness_passed=liveness_passed,
            companyId=companyId,
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

    dedupe_seconds = int(getattr(settings, "CHECK_IN_DEDUPE_SECONDS", 300) or 0)
    if dedupe_seconds > 0:
        since = datetime.now(timezone.utc) - timedelta(seconds=dedupe_seconds)
        recent = await db.execute(
            select(EmployeeTimestamp)
            .where(
                EmployeeTimestamp.company_employeeId
                == company_employee.company_employeeId,
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.timestamp >= since,
            )
            .order_by(EmployeeTimestamp.timestamp.desc())
            .limit(1)
        )
        existing_ts = recent.scalar_one_or_none()
        if existing_ts:
            ts_type = existing_ts.timestampType
            ts_type_value = getattr(ts_type, "value", ts_type)
            photo = existing_ts.photoTimestamp
            return {
                **match_payload,
                "message": "Already checked in recently",
                "checkedIn": False,
                "duplicate": True,
                "mode": mode,
                "dedupeSeconds": dedupe_seconds,
                "isWarning": int(ts_type_value) == 0,
                "employee": _employee_brief(company_employee),
                "timestamp": {
                    "timestampId": str(existing_ts.timestampId),
                    "timestamp": existing_ts.timestamp,
                    "timestampType": ts_type_value,
                    "locationName": existing_ts.locationName,
                    "latitude": existing_ts.latitude,
                    "longitude": existing_ts.longitude,
                    "photoTimestamp": photo,
                    "photoUrl": f"/images/{photo}" if photo else None,
                    "approvalStatus": existing_ts.approvalStatus,
                    "note": existing_ts.note,
                },
            }

    try:
        lat_f = float(latitude)
        lon_f = float(longitude)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and Longitude are required for check-in.",
        )
    if abs(lat_f) < 1e-6 and abs(lon_f) < 1e-6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid GPS coordinates (0,0). Enable location / open via HTTPS before check-in.",
        )

    photo_filename = _persist_photo_from_path(photo_source_path)
    check_in_note = (note or "").strip() or default_note
    timestamp = await create_timestamp(
        {
            "company_employeeId": company_employee.company_employeeId,
            "latitude": lat_f,
            "longitude": lon_f,
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
        "duplicate": False,
        "mode": mode,
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
        mid_path = temp_image_paths[len(temp_image_paths) // 2]
        if face_core_enabled():
            fc = await _face_core_identify(companyId, temp_image_paths, "secure")
            match_payload = await _enrich_face_core_match(db, companyId, fc)
            return await _finalize_check_in(
                db=db,
                companyId=companyId,
                latitude=latitude,
                longitude=longitude,
                note=note,
                match_payload=match_payload,
                photo_source_path=mid_path,
                liveness_passed=True,
                mode="secure",
                default_note="Face kiosk auto check-in",
            )
        target_encoding = await run_on_face_gpu(
            lambda ps=list(temp_image_paths): verify_liveness_and_get_encoding(ps)
        )
        return await _finalize_check_in(
            db=db,
            companyId=companyId,
            latitude=latitude,
            longitude=longitude,
            note=note,
            target_encoding=target_encoding,
            photo_source_path=mid_path,
            liveness_passed=True,
            mode="secure",
            default_note="Face kiosk auto check-in",
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


async def check_in_face_walkby(
    image_files: List[UploadFile],
    companyId: UUID,
    latitude: float,
    longitude: float,
    db: AsyncSession,
    note: Optional[str] = None,
):
    """
    Walk-by check-in: 1–2 face crops, no motion liveness (faster multi-person pass).
    """
    if not image_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided for walk-by check-in",
        )
    if len(image_files) > 3:
        image_files = image_files[:3]

    temp_image_paths: List[str] = []
    try:
        temp_image_paths = await _save_temp_frames(image_files)
        mid_path = temp_image_paths[len(temp_image_paths) // 2]
        if face_core_enabled():
            fc = await _face_core_identify(companyId, temp_image_paths, "walkby")
            match_payload = await _enrich_face_core_match(db, companyId, fc)
            return await _finalize_check_in(
                db=db,
                companyId=companyId,
                latitude=latitude,
                longitude=longitude,
                note=note,
                match_payload=match_payload,
                photo_source_path=mid_path,
                liveness_passed=False,
                mode="walkby",
                default_note="Face kiosk walk-by check-in",
            )
        target_encoding = await run_on_face_gpu(
            lambda ps=list(temp_image_paths): get_walkby_encoding(ps)
        )
        return await _finalize_check_in(
            db=db,
            companyId=companyId,
            latitude=latitude,
            longitude=longitude,
            note=note,
            target_encoding=target_encoding,
            photo_source_path=mid_path,
            liveness_passed=False,
            mode="walkby",
            default_note="Face kiosk walk-by check-in",
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


async def get_encodings_for_member(memberId: UUID, db: AsyncSession):
    """List enrolled encodings for a member (metadata + image URL)."""
    if face_core_enabled():
        company_ids = await _member_company_ids(db, memberId)
        if not company_ids:
            return []
        client = get_face_core_client()
        subject_id = str(memberId)
        seen: set = set()
        rows: List[dict] = []
        for company_id in company_ids:
            code = _company_code(company_id)
            faces = await client.list_faces(code, subject_id)
            for face in faces:
                face_id = face.get("faceId")
                if not face_id or face_id in seen:
                    continue
                seen.add(face_id)
                rows.append(
                    {
                        "faceEncodingId": face_id,
                        "memberId": str(memberId),
                        "createdAt": face.get("createdAt"),
                        "imageUrl": face.get("imageUrl")
                        or f"/enrolled_images/{face_id}.jpg",
                    }
                )
        return rows

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
    if face_core_enabled():
        client = get_face_core_client()
        await client.delete_face(str(faceEncodingId))
        return {"message": "Face encoding deleted successfully"}

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


async def clear_member_face_encodings(memberId: UUID, db: AsyncSession):
    """Delete all enrolled face encodings for one member (no check-in side effects)."""
    member = await db.get(Member, memberId)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if face_core_enabled():
        company_ids = await _member_company_ids(db, memberId)
        client = get_face_core_client()
        subject_id = str(memberId)
        deleted_ids: List[str] = []
        for company_id in company_ids:
            code = _company_code(company_id)
            result = await client.clear_subject_faces(code, subject_id)
            deleted_ids.extend(result.get("faceIds") or [])
        return {
            "message": "All face encodings cleared",
            "deleted": len(deleted_ids),
            "faceEncodingIds": deleted_ids,
        }

    result = await db.execute(
        select(FaceEncoding).where(FaceEncoding.memberId == memberId)
    )
    encodings = list(result.scalars().all())
    deleted_ids: List[str] = []
    for enc in encodings:
        deleted_ids.append(str(enc.faceEncodingId))
        await db.delete(enc)
    await db.commit()

    for enc_id in deleted_ids:
        try:
            image_path = Path(f"enrolled_images/{enc_id}.jpg")
            if image_path.exists():
                image_path.unlink()
        except Exception as e:
            print(f"Error deleting image file enrolled_images/{enc_id}.jpg: {e}")

    return {
        "message": "All face encodings cleared",
        "deleted": len(deleted_ids),
        "faceEncodingIds": deleted_ids,
    }


async def verify_member_face(memberId: UUID, image_file: UploadFile, db: AsyncSession):
    """
    Test-scan against this member's enrolled faces only.
    Returns confidence percent without creating a timestamp / check-in.
    """
    member = await db.get(Member, memberId)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    count_result = await db.execute(
        select(FaceEncoding.faceEncodingId).where(FaceEncoding.memberId == memberId).limit(1)
    )
    if count_result.first() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="พนักงานคนนี้ยังไม่มีใบหน้าที่ลงทะเบียน",
        )

    temp_image_paths: List[str] = []
    try:
        temp_image_paths = await _save_temp_frames([image_file])
        if face_core_enabled():
            company_ids = await _member_company_ids(db, memberId)
            if not company_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="พนักงานคนนี้ยังไม่มีใบหน้าที่ลงทะเบียน",
                )
            client = get_face_core_client()
            subject_id = str(memberId)
            code = _company_code(company_ids[0])
            await client.ensure_company(code)
            enrolled = await client.list_faces(code, subject_id)
            if not enrolled:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="พนักงานคนนี้ยังไม่มีใบหน้าที่ลงทะเบียน",
                )
            fc = await client.verify(code, subject_id, temp_image_paths[0])
            matched = bool(fc.get("matched"))
            face_id = fc.get("faceId")
            score = {
                "memberId": str(memberId),
                "faceEncodingId": str(face_id) if face_id else None,
                "distance": fc.get("distance"),
                "threshold": fc.get("threshold", settings.FACE_RECOGNITION_THRESHOLD),
                "confidence": fc.get("confidence"),
                "confidencePercent": fc.get("confidencePercent"),
                "matchMargin": fc.get("matchMargin"),
                "matchQuality": fc.get("matchQuality"),
                "livenessPassed": fc.get("livenessPassed", False),
                "enrolledImageUrl": fc.get("enrolledImageUrl")
                or (f"/enrolled_images/{face_id}.jpg" if face_id else None),
                "message": "Face verify completed (no check-in)",
                "matched": matched,
                "isTestOnly": True,
                "member": _member_payload(member),
            }
            return score

        features = await run_on_face_gpu(
            lambda p=temp_image_paths[0]: extract_face_features(p, require_quality=False)
        )
        if features is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ไม่พบใบหน้าในรูป",
            )
        target_encoding, _bbox = features

        threshold = float(settings.FACE_RECOGNITION_THRESHOLD)
        distance_expr = FaceEncoding.embedding.cosine_distance(target_encoding)
        stmt = (
            select(
                FaceEncoding.faceEncodingId,
                distance_expr.label("distance"),
            )
            .where(FaceEncoding.memberId == memberId)
            .order_by(distance_expr)
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="พนักงานคนนี้ยังไม่มีใบหน้าที่ลงทะเบียน",
            )

        face_encoding_id, distance = row
        distance_f = float(distance)
        matched = distance_f < threshold
        score = _score_payload(
            face_encoding_id,
            memberId,
            distance_f,
            threshold,
            liveness_passed=False,
        )
        score.update(
            {
                "message": "Face verify completed (no check-in)",
                "matched": matched,
                "isTestOnly": True,
                "member": _member_payload(member),
            }
        )
        return score
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


def _member_status_value(status) -> int:
    if status is None:
        return 0
    if hasattr(status, "value"):
        try:
            return int(status.value)
        except (TypeError, ValueError):
            return 0
    try:
        return int(status)
    except (TypeError, ValueError):
        return 0


def _ts_type_int(ts_type) -> int:
    if ts_type is None:
        return -1
    if isinstance(ts_type, TimestampType):
        return int(ts_type.value)
    try:
        return int(ts_type)
    except (TypeError, ValueError):
        return -1


async def get_kiosk_attendance(companyId: UUID, db: AsyncSession):
    """Today's checked-in roster only — no full-company / not-yet scan."""
    try:
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo("Asia/Bangkok")
        except Exception:
            tz = timezone(timedelta(hours=7))

        now_local = datetime.now(tz)
        today_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today_start + timedelta(days=1)

        ts_result = await db.execute(
            select(EmployeeTimestamp)
            .where(
                EmployeeTimestamp.companyId == companyId,
                EmployeeTimestamp.timestamp >= today_start,
                EmployeeTimestamp.timestamp < tomorrow,
            )
            .order_by(EmployeeTimestamp.timestamp.desc())
        )
        timestamps = ts_result.scalars().all()

        latest_by_emp: dict = {}
        for ts in timestamps:
            emp_id = ts.company_employeeId
            if emp_id not in latest_by_emp:
                latest_by_emp[emp_id] = ts

        emp_ids = list(latest_by_emp.keys())
        employees_by_id: dict = {}
        if emp_ids:
            emp_result = await db.execute(
                select(CompanyEmployee)
                .where(CompanyEmployee.company_employeeId.in_(emp_ids))
                .options(
                    selectinload(CompanyEmployee.member),
                    selectinload(CompanyEmployee.position),
                    selectinload(CompanyEmployee.department),
                )
            )
            employees_by_id = {
                emp.company_employeeId: emp for emp in emp_result.scalars().all()
            }

        checked_in = []
        for emp_id, ts in latest_by_emp.items():
            emp = employees_by_id.get(emp_id)
            member = emp.member if emp else None
            name = (
                f"{getattr(member, 'firstName', '') or ''} {getattr(member, 'lastName', '') or ''}".strip()
                if member
                else "ไม่ทราบชื่อ"
            ) or "ไม่ทราบชื่อ"
            ttype = _ts_type_int(ts.timestampType)
            checked_in.append(
                {
                    "company_employeeId": str(emp_id),
                    "employeeId": (emp.employeeId if emp else "") or "",
                    "employeeName": name,
                    "picture": getattr(member, "picture", None) if member else None,
                    "department": emp.department.thName if emp and emp.department else "",
                    "position": emp.position.thName if emp and emp.position else "",
                    "timestamp": ts.timestamp,
                    "timestampType": ttype,
                    "locationName": ts.locationName or "",
                    "photoTimestamp": ts.photoTimestamp,
                    "approvalStatus": ts.approvalStatus,
                }
            )

        checked_in.sort(
            key=lambda x: x.get("timestamp") or datetime.min.replace(tzinfo=tz),
            reverse=True,
        )

        in_area_count = sum(1 for row in checked_in if row.get("timestampType") == 1)
        outside_count = sum(1 for row in checked_in if row.get("timestampType") == 0)
        return {
            "summary": {
                "checkedInCount": len(checked_in),
                "inAreaCount": in_area_count,
                "outsideCount": outside_count,
                "asOf": now_local.isoformat(),
                "day": today_start.date().isoformat(),
            },
            "checkedIn": checked_in,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load kiosk attendance: {str(e)}",
        )
