"""B4 fail-fast: weak SECRET_KEY / example database password must abort production startup."""
import pytest

from src.config.settings import settings
from src.security import startup_checks


@pytest.fixture(autouse=True)
def _fail_fast_on(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_FAIL_FAST", True)
    monkeypatch.setattr(settings, "SECRET_KEY", "x" * 48)


def test_database_password_parsing_handles_encoding():
    url = "postgresql+asyncpg://dpu:p%40ss%3Aword@db:5432/dpu"
    assert startup_checks.database_password(url) == "p@ss:word"
    assert startup_checks.database_password("postgresql://dpu@db/dpu") is None
    assert startup_checks.database_password("") is None


@pytest.mark.parametrize("password", ["dpu_secret", "postgres", "", "Change-Me", "localdev_secret"])
def test_weak_passwords_detected(password):
    assert startup_checks.database_password_is_weak(password)


def test_strong_password_accepted():
    assert not startup_checks.database_password_is_weak("4f9d1c0e-rotated-2026")


def test_production_refuses_compose_default_password(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://dpu:dpu_secret@db:5432/dpu")
    with pytest.raises(RuntimeError, match="example password"):
        startup_checks.assert_runtime_secrets_configured()


def test_development_only_warns(monkeypatch, caplog):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://dpu:dpu_secret@db:5432/dpu")
    with caplog.at_level("WARNING", logger="dpu.startup"):
        startup_checks.assert_runtime_secrets_configured()
    assert any("example password" in r.getMessage() for r in caplog.records)


def test_production_accepts_rotated_password(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://dpu:S3cure-rotated-pw@db:5432/dpu")
    startup_checks.assert_runtime_secrets_configured()


def test_weak_secret_key_still_refused(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://dpu:S3cure-rotated-pw@db:5432/dpu")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        startup_checks.assert_runtime_secrets_configured()


def test_fail_fast_off_disables_everything(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_FAIL_FAST", False)
    monkeypatch.setattr(settings, "SECRET_KEY", "secret")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://dpu:dpu_secret@db:5432/dpu")
    startup_checks.assert_runtime_secrets_configured()
