"""Compatibility re-exports — face pipeline now uses InsightFace via face_engine."""

from .face_engine import generate_face_encoding, verify_liveness_and_get_encoding

__all__ = ["generate_face_encoding", "verify_liveness_and_get_encoding"]
