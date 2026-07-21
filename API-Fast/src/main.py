from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import logging
import os

from .config.database import engine, Base

# Register all ORM models on Base.metadata before create_all
from .models import (  # noqa: F401
    member,
    company,
    company_employee,
    company_location,
    department,
    position,
    employee_timestamp,
    face_encoding,
)
from .models.face_encoding import prepare_pgvector, ensure_face_embedding_index
from .routes import (
    member_routes,
    company_routes,
    department_routes,
    position_routes,
    employee_routes,
    employee_timestamp_routes,
    company_location_routes,
    auth_routes,
    face_routes,
    file_upload_router,
    system_routes,
    dashboard_routes,
)

logging.basicConfig(level=logging.DEBUG)
app = FastAPI(title="DPU Attendance API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:80",
        "http://127.0.0.1:80",
        "http://localhost:4200",
        "http://localhost:4201",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:4201",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await prepare_pgvector(conn)
        await conn.run_sync(Base.metadata.create_all)
        await ensure_face_embedding_index(conn)


UPLOAD_DIR = "./uploaded_images"
ENROLLED_DIR = "./enrolled_images"
TEMP_DIR = "./temp_images"

for directory in (UPLOAD_DIR, ENROLLED_DIR, TEMP_DIR):
    os.makedirs(directory, exist_ok=True)

app.mount("/images", StaticFiles(directory=UPLOAD_DIR), name="images")
app.mount("/enrolled_images", StaticFiles(directory=ENROLLED_DIR), name="enrolled_images")

app.include_router(auth_routes.router, prefix="/auth", tags=["Authentication"])
app.include_router(member_routes.router, prefix="/members", tags=["Members"])
app.include_router(company_routes.router, prefix="/companys", tags=["Companys"])
app.include_router(
    company_location_routes.router, prefix="/company-locations", tags=["Locations"]
)
app.include_router(department_routes.router, prefix="/departments", tags=["Departments"])
app.include_router(position_routes.router, prefix="/positions", tags=["Positions"])
app.include_router(employee_routes.router, prefix="/employees", tags=["Employees"])
app.include_router(
    employee_timestamp_routes.router, prefix="/timestamp", tags=["Timestamps"]
)
app.include_router(face_routes.router, prefix="/face", tags=["Face Recognition"])
app.include_router(file_upload_router.router, prefix="/api", tags=["File Upload"])
app.include_router(system_routes.router, prefix="/system")
app.include_router(dashboard_routes.router, prefix="/dashboard")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the API",
        "face": "InsightFace buffalo_l + pgvector",
    }
