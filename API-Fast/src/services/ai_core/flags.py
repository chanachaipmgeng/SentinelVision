"""Feature flags: AI core cutover requires URL + API key (both set)."""

from __future__ import annotations

from ...config.settings import settings


def ai_core_enabled() -> bool:
    """Phase 1 LLM gateway (`AI_CORE_URL`)."""
    return bool((settings.AI_CORE_URL or "").strip() and (settings.AI_CORE_API_KEY or "").strip())


def ai_core_face_enabled() -> bool:
    """Phase 2 face-inference (`AI_CORE_FACE_URL`) — independent of LLM URL."""
    return bool(
        (settings.AI_CORE_FACE_URL or "").strip() and (settings.AI_CORE_API_KEY or "").strip()
    )


def ai_core_vision_enabled() -> bool:
    """Phase 2B vision-inference (`AI_CORE_VISION_URL`) — independent of LLM / face URL."""
    return bool(
        (settings.AI_CORE_VISION_URL or "").strip() and (settings.AI_CORE_API_KEY or "").strip()
    )
