"""Face-login challenge JWT helpers."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.security import jwt as jwt_mod  # noqa: E402


def test_face_login_challenge_roundtrip(monkeypatch):
    monkeypatch.setattr(jwt_mod.settings, "SECRET_KEY", "x" * 48)
    monkeypatch.setattr(jwt_mod.settings, "FACE_LOGIN_CHALLENGE_SECONDS", 45)
    mid = str(uuid.uuid4())
    token = jwt_mod.create_face_login_challenge(mid)
    payload = jwt_mod.decode_face_login_challenge(token)
    assert payload["memberId"] == mid
    assert payload["typ"] == jwt_mod.TYP_FACE_LOGIN_CHAL


def test_face_login_challenge_rejects_access_token(monkeypatch):
    monkeypatch.setattr(jwt_mod.settings, "SECRET_KEY", "x" * 48)
    mid = str(uuid.uuid4())
    access = jwt_mod.create_access_token(mid, "admin")
    with pytest.raises(HTTPException) as exc:
        jwt_mod.decode_face_login_challenge(access)
    assert exc.value.status_code == 401
