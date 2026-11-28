"""Optional cutover to shared ai-core-service (Phase 1 LLM gateway)."""

from .client import AsyncAiCoreClient, get_ai_core_client, reset_ai_core_client
from .flags import ai_core_enabled

__all__ = [
    "AsyncAiCoreClient",
    "ai_core_enabled",
    "get_ai_core_client",
    "reset_ai_core_client",
]
