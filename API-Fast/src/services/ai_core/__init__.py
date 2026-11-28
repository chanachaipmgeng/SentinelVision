"""Optional cutover to shared ai-core-service (LLM gateway + face-inference)."""

from .client import AsyncAiCoreClient, get_ai_core_client, reset_ai_core_client
from .face_client import SyncAiCoreFaceClient, get_face_ai_core_client, reset_face_ai_core_client
from .flags import ai_core_enabled, ai_core_face_enabled

__all__ = [
    "AsyncAiCoreClient",
    "SyncAiCoreFaceClient",
    "ai_core_enabled",
    "ai_core_face_enabled",
    "get_ai_core_client",
    "get_face_ai_core_client",
    "reset_ai_core_client",
    "reset_face_ai_core_client",
]
