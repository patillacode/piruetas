from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.notifications import _notify_ntfy, _notify_telegram, send_notification


def _settings(
    ntfy_url="", ntfy_topic="", ntfy_token="", telegram_bot_token="", telegram_chat_id=""
):
    s = MagicMock()
    s.ntfy_url = ntfy_url
    s.ntfy_topic = ntfy_topic
    s.ntfy_token = ntfy_token
    s.telegram_bot_token = telegram_bot_token
    s.telegram_chat_id = telegram_chat_id
    return s


@pytest.mark.asyncio
async def test_notify_ntfy_posts_to_url():
    with patch("app.notifications.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        await _notify_ntfy("https://ntfy.sh", "topic", "Title", "Body")
    mock_client.post.assert_called_once_with(
        "https://ntfy.sh/topic",
        content="Body",
        headers={"Title": "Title"},
        timeout=5,
    )


@pytest.mark.asyncio
async def test_notify_ntfy_with_token():
    with patch("app.notifications.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        await _notify_ntfy(
            "https://ntfy.example.com", "alerts", "Title", "Body", token="secret-token"
        )
    _, kwargs = mock_client.post.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer secret-token"
    assert kwargs["headers"]["Title"] == "Title"


@pytest.mark.asyncio
async def test_notify_ntfy_without_token():
    with patch("app.notifications.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        await _notify_ntfy("https://ntfy.sh", "topic", "Title", "Body")
    _, kwargs = mock_client.post.call_args
    assert "Authorization" not in kwargs["headers"]


@pytest.mark.asyncio
async def test_notify_telegram_posts_to_api():
    with patch("app.notifications.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        await _notify_telegram("tok123", "chat456", "Hello")
    mock_client.post.assert_called_once_with(
        "https://api.telegram.org/bottok123/sendMessage",
        json={"chat_id": "chat456", "text": "Hello"},
        timeout=5,
    )


@pytest.mark.asyncio
async def test_send_notification_calls_ntfy_when_configured():
    with (
        patch("app.notifications._notify_ntfy", new_callable=AsyncMock) as mock_ntfy,
        patch("app.notifications._notify_telegram", new_callable=AsyncMock) as mock_tg,
    ):
        await send_notification(
            _settings(ntfy_url="https://ntfy.sh", ntfy_topic="mytopic"), "T", "M"
        )
    mock_ntfy.assert_called_once()
    mock_tg.assert_not_called()
    url, topic, title, msg, token = mock_ntfy.call_args[0]
    assert url == "https://ntfy.sh"
    assert topic == "mytopic"
    assert title == "T"
    assert "M" in msg
    assert "UTC" in msg
    assert token == ""


@pytest.mark.asyncio
async def test_send_notification_calls_ntfy_with_token_when_configured():
    with (
        patch("app.notifications._notify_ntfy", new_callable=AsyncMock) as mock_ntfy,
        patch("app.notifications._notify_telegram", new_callable=AsyncMock) as mock_tg,
    ):
        await send_notification(
            _settings(ntfy_url="https://ntfy.example.com", ntfy_topic="alerts", ntfy_token="tok"),
            "T",
            "M",
        )
    mock_ntfy.assert_called_once()
    mock_tg.assert_not_called()
    url, topic, _, _, token = mock_ntfy.call_args[0]
    assert url == "https://ntfy.example.com"
    assert topic == "alerts"
    assert token == "tok"


@pytest.mark.asyncio
async def test_send_notification_skips_ntfy_when_topic_missing():
    with (
        patch("app.notifications._notify_ntfy", new_callable=AsyncMock) as mock_ntfy,
        patch("app.notifications._notify_telegram", new_callable=AsyncMock) as mock_tg,
    ):
        await send_notification(_settings(ntfy_url="https://ntfy.sh"), "T", "M")
    mock_ntfy.assert_not_called()
    mock_tg.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_calls_telegram_when_configured():
    with (
        patch("app.notifications._notify_ntfy", new_callable=AsyncMock) as mock_ntfy,
        patch("app.notifications._notify_telegram", new_callable=AsyncMock) as mock_tg,
    ):
        await send_notification(
            _settings(telegram_bot_token="tok", telegram_chat_id="cid"), "T", "M"
        )
    mock_ntfy.assert_not_called()
    mock_tg.assert_called_once()
    token, chat_id, msg = mock_tg.call_args[0]
    assert token == "tok"
    assert chat_id == "cid"
    assert "T" in msg
    assert "M" in msg


@pytest.mark.asyncio
async def test_send_notification_calls_both_when_configured():
    with (
        patch("app.notifications._notify_ntfy", new_callable=AsyncMock) as mock_ntfy,
        patch("app.notifications._notify_telegram", new_callable=AsyncMock) as mock_tg,
    ):
        await send_notification(
            _settings(
                ntfy_url="https://ntfy.sh",
                ntfy_topic="x",
                telegram_bot_token="tok",
                telegram_chat_id="cid",
            ),
            "T",
            "M",
        )
    mock_ntfy.assert_called_once()
    mock_tg.assert_called_once()


@pytest.mark.asyncio
async def test_send_notification_silent_when_nothing_configured():
    with (
        patch("app.notifications._notify_ntfy", new_callable=AsyncMock) as mock_ntfy,
        patch("app.notifications._notify_telegram", new_callable=AsyncMock) as mock_tg,
    ):
        await send_notification(_settings(), "T", "M")
    mock_ntfy.assert_not_called()
    mock_tg.assert_not_called()


@pytest.mark.asyncio
async def test_send_notification_ntfy_exception_does_not_raise():
    with patch(
        "app.notifications._notify_ntfy",
        new_callable=AsyncMock,
        side_effect=Exception("network error"),
    ):
        await send_notification(_settings(ntfy_url="https://ntfy.sh", ntfy_topic="x"), "T", "M")


@pytest.mark.asyncio
async def test_send_notification_telegram_exception_does_not_raise():
    with patch(
        "app.notifications._notify_telegram",
        new_callable=AsyncMock,
        side_effect=Exception("timeout"),
    ):
        await send_notification(
            _settings(telegram_bot_token="tok", telegram_chat_id="cid"), "T", "M"
        )
