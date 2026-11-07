import os
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Integration tests (tests/test_tenant_isolation.py, tests/test_token_lifecycle.py) need a real
# PostgreSQL with pgvector. Resolution order, decided before any `src.*` import
# (config/database.py binds the engine to DATABASE_URL at import time):
#   1. TEST_DATABASE_URL  — an existing database (e.g. CI service container); it must win over
#                           the DATABASE_URL in .env, so it is exported here as well
#   2. `pgserver` package — embedded PostgreSQL + pgvector started per pytest session
#   3. neither            — DB-backed tests skip themselves, unit tests still run
_embedded_pg = None

if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

# Route modules import the InsightFace engine at module level; stub it when the GPU stack is not
# installed so auth/HR routes can be tested without onnxruntime.
try:
    import insightface  # noqa: F401
except ImportError:  # pragma: no cover - only on machines without the face stack
    _insightface = types.ModuleType("insightface")
    _insightface_app = types.ModuleType("insightface.app")

    class _FaceAnalysisStub:  # minimal placeholder; never instantiated in tests
        def __init__(self, *args, **kwargs):
            raise RuntimeError("insightface is not installed in this test environment")

    _insightface_app.FaceAnalysis = _FaceAnalysisStub
    _insightface.app = _insightface_app
    sys.modules["insightface"] = _insightface
    sys.modules["insightface.app"] = _insightface_app

try:
    import onnxruntime  # noqa: F401
except ImportError:  # pragma: no cover
    sys.modules["onnxruntime"] = types.ModuleType("onnxruntime")


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


def _migrate_test_database() -> None:
    """Bring the test database to Alembic head (the API no longer runs create_all)."""
    from src.config.migrations import upgrade_to_head

    upgrade_to_head()


def pytest_configure(config):
    global _embedded_pg
    # Tests never need the production fail-fast guard on the placeholder SECRET_KEY.
    os.environ.setdefault("AUTH_FAIL_FAST", "false")
    # The API process must not migrate on its own in tests; conftest does it once per session.
    os.environ["MIGRATE_ON_STARTUP"] = "false"
    test_url = os.environ.get("TEST_DATABASE_URL")
    if test_url:
        os.environ["DATABASE_URL"] = test_url
    else:
        started = _start_embedded_postgres()
        if started is None:
            return
        _embedded_pg, url = started
        os.environ["DATABASE_URL"] = url
        os.environ["DB_SCHEMA"] = "public"
    _migrate_test_database()
    os.environ["DPU_TEST_DB_READY"] = "1"


def pytest_unconfigure(config):
    global _embedded_pg
    if _embedded_pg is not None:
        try:
            _embedded_pg.cleanup()
        finally:
            _embedded_pg = None
    # src.main's configure_logging() attached handlers to pytest's (now closed) capture stream;
    # drop them so pgserver's atexit logging does not print "I/O operation on closed file".
    import logging

    logging.getLogger().handlers.clear()
