from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# โหลด environment variables จากไฟล์ .env
load_dotenv()

# รับค่า DATABASE_URL จากไฟล์ .env
DATABASE_URL = os.getenv("DATABASE_URL")

# สร้าง engine สำหรับฐานข้อมูล
engine = create_async_engine(DATABASE_URL, echo=True)

# สร้าง session factory สำหรับการจัดการ session ของฐานข้อมูล
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base สำหรับใช้ในการสร้างโมเดล
Base = declarative_base()

# Dependency สำหรับใช้ใน FastAPI
async def get_db():
    async with async_session() as session:
        yield session
