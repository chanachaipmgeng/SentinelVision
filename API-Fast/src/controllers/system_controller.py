from datetime import datetime
from typing import Any, Dict

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..models.system_setting import SystemSetting

TTS_SETTING_KEY = "tts"

DEFAULT_TTS_SETTINGS: Dict[str, Any] = {
    "enabled": True,
    "lang": "th-TH",
    "rate": 1.0,
    "pitch": 1.0,
    "templates": {
        "checkInSuccess": "ลงเวลาสำเร็จ คุณ{name}",
        "checkInWarning": "บันทึกนอกพื้นที่ คุณ{name}",
        "checkInDuplicate": "คุณ{name} ลงเวลาไปแล้ว",
        "enrollSuccess": "บันทึกใบหน้าสำเร็จ คุณ{name}",
        "enrollFailed": "บันทึกใบหน้าไม่สำเร็จ กรุณาลองใหม่",
    },
}


async def rebuild_face_index():
    """
    FAISS rebuild is no longer required — embeddings live in Postgres (pgvector)
    and are searchable immediately after enroll/delete.
    """
    return {
        "message": (
            "No rebuild needed. Face search uses pgvector cosine distance "
            "on face_encoding.embedding (InsightFace 512-d)."
        ),
        "index": "pgvector",
    }


def _merge_tts(raw: Any) -> Dict[str, Any]:
    src = raw if isinstance(raw, dict) else {}
    raw_templates = src.get("templates")
    templates_src = raw_templates if isinstance(raw_templates, dict) else {}
    templates = dict(DEFAULT_TTS_SETTINGS["templates"])
    for key, default_val in DEFAULT_TTS_SETTINGS["templates"].items():
        val = templates_src.get(key)
        if isinstance(val, str) and val.strip():
            templates[key] = val.strip()
        else:
            templates[key] = default_val

    try:
        rate = float(src.get("rate", 1.0))
    except (TypeError, ValueError):
        rate = 1.0
    try:
        pitch = float(src.get("pitch", 1.0))
    except (TypeError, ValueError):
        pitch = 1.0

    lang = src.get("lang")
    return {
        "enabled": src.get("enabled") is not False,
        "lang": lang.strip() if isinstance(lang, str) and lang.strip() else "th-TH",
        "rate": max(0.5, min(1.5, rate)),
        "pitch": max(0.0, min(2.0, pitch)),
        "templates": templates,
    }


async def get_tts_settings(db: AsyncSession) -> Dict[str, Any]:
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == TTS_SETTING_KEY)
    )
    row = result.scalar_one_or_none()
    if not row:
        return _merge_tts(DEFAULT_TTS_SETTINGS)
    return _merge_tts(row.value)


async def update_tts_settings(payload: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    if payload is None or not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="tts settings must be an object",
        )
    merged = _merge_tts(payload)
    result = await db.execute(
        select(SystemSetting).where(SystemSetting.key == TTS_SETTING_KEY)
    )
    row = result.scalar_one_or_none()
    now = datetime.utcnow()
    if row:
        row.value = merged
        row.updatedAt = now
    else:
        row = SystemSetting(key=TTS_SETTING_KEY, value=merged, updatedAt=now)
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return _merge_tts(row.value)
