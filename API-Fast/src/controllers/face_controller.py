from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from pathlib import Path
from uuid import UUID
import uuid
import shutil
from ..models.member import Member
from ..utils.face_recognition import add_face_regonite, check_face_regonite,check_face_regonite_emp
from ..utils.file_handler import save_uploaded_file

# ฟังก์ชันสำหรับเพิ่มใบหน้า
async def add_face(memberId: UUID, image_file, db: AsyncSession):
    member = await db.get(Member, memberId)
    if not member:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        # บันทึกไฟล์ภาพและเก็บเส้นทางของไฟล์
        image_path = await save_uploaded_file(image_file)
        output = add_face_regonite(str(image_path), str(memberId))
        
        # เก็บข้อมูล faceEmbedding ในฐานข้อมูล
        member.faceEmbedding = output
        await db.commit()
        await db.refresh(member)
        
        return {"message": "Face added successfully", "member": str(member.memberId)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ฟังก์ชันสำหรับตรวจสอบใบหน้า
async def check_face(memberId: UUID, image_file, db: AsyncSession):
    member = await db.get(Member, memberId)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if not member.faceEmbedding:
        raise HTTPException(status_code=400, detail="No enrolled face found")

    # บันทึกไฟล์ภาพชั่วคราว
    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    image_path = temp_dir / f"{uuid.uuid4()}.jpg"
    with image_path.open("wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)

    try:
        output = check_face_regonite(str(image_path), str(memberId))
        if "Face match found!" in output:
            return {"message": output}
        else:
            raise HTTPException(status_code=401, detail="Face does not match")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        image_path.unlink()  # ลบไฟล์ชั่วคราว
        
async def check_face_emp(image_file, db: AsyncSession):
    # บันทึกไฟล์ภาพชั่วคราว
    temp_dir = Path("temp_images")
    temp_dir.mkdir(exist_ok=True)
    image_path = temp_dir / f"{uuid.uuid4()}.jpg"
    with image_path.open("wb") as buffer:
        shutil.copyfileobj(image_file.file, buffer)

    try:
        output = check_face_regonite_emp(str(image_path))
        if output:
            return {"message": output}
        else:
            raise HTTPException(status_code=401, detail="Face does not match")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        image_path.unlink()  # ลบไฟล์ชั่วคราว
