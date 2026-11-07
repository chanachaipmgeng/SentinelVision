import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Integration tests (tests/test_tenant_isolation.py) need a real PostgreSQL with pgvector.
# Resolution order, decided before any `src.*` import (config/database.py binds the engine
# to DATABASE_URL at import time):
#   1. TEST_DATABASE_URL  — an existing database (e.g. CI service container)
#   2. `pgserver` package — embedded PostgreSQL + pgvector started per pytest session
#   3. neither            — DB-backed tests skip themselves, unit tests still run
_embedded_pg = None


def _start_embedded_postgres():
    try:
        import pgserver  # type: ignore
    except ImportError:
        return None
    data_dir = tempfile.mkdtemp(prefix="dpu-test-pg-")
    server = pgserver.get_server(data_dir)
    server.psql("CREATE EXTENSION IF NOT EXISTS vector")
    uri = server.get_uri()  # postgresql://postgres:@/postgres?host=<socket dir>
    return server, uri.replace("postgresql://", "postgresql+asyncpg://", 1)


def pytest_configure(config):
    global _embedded_pg
    # Tests never need the production fail-fast guard on the placeholder SECRET_KEY.
    os.environ.setdefault("AUTH_FAIL_FAST", "false")
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        os.environ["DATABASE_URL"] = test_url
        os.environ["DPU_TEST_DB_READY"] = "1"
        return
    started = _start_embedded_postgres()
    if started is None:
        return
    _embedded_pg, url = started
    os.environ["DATABASE_URL"] = url
    os.environ["DB_SCHEMA"] = "public"
    os.environ["DPU_TEST_DB_READY"] = "1"


def pytest_unconfigure(config):
    global _embedded_pg
    if _embedded_pg is not None:
        try:
            _embedded_pg.cleanup()
        finally:
            _embedded_pg = None
