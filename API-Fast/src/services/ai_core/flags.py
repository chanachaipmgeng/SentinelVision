"""Feature flag: AI core cutover is on only when URL and API key are both set."""

from __future__ import annotations

from ...config.settings import settings


def ai_core_enabled() -> bool:
    return bool((settings.AI_CORE_URL or "").strip() and (settings.AI_CORE_API_KEY or "").strip())
