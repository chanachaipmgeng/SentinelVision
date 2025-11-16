from fastapi import FastAPI
from .config.database import engine
from .models.member import Base
import os
from fastapi.staticfiles import StaticFiles
import logging
from .routes import member_routes,company_routes,department_routes,position_routes,employee_routes,employee_timestamp_routes,company_location_routes,auth_routes,face_routes,file_upload_router
from fastapi.middleware.cors import CORSMiddleware
logging.basicConfig(level=logging.DEBUG)
app = FastAPI()
# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200","http://localhost:4201","https://61a8-49-228-101-141.ngrok-free.app"],  # Allow specific origin
    allow_credentials=True,  # Allow cookies and authorization headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)
# สร้างตารางทั้งหมดในฐานข้อมูลเมื่อแอปเริ่มทำงาน
@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
# โฟลเดอร์สำหรับเก็บไฟล์รูปภาพ
UPLOAD_DIR = "./uploaded_images"

# ตรวจสอบว่ามีโฟลเดอร์หรือไม่ ถ้าไม่มีให้สร้าง
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# เส้นทางสำหรับให้บริการไฟล์แบบ static (เช่น รูปภาพ)
app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")
# รวม routes
app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(member_routes.router, prefix="/members", tags=["Members"])
app.include_router(company_routes.router, prefix="/companys", tags=["Companys"])
app.include_router(company_location_routes.router, prefix="/company-locations", tags=["Locations"])
app.include_router(department_routes.router, prefix="/departments", tags=["Departments"])
app.include_router(position_routes.router, prefix="/positions", tags=["Positions"])
app.include_router(employee_routes.router, prefix="/employees", tags=["Employees"])
app.include_router(employee_timestamp_routes.router, prefix="/timestamp", tags=["Timestamps"])
app.include_router(face_routes.router, prefix="/face", tags=["Face Recognition"])
app.include_router(file_upload_router.router, prefix="/api", tags=["File Upload"])
@app.get("/")
async def root():
    logging.debug("This is a debug message")
    return {"message": "Welcome to the API"}