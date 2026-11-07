"""Fail-fast checks for secrets that must never reach production with example values.

``APP_ENV`` defaults to ``production``; a deployment has to opt *into* development mode.
``AUTH_FAIL_FAST=false`` disables every check (local throwaway runs, unit tests) and is
logged loudly so it cannot hide in a server ``.env``.

Checks:
* ``SECRET_KEY`` — random, >= 32 chars, not a known placeholder (always when fail-fast is on,
  see :func:`security.jwt.assert_secret_configured`).
* database password inside ``DATABASE_URL`` — not empty and not one of the example /
  compose-default values (``dpu_secret`` …). Fatal in production, a warning in development
  so ``cp .env.example .env`` still works on a laptop.
"""
from __future__ import annotations

import logging
import os
from urllib.parse import unquote, urlsplit

from ..config.settings import settings
from .jwt import assert_secret_configured

logger = logging.getLogger("dpu.startup")

WEAK_DB_PASSWORDS = frozenset(
    {
        "",
        "dpu_secret",
        "localdev_secret",
        "postgres",
        "password",
        "changeme",
        "change-me",
        "change-me-in-production",
        "secret",
    }
)
DEVELOPMENT_ENVS = frozenset({"development", "dev", "local", "test"})


def is_production() -> bool:
    return (settings.APP_ENV or "production").strip().lower() not in DEVELOPMENT_ENVS


def database_password(database_url: str | None = None) -> str | None:
    """Return the password part of ``DATABASE_URL`` (``None`` when absent/unparseable)."""
    url = database_url if database_url is not None else os.getenv("DATABASE_URL", "")
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    if parts.password is None:
        return None
    return unquote(parts.password)


def database_password_is_weak(password: str | None) -> bool:
    if password is None:
        return True
    return password.strip().lower() in WEAK_DB_PASSWORDS


def assert_database_credentials_configured() -> None:
    if not settings.AUTH_FAIL_FAST:
        return
    password = database_password()
    if not database_password_is_weak(password):
        return
    message = (
        "POSTGRES_PASSWORD / DATABASE_URL still uses an example password "
        "(dpu_secret / postgres / password / ...). Set a real password in .env "
        "(compose refuses to start without POSTGRES_PASSWORD) and rotate the database role."
    )
    if is_production():
        raise RuntimeError(f"{message} Set APP_ENV=development to downgrade this to a warning locally.")
    logger.warning("%s (APP_ENV=%s: continuing)", message, settings.APP_ENV)


def assert_runtime_secrets_configured() -> None:
    """Called once at import time from ``main.py`` before the app is built."""
    if not settings.AUTH_FAIL_FAST:
        logger.warning(
            "AUTH_FAIL_FAST=false: SECRET_KEY / database password checks are DISABLED "
            "(APP_ENV=%s). Never run production this way.",
            settings.APP_ENV,
        )
        return
    assert_secret_configured()
    assert_database_credentials_configured()
