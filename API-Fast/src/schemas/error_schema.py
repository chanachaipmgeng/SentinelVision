"""Standard public API error envelope (Phase D6).

Public responses never include raw ``str(exception)``. Handlers and middleware share
:func:`error_body` so both ``/…`` and ``/api/v1/…`` aliases return the same shape.

``detail`` is kept as a string alias of ``error.message`` for older SPA clients.
"""
from __future__ import annotations

from typing import Any, Optional


def error_body(
    *,
    code: str,
    message: str,
    status_code: int,
    request_id: Optional[str] = None,
    details: Optional[Any] = None,
) -> dict:
    err: dict[str, Any] = {
        "code": code,
        "message": message,
        "status": int(status_code),
    }
    if request_id:
        err["requestId"] = request_id
    if details is not None:
        err["details"] = details
    return {"error": err, "detail": message}


def http_exception_code(status_code: int, detail: Any = None) -> str:
    """Map common status / detail tokens to stable machine codes."""
    if isinstance(detail, str):
        token = detail.strip().upper().replace(" ", "_")
        if token in {"MFA_REQUIRED", "INVALID_CREDENTIALS", "ACCOUNT_DISABLED"}:
            return token.lower()
        if detail == "MFA_REQUIRED":
            return "mfa_required"
    mapping = {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        501: "not_implemented",
        503: "unavailable",
    }
    return mapping.get(int(status_code), "http_error")


def sanitize_public_message(detail: Any, *, status_code: int = 500) -> str:
    """Never leak exception text on 5xx; keep intentional 4xx strings."""
    if status_code >= 500:
        return "Internal error"
    if detail is None:
        return "Request failed"
    if isinstance(detail, str):
        return detail
    if isinstance(detail, (list, dict)):
        # FastAPI validation errors — pass through as structured details separately.
        return "Validation failed"
    return "Request failed"
