"""HMAC-signed Guest Self-Service Visitor Pre-Registration tokens."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException, status

from ..config.settings import settings

_INVITE_PREFIX = "sv_vis_"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + pad)


def _sign(payload_b64: str) -> str:
    secret = settings.SECRET_KEY.encode("utf-8")
    digest = hmac.new(secret, payload_b64.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def create_visitor_invite_token(
    *,
    company_id: UUID,
    visitor_name: str,
    host_name: Optional[str] = None,
    purpose: Optional[str] = None,
    valid_hours: int = 12,
    invite_ttl_hours: int = 72,
) -> dict[str, Any]:
    name = visitor_name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="visitorName is required",
        )
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=max(1, min(int(invite_ttl_hours), 168)))
    payload = {
        "typ": "visitor_invite",
        "cid": str(company_id),
        "name": name[:120],
        "host": (host_name or "").strip()[:120] or None,
        "purpose": (purpose or "").strip()[:200] or None,
        "vh": max(1, min(int(valid_hours), 720)),
        "exp": int(exp.timestamp()),
    }
    encoded = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    sig = _sign(encoded)
    token = f"{_INVITE_PREFIX}{encoded}.{sig}"
    return {
        "inviteToken": token,
        "invitePath": f"/sentinel/public/visitor-invite/{token}",
        "expiresAt": exp.isoformat(),
    }


def verify_visitor_invite_token(token: str) -> dict[str, Any]:
    raw = (token or "").strip()
    if not raw.startswith(_INVITE_PREFIX) or "." not in raw:
        raise HTTPException(status_code=400, detail="Invalid visitor invite token")
    body = raw[len(_INVITE_PREFIX) :]
    payload_b64, sig = body.split(".", 1)
    expected_sig = _sign(payload_b64)
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid visitor invite signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed visitor invite payload") from None

    if payload.get("typ") != "visitor_invite":
        raise HTTPException(status_code=400, detail="Invalid visitor invite type")
    exp_ts = int(payload.get("exp") or 0)
    if datetime.now(timezone.utc).timestamp() > exp_ts:
        raise HTTPException(status_code=410, detail="Visitor invite link has expired")

    return {
        "companyId": UUID(str(payload["cid"])),
        "visitorName": str(payload.get("name") or ""),
        "hostName": payload.get("host"),
        "purpose": payload.get("purpose"),
        "validHours": int(payload.get("vh") or 12),
        "expiresAt": datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat(),
    }


_PASS_PREFIX = "sv_pass_"


def create_visitor_pass_token(
    *,
    company_id: UUID,
    identity_id: UUID,
    visitor_name: str,
    valid_from: datetime,
    expires_at: datetime,
    zone_ids: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Generate a tamper-proof signed Visitor Digital Pass token for QR / badge verification."""
    payload = {
        "typ": "visitor_pass",
        "cid": str(company_id),
        "iid": str(identity_id),
        "name": visitor_name.strip()[:120],
        "vf": int(valid_from.timestamp()),
        "exp": int(expires_at.timestamp()),
        "zones": zone_ids or [],
    }
    encoded = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    sig = _sign(encoded)
    pass_code = f"{_PASS_PREFIX}{encoded}.{sig}"

    qr_data_url: Optional[str] = None
    try:
        import io
        import qrcode

        qr = qrcode.QRCode(box_size=6, border=2)
        qr.add_data(pass_code)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        qr_data_url = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
    except Exception:
        pass

    return {
        "passCode": pass_code,
        "qrData": pass_code,
        "qrDataUrl": qr_data_url,
        "validFrom": valid_from.isoformat(),
        "expiresAt": expires_at.isoformat(),
        "visitorName": visitor_name,
        "zones": zone_ids or [],
    }


def verify_visitor_pass_token(pass_code: str) -> dict[str, Any]:
    """Verify digital visitor pass signature and active validity window."""
    raw = (pass_code or "").strip()
    if not raw.startswith(_PASS_PREFIX) or "." not in raw:
        raise HTTPException(status_code=400, detail="Invalid visitor pass format")
    body = raw[len(_PASS_PREFIX) :]
    payload_b64, sig = body.split(".", 1)
    expected_sig = _sign(payload_b64)
    if not hmac.compare_digest(sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid or tampered visitor pass signature")
    try:
        payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed visitor pass payload") from None

    if payload.get("typ") != "visitor_pass":
        raise HTTPException(status_code=400, detail="Invalid token type, expected visitor_pass")

    now_ts = datetime.now(timezone.utc).timestamp()
    vf_ts = int(payload.get("vf") or 0)
    exp_ts = int(payload.get("exp") or 0)

    if now_ts < vf_ts:
        raise HTTPException(status_code=403, detail="Visitor pass is not yet active")
    if now_ts > exp_ts:
        raise HTTPException(status_code=410, detail="Visitor pass has expired")

    return {
        "companyId": UUID(str(payload["cid"])),
        "identityId": UUID(str(payload["iid"])),
        "visitorName": str(payload.get("name") or ""),
        "validFrom": datetime.fromtimestamp(vf_ts, tz=timezone.utc).isoformat(),
        "expiresAt": datetime.fromtimestamp(exp_ts, tz=timezone.utc).isoformat(),
        "zones": payload.get("zones") or [],
    }

