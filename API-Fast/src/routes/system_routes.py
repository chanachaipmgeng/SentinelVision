from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.database import get_db
from ..controllers.system_controller import (
    get_tts_settings,
    rebuild_face_index,
    update_tts_settings,
)

router = APIRouter()


@router.post(
    "/rebuild-index",
    status_code=status.HTTP_200_OK,
    tags=["System"],
    summary="Face index status (pgvector — no rebuild required)",
)
async def rebuild_index_route():
    """
    Kept for backward compatibility with older admin tooling.
    InsightFace embeddings are stored in Postgres with pgvector; there is no
    separate FAISS file to rebuild.
    """
    return await rebuild_face_index()


@router.get(
    "/tts-settings",
    tags=["System"],
    summary="Global TTS speech templates (shared by all companies)",
)
async def get_tts_settings_route(db: AsyncSession = Depends(get_db)):
    return await get_tts_settings(db)


@router.put(
    "/tts-settings",
    tags=["System"],
    summary="Update global TTS speech templates",
)
async def put_tts_settings_route(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
):
    return await update_tts_settings(payload, db)
