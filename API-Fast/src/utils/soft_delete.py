"""Soft-delete helpers. Rows stay in the database with deletedAt set."""
from __future__ import annotations

from datetime import datetime, timezone


def mark_deleted(row) -> None:
    row.deletedAt = datetime.now(timezone.utc)
