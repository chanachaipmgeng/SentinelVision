"""Shared server-side page envelope for list endpoints (Phase E2)."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PageEnvelope(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = 0
    offset: int = 0


def page_envelope(items: list[Any], *, total: int, limit: int, offset: int) -> dict[str, Any]:
    return {
        "items": items,
        "total": int(total),
        "limit": int(limit),
        "offset": int(offset),
    }
