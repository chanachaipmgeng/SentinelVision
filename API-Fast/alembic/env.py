"""Alembic environment — Alembic is the single source of truth for the database schema.

* ``target_metadata`` is the application's ``Base.metadata`` (``src/config/schema.py``), so
  ``alembic revision --autogenerate`` and ``alembic check`` compare the real models.
* The connection URL comes from ``DATABASE_URL`` (asyncpg URLs are rewritten to psycopg,
  the sync driver Alembic uses); ``DB_SCHEMA`` selects the application schema when the
  database is shared (``search_path`` + ``alembic_version`` live in that schema).

Typical commands (run from ``API-Fast/`` with ``DATABASE_URL`` exported)::

    alembic upgrade head                 # fresh install / upgrade
    alembic check                        # models vs database, exit 1 on drift
    alembic stamp 0008_revocation_kiosk_pairing && alembic upgrade head   # legacy create_all DBs
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

_raw_url = os.environ.get("DATABASE_URL", "")
if _raw_url:
    config.set_main_option(
        "sqlalchemy.url",
        _raw_url.replace("+asyncpg", "+psycopg").replace("%", "%%"),
    )
if config.config_file_name is not None and not config.get_main_option("skip_logging_config"):
    fileConfig(config.config_file_name)

# Importing src.config.schema needs DATABASE_URL (config/database.py binds the engine at import).
if not os.environ.get("DATABASE_URL"):
    os.environ["DATABASE_URL"] = config.get_main_option("sqlalchemy.url", "")

from src.config.database import DB_SCHEMA  # noqa: E402
from src.config.schema import metadata as target_metadata  # noqa: E402

_app_schema = DB_SCHEMA if DB_SCHEMA != "public" else None


def include_name(name, type_, parent_names):
    """Only compare objects that live in the application's schema."""
    if type_ == "schema":
        return name == _app_schema
    return True


def _configure_kwargs() -> dict:
    return {
        "target_metadata": target_metadata,
        "compare_type": True,
        "compare_server_default": False,
        "include_schemas": _app_schema is not None,
        "include_name": include_name,
        "version_table_schema": _app_schema,
    }


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_configure_kwargs(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section, {})
    connect_args = {}
    if _app_schema:
        connect_args["options"] = f"-csearch_path={_app_schema},public"
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    with connectable.connect() as connection:
        if _app_schema:
            from sqlalchemy import text

            connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{_app_schema}"'))
            connection.commit()
        context.configure(connection=connection, **_configure_kwargs())
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
