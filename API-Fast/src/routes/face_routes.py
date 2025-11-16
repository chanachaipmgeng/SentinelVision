from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ..config.database import get_db
from ..controllers.face_controller import add_face, check_face , check_face_emp
from uuid import UUID

router = APIRouter()

# เส้นทาง API สำหรับเพิ่มใบหน้า
@router.post("/members/{memberId}/add-face")
async def add_face_route(memberId: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await add_face(memberId, file, db)

# เส้นทาง API สำหรับตรวจสอบใบหน้า
@router.post("/members/{memberId}/check-face")
async def check_face_route(memberId: UUID, file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await check_face(memberId, file, db)

# เส้นทาง API สำหรับตรวจสอบใบหน้า
@router.post("/members/check-face-emp")
async def check_face_emp_route(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    return await check_face_emp(file, db)