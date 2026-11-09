"""Phase 5A: Telegram Bot API + Discord webhook outbox delivery."""
from __future__ import annotations

from io import BytesIO
from urllib.error import HTTPError

import pytest

from src.services import notification_service as ns


class _FakeResp:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_send_telegram_posts_send_message(monkeypatch):
    calls = []

    def _urlopen(req, timeout=20):
        calls.append(
            {
                "url": req.full_url,
                "data": req.data,
                "method": req.get_method(),
                "ctype": req.headers.get("Content-type") or req.headers.get("Content-Type"),
            }
        )
        return _FakeResp(200)

    monkeypatch.setattr(ns.urllib.request, "urlopen", _urlopen)
    ns._send_telegram(
        {
            "telegramBotToken": "123:ABC",
            "telegramChatId": "-10042",
            "body": "hello tg",
        }
    )
    assert len(calls) == 1
    assert calls[0]["url"] == "https://api.telegram.org/bot123:ABC/sendMessage"
    assert b'"chat_id":"-10042"' in calls[0]["data"]
    assert b'"text":"hello tg"' in calls[0]["data"]


def test_send_telegram_skips_without_token_or_chat(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("should not call network")

    monkeypatch.setattr(ns.urllib.request, "urlopen", _boom)
    ns._send_telegram({"telegramChatId": "1"})
    ns._send_telegram({"telegramBotToken": "t"})


def test_send_discord_posts_content(monkeypatch):
    calls = []

    def _urlopen(req, timeout=20):
        calls.append({"url": req.full_url, "data": req.data, "status_path": True})
        return _FakeResp(204)

    monkeypatch.setattr(ns.urllib.request, "urlopen", _urlopen)
    ns._send_discord(
        {
            "discordWebhookUrl": "https://discord.com/api/webhooks/1/secret",
            "body": "hello discord",
        }
    )
    assert len(calls) == 1
    assert calls[0]["url"] == "https://discord.com/api/webhooks/1/secret"
    assert b'"content":"hello discord"' in calls[0]["data"]


def test_send_discord_raises_on_http_error(monkeypatch):
    def _urlopen(req, timeout=20):
        raise HTTPError(req.full_url, 500, "boom", hdrs=None, fp=BytesIO(b"err"))

    monkeypatch.setattr(ns.urllib.request, "urlopen", _urlopen)
    with pytest.raises(HTTPError):
        ns._send_discord(
            {
                "discordWebhookUrl": "https://discord.com/api/webhooks/1/secret",
                "body": "x",
            }
        )


@pytest.mark.asyncio
async def test_drain_outbox_dispatches_telegram_and_discord(monkeypatch):
    """Unknown-channel regression: telegram/discord must not raise unknown channel."""
    from datetime import datetime, timezone
    from uuid import uuid4
    from unittest.mock import AsyncMock, MagicMock

    tg = []
    dc = []
    monkeypatch.setattr(ns, "_send_telegram", lambda p: tg.append(p))
    monkeypatch.setattr(ns, "_send_discord", lambda p: dc.append(p))
    monkeypatch.setattr(ns, "unseal_payload_secrets", lambda p: dict(p or {}))

    row_tg = MagicMock()
    row_tg.id = uuid4()
    row_tg.channel = "telegram"
    row_tg.attempts = 0
    row_tg.createdAt = datetime.now(timezone.utc)
    row_tg.payload = {
        "telegramBotToken": "t",
        "telegramChatId": "1",
        "body": "tg",
    }
    row_tg.status = "pending"
    row_tg.lastError = None
    row_tg.deadLetteredAt = None
    row_tg.companyId = None
    row_tg.event = "system.test"

    row_dc = MagicMock()
    row_dc.id = uuid4()
    row_dc.channel = "discord"
    row_dc.attempts = 0
    row_dc.createdAt = datetime.now(timezone.utc)
    row_dc.payload = {"discordWebhookUrl": "https://example/hook", "body": "dc"}
    row_dc.status = "pending"
    row_dc.lastError = None
    row_dc.deadLetteredAt = None
    row_dc.companyId = None
    row_dc.event = "system.test"

    result = MagicMock()
    result.scalars.return_value.all.return_value = [row_tg, row_dc]

    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = False
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    monkeypatch.setattr(ns, "async_session", lambda: session)

    sent = await ns.drain_outbox(limit=10)
    assert sent == 2
    assert row_tg.status == "sent"
    assert row_dc.status == "sent"
    assert tg and dc
