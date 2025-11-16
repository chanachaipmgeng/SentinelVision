from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, UploadFile
from pathlib import Path
from uuid import UUID
import uuid
import shutil
import json
from typing import List

from ..models.member import Member
from ..models.face_encoding import FaceEncoding
from ..utils.face_recognition import generate_face_encoding, verify_liveness_and_get_encoding
from ..utils.face_index import search_face
from ..config.settings import settings


async def add_face(memberId: UUID, image_file: UploadFile, db: AsyncSession):
    """สร้าง Encoding, บันทึก record ใน DB, และเก็บไฟล์รูปภาพ"""
    member = await db.get(Member, memberId)
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / f"{uuid.uuid4()}.jpg"
    file_moved = False  # Flag to check if file has been moved

    try:
        # Save to temp path first
        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
        
        encoding = generate_face_encoding(str(temp_file_path))
        
        if encoding is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No face detected in the image.")

        # สร้าง object ใหม่สำหรับตาราง FaceEncoding
        new_face_encoding = FaceEncoding(
            memberId=member.memberId,
            encoding=json.dumps(encoding)
        )
        db.add(new_face_encoding)
        await db.commit()
        await db.refresh(new_face_encoding)

        # ย้ายไฟล์จาก temp ไปยัง permanent location
        permanent_dir = Path("enrolled_images")
        permanent_path = permanent_dir / f"{new_face_encoding.faceEncodingId}.jpg"
        shutil.move(str(temp_file_path), permanent_path)
        file_moved = True
        
        return {"message": "New face encoding added successfully", "faceEncodingId": str(new_face_encoding.faceEncodingId)}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        # ลบไฟล์ชั่วคราวถ้ายังไม่ได้ย้ายไฟล์
        if not file_moved and temp_file_path.exists():
            temp_file_path.unlink()


async def check_face_emp(image_files: List[UploadFile], db: AsyncSession):
    """ตรวจสอบ Liveness และค้นหาใบหน้าด้วย FAISS index"""
    if not image_files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No image files provided for liveness check")

    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    temp_image_paths = []
    
    try:
        for image_file in image_files:
            image_path = temp_dir / f"{uuid.uuid4()}.jpg"
            with image_path.open("wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            temp_image_paths.append(str(image_path))

        # 1. Verify liveness and get the encoding of the current face
        target_encoding = verify_liveness_and_get_encoding(temp_image_paths)

        # 2. Search for the best match in the FAISS index
        face_encoding_id, distance = search_face(
            target_encoding,
            threshold=settings.FACE_RECOGNITION_THRESHOLD
        )

        # 3. If a match is found, get the corresponding memberId
        if face_encoding_id:
            encoding_record = await db.get(FaceEncoding, face_encoding_id)
            if encoding_record:
                matched_member_id = encoding_record.memberId
                print(f"FAISS match corresponds to memberId: {matched_member_id}")
                return {"message": "Face match found!", "memberId": str(matched_member_id)}

        # 4. If no match, raise error
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Face does not match any record.")

    except (ValueError, RuntimeError) as ve:
        # Catches errors from liveness check and FAISS search (e.g., index not found)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        # Clean up all temporary images
        for path in temp_image_paths:
            if Path(path).exists():
                Path(path).unlink()

async def get_encodings_for_member(memberId: UUID, db: AsyncSession):
    """ดึงข้อมูล Encodings ทั้งหมดของพนักงานคนเดียว"""
    stmt = select(FaceEncoding).where(FaceEncoding.memberId == memberId)
    result = await db.execute(stmt)
    encodings = result.scalars().all()

    response = [
        {
            "faceEncodingId": str(enc.faceEncodingId),
            "memberId": str(enc.memberId),
            "createdAt": enc.createdAt,
            "imageUrl": f"/enrolled_images/{enc.faceEncodingId}.jpg"
        }
        for enc in encodings
    ]
    return response

async def delete_face_encoding(faceEncodingId: UUID, db: AsyncSession):
    """ลบ Face Encoding หนึ่งรายการ (และไฟล์รูปภาพ)"""
    encoding_record = await db.get(FaceEncoding, faceEncodingId)
    if not encoding_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face encoding not found")

    # Delete record from DB
    await db.delete(encoding_record)
    await db.commit()

    # Delete image file from filesystem
    try:
        image_path = Path(f"enrolled_images/{faceEncodingId}.jpg")
        if image_path.exists():
            image_path.unlink()
    except Exception as e:
        # Log this error, but don't fail the request if the DB record was deleted.
        print(f"Error deleting image file {image_path}: {e}")

    return {"message": "Face encoding deleted successfully"}
