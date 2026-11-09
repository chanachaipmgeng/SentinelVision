"""Authz allow-list for Bearer sv_… tenant API keys."""
from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.security.middleware import _is_api_key_path_allowed  # noqa: E402

CID = str(uuid4())


def test_cameras_read_get_allowed():
    path = f"/cameras/company/{CID}/cameras"
    assert _is_api_key_path_allowed("GET", path, ["cameras.read"])
    assert not _is_api_key_path_allowed("POST", path, ["cameras.read"])
    assert not _is_api_key_path_allowed("GET", path, ["incidents.read"])


def test_incidents_read_get_allowed():
    path = f"/sentinel/company/{CID}/incidents"
    assert _is_api_key_path_allowed("GET", path, ["incidents.read"])
    assert _is_api_key_path_allowed("GET", f"{path}/{uuid4()}", ["incidents.read"])
    assert not _is_api_key_path_allowed("POST", path, ["incidents.read"])
    assert not _is_api_key_path_allowed("GET", path, ["cameras.read"])


def test_settings_paths_denied():
    path = f"/companys/{CID}/api-keys"
    assert not _is_api_key_path_allowed("GET", path, ["cameras.read", "incidents.read"])
