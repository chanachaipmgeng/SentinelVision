"""Camera stream reachability — RTSP DESCRIBE / HTTP HEAD (adapted from AI_VISION)."""

from __future__ import annotations

import asyncio
import base64
import time
from urllib.parse import urlparse, urlunparse


def _parse_endpoint(url: str, protocol: str) -> tuple[str, int, str]:
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or protocol or "rtsp").lower()
    host = parsed.hostname or ""
    if not host:
        return "", 0, scheme
    default_port = 554
    if scheme in ("http", "https"):
        default_port = 443 if scheme == "https" else 80
    elif scheme == "rtmp":
        default_port = 1935
    port = parsed.port or default_port
    return host, port, scheme


def _rtsp_request_uri(url: str, parsed) -> str:
    if parsed.username:
        host = parsed.hostname or ""
        port = parsed.port
        netloc = f"{host}:{port}" if port else host
        return urlunparse((parsed.scheme, netloc, parsed.path or "/", "", parsed.query, ""))
    return url


def _basic_auth_header(parsed) -> str:
    if not parsed.username:
        return ""
    token = base64.b64encode(f"{parsed.username}:{parsed.password or ''}".encode()).decode("ascii")
    return f"Authorization: Basic {token}\r\n"


async def _read_rtsp_status(reader: asyncio.StreamReader, timeout: float) -> int | None:
    try:
        line = await asyncio.wait_for(reader.readline(), timeout=timeout)
    except TimeoutError:
        return None
    if not line:
        return None
    text = line.decode(errors="ignore").strip()
    parts = text.split()
    if len(parts) >= 2 and parts[0].upper().startswith("RTSP/"):
        try:
            return int(parts[1])
        except ValueError:
            return None
    return None


async def _close_writer(writer: asyncio.StreamWriter) -> None:
    writer.close()
    try:
        await asyncio.wait_for(writer.wait_closed(), timeout=1.0)
    except (TimeoutError, OSError):
        pass


async def _check_rtsp(
    url: str, host: str, port: int, timeout: float
) -> tuple[bool, float | None, str | None]:
    parsed = urlparse(url.strip())
    t0 = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
    except (TimeoutError, OSError):
        return False, None, "tcp_failed"

    tcp_ms = round((time.monotonic() - t0) * 1000, 1)
    request_uri = _rtsp_request_uri(url, parsed)
    auth = _basic_auth_header(parsed)
    remaining = max(0.5, timeout - (time.monotonic() - t0))
    req = (
        f"DESCRIBE {request_uri} RTSP/1.0\r\n"
        f"CSeq: 1\r\n"
        f"Accept: application/sdp\r\n"
        f"{auth}"
        f"User-Agent: SentinelVision/1.0\r\n"
        f"\r\n"
    ).encode()
    status: int | None = None
    try:
        writer.write(req)
        await writer.drain()
        status = await _read_rtsp_status(reader, remaining)
    except OSError:
        status = None
    finally:
        await _close_writer(writer)

    if status is None:
        return False, tcp_ms, "rtsp_no_response"
    if status in (200, 401):
        return True, tcp_ms, None
    return False, tcp_ms, f"rtsp_{status}"


async def _check_http(
    url: str, host: str, port: int, timeout: float
) -> tuple[bool, float | None, str | None]:
    parsed = urlparse(url.strip())
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    t0 = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
    except (TimeoutError, OSError):
        return False, None, "tcp_failed"

    host_header = host if port in (80, 443) else f"{host}:{port}"
    req = f"HEAD {path} HTTP/1.1\r\nHost: {host_header}\r\nConnection: close\r\n\r\n".encode()
    try:
        writer.write(req)
        await writer.drain()
        remaining = max(0.5, timeout - (time.monotonic() - t0))
        line = await asyncio.wait_for(reader.readline(), timeout=remaining)
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        text = line.decode(errors="ignore")
        ok = any(code in text for code in (" 200 ", " 401 ", " 403 "))
        return ok, latency_ms, None if ok else "http_error"
    except (TimeoutError, OSError):
        return False, None, "http_failed"
    finally:
        await _close_writer(writer)


async def check_stream_reachability(
    url: str,
    *,
    protocol: str = "rtsp",
    timeout: float = 4.0,
) -> dict:
    """Return ``{online, latency_ms, error?, check?}`` for a camera stream URL."""
    url = (url or "").strip()
    if not url:
        return {"online": False, "latency_ms": None, "error": "invalid_url", "check": "none"}

    host, port, scheme = _parse_endpoint(url, protocol)
    if not host:
        return {"online": False, "latency_ms": None, "error": "invalid_url", "check": "none"}

    proto = (protocol or scheme or "rtsp").lower()
    if proto in ("browser", "file"):
        return {"online": False, "latency_ms": None, "error": "not_pingable", "check": "none"}

    if scheme in ("rtsp", "rtsps") or proto == "rtsp":
        online, latency_ms, err = await _check_rtsp(url, host, port, timeout)
        return {
            "online": online,
            "latency_ms": latency_ms,
            "error": err,
            "check": "rtsp_describe",
        }

    if scheme in ("http", "https") or proto in ("http", "hls"):
        online, latency_ms, err = await _check_http(url, host, port, timeout)
        return {
            "online": online,
            "latency_ms": latency_ms,
            "error": err,
            "check": "http_head",
        }

    t0 = time.monotonic()
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        latency_ms = round((time.monotonic() - t0) * 1000, 1)
        await _close_writer(writer)
        return {"online": True, "latency_ms": latency_ms, "check": "tcp"}
    except (TimeoutError, OSError):
        return {"online": False, "latency_ms": None, "error": "tcp_failed", "check": "tcp"}
