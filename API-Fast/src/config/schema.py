"""Single entry point for the application's SQLAlchemy metadata.

Importing this module registers every ORM mapper (models package + the tables that live in
``services/``) on :data:`Base.metadata`. Alembic (``alembic/env.py``) and the schema tests use it
as ``target_metadata`` so that autogenerate / ``alembic check`` see the complete schema.
"""
from __future__ import annotations

from sqlalchemy import MetaData

from .database import Base
from .. import models  # noqa: F401  registers every model module
from ..services import (  # noqa: F401  audit_log / outbox / import_job / error_log
    audit_service,
    error_log_service,
    notification_service,
)

metadata: MetaData = Base.metadata

__all__ = ["Base", "metadata"]
