"""Optional cutover to shared ai-core-service (LLM gateway + face + vision)."""

from .client import AsyncAiCoreClient, get_ai_core_client, reset_ai_core_client
from .face_client import SyncAiCoreFaceClient, get_face_ai_core_client, reset_face_ai_core_client
from .flags import ai_core_enabled, ai_core_face_enabled, ai_core_vision_enabled
from .vision_client import (
    SyncAiCoreVisionClient,
    get_vision_ai_core_client,
    reset_vision_ai_core_client,
)

__all__ = [
    "AsyncAiCoreClient",
    "SyncAiCoreFaceClient",
    "SyncAiCoreVisionClient",
    "ai_core_enabled",
    "ai_core_face_enabled",
    "ai_core_vision_enabled",
    "get_ai_core_client",
    "get_face_ai_core_client",
    "get_vision_ai_core_client",
    "reset_ai_core_client",
    "reset_face_ai_core_client",
    "reset_vision_ai_core_client",
]
