"""Fernet encryption for secrets stored inside notification_outbox payloads (D3).

Key source: ``OUTBOX_ENCRYPTION_KEY`` (url-safe Fernet key, 32 url-safe base64-encoded bytes).
Generate with::

    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

When the env key is empty, seal/unseal are no-ops (plaintext) so local/dev keeps working;
production should set the key. Never commit a real key.
"""
from __future__ import annotations

import logging
from typing import Any, Mapping, MutableMapping, Optional

from cryptography.fernet import Fernet, InvalidToken

from ..config.settings import settings

logger = logging.getLogger("dpu.outbox_crypto")

SECRET_FIELDS = ("lineToken", "webhookSecret", "lineChannelAccessToken")
_PREFIX = "fernet:"


def _fernet() -> Optional[Fernet]:
    raw = (getattr(settings, "OUTBOX_ENCRYPTION_KEY", "") or "").strip()
    if not raw:
        return None
    try:
        return Fernet(raw.encode("utf-8") if isinstance(raw, str) else raw)
    except Exception as exc:  # noqa: BLE001 — invalid key must not crash worker
        logger.error("OUTBOX_ENCRYPTION_KEY is invalid: %s", exc)
        return None


def encrypt_secret(value: str) -> str:
    """Encrypt a secret string. Returns ``fernet:<token>`` or plaintext when key unset."""
    if value is None:
        return ""
    text = str(value)
    if not text or text.startswith(_PREFIX):
        return text
    f = _fernet()
    if f is None:
        return text
    token = f.encrypt(text.encode("utf-8")).decode("utf-8")
    return f"{_PREFIX}{token}"


def decrypt_secret(value: str) -> str:
    """Decrypt a ``fernet:…`` value; plaintext passthrough when unprefixed or key unset."""
    if value is None:
        return ""
    text = str(value)
    if not text.startswith(_PREFIX):
        return text
    token = text[len(_PREFIX) :]
    f = _fernet()
    if f is None:
        raise RuntimeError("OUTBOX_ENCRYPTION_KEY required to decrypt sealed outbox secret")
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("failed to decrypt outbox secret") from exc


def seal_payload_secrets(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a copy of ``payload`` with known secret fields Fernet-encrypted."""
    out: dict[str, Any] = dict(payload or {})
    for field in SECRET_FIELDS:
        if field in out and out[field]:
            out[field] = encrypt_secret(str(out[field]))
    return out


def unseal_payload_secrets(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a copy of ``payload`` with known secret fields decrypted for delivery."""
    out: dict[str, Any] = dict(payload or {})
    for field in SECRET_FIELDS:
        if field in out and out[field]:
            out[field] = decrypt_secret(str(out[field]))
    return out


def redact_payload_for_api(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    """Strip secret values before returning outbox rows to the admin UI."""
    out: MutableMapping[str, Any] = dict(payload or {})
    for field in SECRET_FIELDS:
        if field in out and out[field]:
            out[field] = "***"
            out[f"has{field[0].upper()}{field[1:]}"] = True
    return dict(out)
