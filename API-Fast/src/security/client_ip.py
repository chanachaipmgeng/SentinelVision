"""Trusted proxy client IP resolution (prevents X-Forwarded-For spoofing)."""
from __future__ import annotations

from fastapi import Request


def client_ip_from_request(request: Request, *, default: str = "unknown") -> str:
    """Resolve client IP preferring Nginx-controlled X-Real-IP or rightmost X-Forwarded-For hop."""
    xrip = (request.headers.get("x-real-ip") or "").strip()
    if xrip:
        return xrip
    xff = (request.headers.get("x-forwarded-for") or "").strip()
    if xff:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if parts:
            return parts[-1]
    return request.client.host if request.client else default
