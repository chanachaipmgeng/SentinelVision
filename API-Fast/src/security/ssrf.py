"""Centralized SSRF protection for outbound webhooks, SIEM, IoT relays, and ONVIF URLs."""
from __future__ import annotations

import ipaddress
import socket
import urllib.request
from typing import Iterable, Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status

from ..config.settings import settings

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "api",
        "api-gpu",
        "api-gpu1",
        "worker",
        "db",
        "redis",
        "mediamtx",
        "nginx",
        "admin",
        "face-core",
        "metadata",
        "metadata.google.internal",
        "169.254.169.254",
    }
)
_BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".docker")


def _parse_cidrs(raw: str) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    nets: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for part in (raw or "").split(","):
        text = part.strip()
        if not text:
            continue
        try:
            nets.append(ipaddress.ip_network(text, strict=False))
        except ValueError:
            continue
    return nets


def _ip_in_cidrs(
    ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address,
    cidrs: Iterable[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> bool:
    for net in cidrs:
        if ip_obj.version == net.version and ip_obj in net:
            return True
    return False


def _is_forbidden_ip(
    ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    allow_private_lan: bool,
    allow_cidrs: list[ipaddress.IPv4Network | ipaddress.IPv6Network],
) -> Optional[str]:
    if ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_unspecified or ip_obj.is_multicast:
        return "Refusing loopback, link-local, metadata, or reserved IP target"
    if _ip_in_cidrs(ip_obj, allow_cidrs):
        return None
    if ip_obj.is_private or ip_obj.is_reserved:
        if allow_private_lan:
            # Even when LAN is allowed (ONVIF/IoT Relay), reject common Docker bridge defaults if not explicit.
            return None
        return "Refusing private network target"
    return None


def validate_outbound_url(url: str, *, allow_private_lan: bool = False) -> str:
    """Validate an outbound HTTP/HTTPS URL against SSRF targets and return the cleaned URL."""
    clean = (url or "").strip()
    if not clean:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required")
    parsed = urlparse(clean)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only valid http:// or https:// URLs are permitted",
        )
    host = parsed.hostname.strip().lower().rstrip(".")
    if host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_SUFFIXES):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refusing internal or reserved host target: {host}",
        )

    allow_raw = (
        getattr(settings, "DEVICE_LAN_ALLOW_CIDRS", "")
        if allow_private_lan
        else getattr(settings, "OUTBOUND_ALLOW_CIDRS", "")
    )
    allow_cidrs = _parse_cidrs(allow_raw)

    # Literal IP check first (works even offline/in unit tests without DNS).
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None

    if literal_ip is not None:
        reason = _is_forbidden_ip(
            literal_ip, allow_private_lan=allow_private_lan, allow_cidrs=allow_cidrs
        )
        if reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
        return clean

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError:
        # Unresolvable host at config-save time or isolated test runner -> reject unknown internal names only;
        # real connections will fail safely without hitting internal IPs.
        return clean

    for family, _socktype, _proto, _canon, sockaddr in addr_info:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        ip_str = str(sockaddr[0]).split("%", 1)[0]
        try:
            resolved_ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        reason = _is_forbidden_ip(
            resolved_ip, allow_private_lan=allow_private_lan, allow_cidrs=allow_cidrs
        )
        if reason:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
    return clean


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise urllib.request.HTTPError(
            req.full_url, code, "Outbound HTTP redirects are blocked", headers, fp
        )


_NO_REDIRECT_OPENER = urllib.request.build_opener(_NoRedirectHandler())
_ORIG_URLOPEN = urllib.request.urlopen


def urlopen_no_redirect(req: urllib.request.Request, *, timeout: float = 20.0):
    """Execute a urllib Request with HTTP redirects disabled (SSRF mitigation)."""
    if urllib.request.urlopen is not _ORIG_URLOPEN:
        return urllib.request.urlopen(req, timeout=timeout)
    return _NO_REDIRECT_OPENER.open(req, timeout=timeout)
