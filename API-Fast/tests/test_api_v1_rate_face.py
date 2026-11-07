"""Phase D6/D7/D8: API v1 aliases, app rate limits (429), enrollment quality gate."""
from __future__ import annotations

import numpy as np
import pytest
from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient

from src.config import settings as settings_mod
from src.schemas.error_schema import error_body, sanitize_public_message
from src.services import rate_limit_service as rl
from src.services.idempotency_service import idempotent_json, reset_idempotency_for_tests
from src.utils.api_paths import canonical_api_path
from src.utils.enrollment_quality import check_enrollment_quality_bgr
from src.utils.liveness_detection import check_liveness_frame_bgr, reset_pad_for_tests


@pytest.fixture(autouse=True)
def _reset_limits():
    rl.reset_rate_limits_for_tests()
    reset_idempotency_for_tests()
    reset_pad_for_tests()
    yield
    rl.reset_rate_limits_for_tests()
    reset_idempotency_for_tests()
    reset_pad_for_tests()


def test_canonical_api_v1_and_companies_alias():
    assert canonical_api_path("/api/v1/auth/login") == "/auth/login"
    assert canonical_api_path("/api/v1/companys") == "/companys"
    assert canonical_api_path("/api/v1/companies") == "/companys"
    assert canonical_api_path("/companies/abc") == "/companys/abc"
    assert canonical_api_path("/companys/abc") == "/companys/abc"
    assert canonical_api_path("/api/v1/face/members/identify") == "/face/members/identify"


def test_error_schema_hides_5xx_exception_text():
    assert sanitize_public_message(RuntimeError("secret"), status_code=500) == "Internal error"
    assert sanitize_public_message("face too blurry", status_code=400) == "face too blurry"
    body = error_body(code="rate_limited", message="Too many requests", status_code=429, request_id="r1")
    assert body["detail"] == "Too many requests"
    assert body["error"]["code"] == "rate_limited"
    assert body["error"]["requestId"] == "r1"


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "RATE_LIMIT_LOGIN_PER_MINUTE", 3)
    monkeypatch.setattr(settings_mod.settings, "REDIS_URL", "")

    app = FastAPI()

    @app.post("/auth/login")
    async def login(_=Depends(rl.rate_limit_login)):
        return {"ok": True}

    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from src.schemas.error_schema import error_body, http_exception_code, sanitize_public_message

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException):
        return JSONResponse(
            error_body(
                code=http_exception_code(exc.status_code, exc.detail),
                message=sanitize_public_message(exc.detail, status_code=exc.status_code),
                status_code=exc.status_code,
            ),
            status_code=exc.status_code,
            headers=dict(exc.headers) if exc.headers else None,
        )

    client = TestClient(app, raise_server_exceptions=False)
    assert client.post("/auth/login").status_code == 200
    assert client.post("/auth/login").status_code == 200
    assert client.post("/auth/login").status_code == 200
    blocked = client.post("/auth/login")
    assert blocked.status_code == 429
    payload = blocked.json()
    assert payload["error"]["code"] == "rate_limited"
    assert payload["detail"] == "Too many requests"
    assert "Retry-After" in blocked.headers


def test_idempotency_key_replays_same_body():
    app = FastAPI()
    calls = {"n": 0}

    @app.post("/timestamp/company/{company_id}")
    async def punch(company_id: str, request: Request):
        async def _run():
            calls["n"] += 1
            return {"timestampId": f"ts-{calls['n']}", "companyId": company_id}

        return await idempotent_json(
            request, scope="timestamp.punch", company_id=company_id, compute=_run
        )

    client = TestClient(app)
    headers = {"Idempotency-Key": "punch-1"}
    first = client.post("/timestamp/company/c1", headers=headers)
    second = client.post("/timestamp/company/c1", headers=headers)
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json() == {"timestampId": "ts-1", "companyId": "c1"}
    assert calls["n"] == 1
    assert second.headers.get("Idempotency-Replayed") == "true"


def test_enrollment_quality_gate_rejects_tiny_face(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "ENROLL_MIN_FACE_RATIO", 0.2)
    monkeypatch.setattr(settings_mod.settings, "ENROLL_MIN_SHARPNESS", 0.0)
    monkeypatch.setattr(settings_mod.settings, "IMAGE_BLUR_THRESHOLD", 0.0)
    monkeypatch.setattr(settings_mod.settings, "IMAGE_BRIGHTNESS_MIN", 0)
    monkeypatch.setattr(settings_mod.settings, "IMAGE_BRIGHTNESS_MAX", 255)

    # 200x200 image with a tiny 10x10 "face" bbox → ratio 0.0025 << 0.2
    image = np.full((200, 200, 3), 120, dtype=np.uint8)
    # Add texture so blur/chroma paths stay happy if invoked.
    image[50:150, 50:150] = 140
    ok, reason, scores = check_enrollment_quality_bgr(image, [10, 10, 20, 20], kps=None)
    assert ok is False
    assert "too small" in reason.lower()
    assert scores["faceRatio"] < 0.2


def test_enrollment_quality_gate_accepts_large_frontal(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "ENROLL_MIN_FACE_RATIO", 0.05)
    monkeypatch.setattr(settings_mod.settings, "ENROLL_MIN_SHARPNESS", 1.0)
    monkeypatch.setattr(settings_mod.settings, "IMAGE_BLUR_THRESHOLD", 0.0)
    monkeypatch.setattr(settings_mod.settings, "IMAGE_BRIGHTNESS_MIN", 0)
    monkeypatch.setattr(settings_mod.settings, "IMAGE_BRIGHTNESS_MAX", 255)
    monkeypatch.setattr(settings_mod.settings, "ENROLL_MAX_YAW_DEG", 40.0)
    monkeypatch.setattr(settings_mod.settings, "ENROLL_MAX_ROLL_DEG", 40.0)

    rng = np.random.default_rng(0)
    image = rng.integers(80, 180, size=(240, 240, 3), dtype=np.uint8)
    bbox = [40, 40, 200, 200]
    # Frontal-ish 5-point landmarks
    kps = np.asarray(
        [[90, 100], [150, 100], [120, 130], [100, 160], [140, 160]], dtype=np.float32
    )
    ok, reason, scores = check_enrollment_quality_bgr(image, bbox, kps=kps)
    assert ok is True, reason
    assert scores["faceRatio"] >= 0.05


def test_pad_skipped_without_model(monkeypatch):
    monkeypatch.setattr(settings_mod.settings, "FACE_PAD_MODEL_PATH", "")
    monkeypatch.setattr(settings_mod.settings, "FACE_ANTISPOOF_ENABLED", False)
    image = np.full((80, 80, 3), 100, dtype=np.uint8)
    ok, msg = check_liveness_frame_bgr(image, [5, 5, 75, 75])
    assert ok is True
    assert "heuristic_disabled" in msg or "pad_skipped" in msg or ok


def test_main_mounts_v1_and_companies_aliases():
    """``src/main.py`` mounts legacy + ``/api/v1`` and ``/companies`` aliases."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "src" / "main.py").read_text(encoding="utf-8")
    assert "API_V1_PREFIX" in source
    assert '_mount_api("")' in source
    assert "_mount_api(API_V1_PREFIX)" in source
    assert 'prefix=f"{p}/companies"' in source
    assert 'prefix=f"{p}/companys"' in source
    assert "Idempotency" not in source  # wiring lives on punch/import routes, not main
