"""B1: the real ``src.main`` application boots without running DDL and gates /ready on the schema.

* ``/health`` is 200 regardless of the database state
* ``/ready`` is 200 when ``alembic_version`` is at head and reports the revision
* ``/ready`` is 503 ``schema_out_of_date`` when the database is behind head (REQUIRE_SCHEMA_HEAD)
  and recovers without a restart once ``alembic upgrade head`` ran
* ``MIGRATE_ON_STARTUP=true`` upgrades the database during startup

Needs the test database from tests/conftest.py. InsightFace is stubbed there, so the GPU queue
starts without loading a model (workers load lazily).
"""
from __future__ import annotations

import asyncio
import importlib
import os
import sys
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient

if not os.environ.get("DPU_TEST_DB_READY"):
    pytest.skip(
        "No test database: set TEST_DATABASE_URL or `pip install pgserver`",
        allow_module_level=True,
    )

import src.config.settings as settings_mod  # noqa: E402
from src.config import migrations  # noqa: E402
from src.config.database import engine  # noqa: E402

API_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def main_module():
    """Import ``src.main`` once (it mounts static dirs relative to the CWD)."""
    cwd = os.getcwd()
    os.chdir(API_ROOT)
    for folder in ("uploaded_images", "enrolled_images", "temp_images"):
        (API_ROOT / folder).mkdir(exist_ok=True)
    try:
        if "src.main" in sys.modules:
            module = importlib.reload(sys.modules["src.main"])
        else:
            module = importlib.import_module("src.main")
        yield module
    finally:
        os.chdir(cwd)


def _dispose():
    async def _d():
        await engine.dispose()

    asyncio.run(_d())


@pytest.fixture(autouse=True)
def _reset_pool():
    _dispose()
    yield
    _dispose()


def _client(main_module) -> TestClient:
    return TestClient(main_module.app)


def test_health_and_ready_at_head(main_module, monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "MIGRATE_ON_STARTUP", False)
    monkeypatch.setattr(settings_mod.settings, "REQUIRE_SCHEMA_HEAD", True)
    with _client(main_module) as client:
        assert client.get("/health").json() == {"status": "ok"}
        ready = client.get("/ready")
        assert ready.status_code == 200, ready.text
        body = ready.json()
        assert body["status"] == "ok"
        assert body["schema"] == {
            "status": "ok",
            "current": migrations.head_revision(),
            "head": migrations.head_revision(),
        }
        assert body["queue"]["started"] is True


def test_ready_is_503_until_schema_reaches_head(main_module, monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "MIGRATE_ON_STARTUP", False)
    monkeypatch.setattr(settings_mod.settings, "REQUIRE_SCHEMA_HEAD", True)
    cfg = migrations.alembic_config()
    command.downgrade(cfg, "-1")
    try:
        with _client(main_module) as client:
            assert client.get("/health").status_code == 200
            ready = client.get("/ready")
            assert ready.status_code == 503, ready.text
            assert ready.json()["code"] == "schema_out_of_date"
            assert ready.json()["schema"]["status"] == "behind"
            # Operator migrates while the API keeps running → readiness recovers on the next probe.
            command.upgrade(cfg, "head")
            assert client.get("/ready").status_code == 200
    finally:
        command.upgrade(cfg, "head")


def test_ready_only_warns_when_strict_gate_disabled(main_module, monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "MIGRATE_ON_STARTUP", False)
    monkeypatch.setattr(settings_mod.settings, "REQUIRE_SCHEMA_HEAD", False)
    cfg = migrations.alembic_config()
    command.downgrade(cfg, "-1")
    try:
        with _client(main_module) as client:
            ready = client.get("/ready")
            assert ready.status_code == 200, ready.text
            assert ready.json()["schema"]["status"] == "behind"
    finally:
        command.upgrade(cfg, "head")


def test_migrate_on_startup_upgrades_to_head(main_module, monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "MIGRATE_ON_STARTUP", True)
    monkeypatch.setattr(settings_mod.settings, "REQUIRE_SCHEMA_HEAD", True)
    cfg = migrations.alembic_config()
    command.downgrade(cfg, "-1")
    try:
        with _client(main_module) as client:
            ready = client.get("/ready")
            assert ready.status_code == 200, ready.text
            assert ready.json()["schema"]["status"] == "ok"
    finally:
        command.upgrade(cfg, "head")
