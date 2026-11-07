"""Canonicalize public API paths for authz (Phase D6).

Legacy routes stay mounted at the root. ``/api/v1/...`` is an alias of the same
handlers. ``/companies`` is an alias of the historical ``/companys`` typo.
"""
from __future__ import annotations

API_V1_PREFIX = "/api/v1"


def strip_api_v1(path: str) -> str:
    if path == API_V1_PREFIX or path.startswith(API_V1_PREFIX + "/"):
        rest = path[len(API_V1_PREFIX) :] or "/"
        return rest if rest.startswith("/") else f"/{rest}"
    return path


def companies_to_companys(path: str) -> str:
    if path == "/companies" or path.startswith("/companies/"):
        return "/companys" + path[len("/companies") :]
    return path


def canonical_api_path(path: str) -> str:
    """Normalize for AuthzMiddleware company binding and open-prefix checks."""
    normalized = path.rstrip("/") or "/"
    return companies_to_companys(strip_api_v1(normalized))
