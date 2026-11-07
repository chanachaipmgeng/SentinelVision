"""RFC 6238 TOTP (Time-based One-Time Password) implementation using standard library only."""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
import urllib.parse
from typing import Optional


def generate_totp_secret(length_bytes: int = 20) -> str:
    """Generate a Base32-encoded 160-bit secret compatible with Google/Microsoft Authenticator."""
    raw = secrets.token_bytes(length_bytes)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _hotp(secret: str, counter: int, digits: int = 6) -> str:
    clean = (secret or "").strip().upper().replace(" ", "")
    padding = (8 - len(clean) % 8) % 8
    key = base64.b32decode(clean + ("=" * padding), casefold=True)
    msg = struct.pack(">Q", int(counter))
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code_int = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(code_int).zfill(digits)


def generate_totp_code(secret: str, *, timestamp: Optional[float] = None, period: int = 30) -> str:
    ts = time.time() if timestamp is None else float(timestamp)
    counter = int(ts // period)
    return _hotp(secret, counter)


def verify_totp(
    secret: str,
    code: str,
    *,
    timestamp: Optional[float] = None,
    period: int = 30,
    window: int = 1,
) -> bool:
    if not secret or not code:
        return False
    candidate = str(code).strip().replace(" ", "")
    if len(candidate) != 6 or not candidate.isdigit():
        return False
    ts = time.time() if timestamp is None else float(timestamp)
    base_counter = int(ts // period)
    for offset in range(-window, window + 1):
        expected = _hotp(secret, base_counter + offset)
        if hmac.compare_digest(expected, candidate):
            return True
    return False


def build_otpauth_uri(secret: str, username: str, issuer: str = "DPU Attendance") -> str:
    label = urllib.parse.quote(f"{issuer}:{username}")
    params = urllib.parse.urlencode(
        {
            "secret": secret,
            "issuer": issuer,
            "algorithm": "SHA1",
            "digits": "6",
            "period": "30",
        }
    )
    return f"otpauth://totp/{label}?{params}"
