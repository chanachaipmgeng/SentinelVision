import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Integration tests (tests/test_token_lifecycle.py) run against TEST_DATABASE_URL when set;
# it must win over the DATABASE_URL in .env, so export it before src.config.database is imported.
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
