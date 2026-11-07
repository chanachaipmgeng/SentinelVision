"""Alembic helpers used by the API process (startup check, optional auto-upgrade) and tests.

Alembic is the only component that changes the database schema. The API never runs
``create_all`` or ad-hoc DDL; it only verifies that the database is at the latest revision and,
when ``MIGRATE_ON_STARTUP=true``, runs ``alembic upgrade head`` before serving traffic.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from .database import DB_SCHEMA

logger = logging.getLogger("dpu.schema")

API_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = API_ROOT / "alembic.ini"
SCRIPT_LOCATION = API_ROOT / "alembic"


def alembic_config() -> Config:
    """Alembic ``Config`` bound to the repository's ``alembic.ini`` regardless of the CWD."""
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(SCRIPT_LOCATION))
    # The API already configured logging; env.py skips fileConfig when this flag is set.
    cfg.set_main_option("skip_logging_config", "true")
    return cfg


def head_revision() -> str:
    """Latest revision id in ``alembic/versions`` (the chain is linear, so exactly one head)."""
    heads = ScriptDirectory.from_config(alembic_config()).get_heads()
    if len(heads) != 1:
        raise RuntimeError(f"expected exactly one Alembic head, found {heads}")
    return heads[0]


def _version_table() -> str:
    return f'"{DB_SCHEMA}".alembic_version' if DB_SCHEMA != "public" else "alembic_version"


async def current_revision(connection) -> str | None:
    """Revision stamped in ``alembic_version`` or ``None`` when Alembic has never run."""
    try:
        row = await connection.execute(text(f"SELECT version_num FROM {_version_table()}"))
        return row.scalar_one_or_none()
    except (ProgrammingError, DBAPIError):
        # UndefinedTable: the database was created by the legacy create_all path (or is empty).
        return None


@dataclass(frozen=True)
class SchemaStatus:
    current: str | None
    head: str

    @property
    def at_head(self) -> bool:
        return self.current == self.head

    @property
    def code(self) -> str:
        if self.at_head:
            return "ok"
        return "unmanaged" if self.current is None else "behind"

    def as_dict(self) -> dict[str, str | None]:
        return {"status": self.code, "current": self.current, "head": self.head}


async def schema_status(connection) -> SchemaStatus:
    return SchemaStatus(current=await current_revision(connection), head=head_revision())


def upgrade_to_head() -> None:
    """Run ``alembic upgrade head`` synchronously (call via ``asyncio.to_thread`` from the app)."""
    command.upgrade(alembic_config(), "head")


def remediation_hint(status: SchemaStatus) -> str:
    if status.current is None:
        return (
            "alembic_version is missing. Fresh database: `alembic upgrade head`. Database created by the "
            "old create_all startup: `alembic stamp 0008_revocation_kiosk_pairing && alembic upgrade head` "
            "(docs/RUNBOOK.md, Database migrations)."
        )
    return f"database is at {status.current}, code expects {status.head}: run `alembic upgrade head`."
