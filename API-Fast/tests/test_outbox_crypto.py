"""D3: Fernet sealing of secrets stored in notification_outbox payloads."""
from __future__ import annotations

from cryptography.fernet import Fernet

from src.services import outbox_crypto as crypto


def test_encrypt_decrypt_roundtrip(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(crypto.settings, "OUTBOX_ENCRYPTION_KEY", key)
    sealed = crypto.encrypt_secret("super-secret-token")
    assert sealed.startswith("fernet:")
    assert sealed != "super-secret-token"
    assert crypto.decrypt_secret(sealed) == "super-secret-token"


def test_seal_unseal_payload_fields(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(crypto.settings, "OUTBOX_ENCRYPTION_KEY", key)
    sealed = crypto.seal_payload_secrets(
        {
            "body": "hello",
            "lineToken": "LINE-TOKEN",
            "webhookSecret": "WH-SECRET",
            "lineChannelAccessToken": "CA-TOKEN",
        }
    )
    assert sealed["body"] == "hello"
    assert sealed["lineToken"].startswith("fernet:")
    assert sealed["webhookSecret"].startswith("fernet:")
    assert sealed["lineChannelAccessToken"].startswith("fernet:")
    open_ = crypto.unseal_payload_secrets(sealed)
    assert open_["lineToken"] == "LINE-TOKEN"
    assert open_["webhookSecret"] == "WH-SECRET"
    assert open_["lineChannelAccessToken"] == "CA-TOKEN"


def test_plaintext_passthrough_when_key_unset(monkeypatch):
    monkeypatch.setattr(crypto.settings, "OUTBOX_ENCRYPTION_KEY", "")
    assert crypto.encrypt_secret("plain") == "plain"
    sealed = crypto.seal_payload_secrets({"lineToken": "abc", "body": "x"})
    assert sealed["lineToken"] == "abc"
    assert crypto.unseal_payload_secrets(sealed)["lineToken"] == "abc"


def test_redact_for_api(monkeypatch):
    monkeypatch.setattr(crypto.settings, "OUTBOX_ENCRYPTION_KEY", "")
    redacted = crypto.redact_payload_for_api({"lineToken": "abc", "body": "hi"})
    assert redacted["lineToken"] == "***"
    assert redacted["body"] == "hi"


def test_idempotent_reencrypt(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(crypto.settings, "OUTBOX_ENCRYPTION_KEY", key)
    once = crypto.encrypt_secret("tok")
    twice = crypto.encrypt_secret(once)
    assert once == twice
