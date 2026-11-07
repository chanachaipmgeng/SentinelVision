from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

_db_schema = (os.getenv("DB_SCHEMA") or "public").strip() or "public"
DB_SCHEMA = _db_schema

_metadata = MetaData(schema=DB_SCHEMA if DB_SCHEMA != "public" else None)

_connect_args = {}
if DB_SCHEMA != "public":
    _connect_args["server_settings"] = {"search_path": f"{DB_SCHEMA}, public"}

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
    max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
    pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
    connect_args=_connect_args,
)

async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base(metadata=_metadata)


async def get_db():
    async with async_session() as session:
        yield session
