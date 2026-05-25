import logging
from datetime import UTC, datetime

import httpx

logger = logging.getLogger(__name__)


async def _notify_ntfy(url: str, title: str, message: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(url, content=message, headers={"Title": title}, timeout=5)


async def _notify_telegram(bot_token: str, chat_id: str, message: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, json={"chat_id": chat_id, "text": message}, timeout=5)


async def send_notification(settings, title: str, message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    full_message = f"{message}\ntime={timestamp}"

    if settings.ntfy_url:
        try:
            await _notify_ntfy(settings.ntfy_url, title, full_message)
        except Exception:
            logger.exception("ntfy notification failed")

    if settings.telegram_bot_token and settings.telegram_chat_id:
        try:
            await _notify_telegram(
                settings.telegram_bot_token,
                settings.telegram_chat_id,
                f"[{title}] {full_message}",
            )
        except Exception:
            logger.exception("telegram notification failed")
