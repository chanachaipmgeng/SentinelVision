from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, UploadFile
from pathlib import Path
from uuid import UUID
import uuid
import shutil
from typing import List

from ..models.member import Member
from ..models.face_encoding import FaceEncoding
from ..utils.face_engine import generate_face_encoding, verify_liveness_and_get_encoding
from ..config.settings import settings


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


async def check_face_emp(image_files: List[UploadFile], db: AsyncSession):
    """Liveness check + 1:N match via pgvector cosine distance."""
    if not image_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No image files provided for liveness check",
        )

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_image_paths = []

    try:
        for image_file in image_files:
            image_path = temp_dir / f"{uuid.uuid4()}.jpg"
            with image_path.open("wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            temp_image_paths.append(str(image_path))

        target_encoding = verify_liveness_and_get_encoding(temp_image_paths)

        match = await _search_face_pgvector(
            db,
            target_encoding,
            threshold=settings.FACE_RECOGNITION_THRESHOLD,
        )

        if match:
            face_encoding_id, matched_member_id, distance = match
            print(
                f"pgvector match faceEncodingId={face_encoding_id} "
                f"memberId={matched_member_id} distance={distance:.4f}"
            )
            return {
                "message": "Face match found!",
                "memberId": str(matched_member_id),
            }

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Face does not match any record.",
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
        for path in temp_image_paths:
            p = Path(path)
            if p.exists():
                p.unlink()


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
