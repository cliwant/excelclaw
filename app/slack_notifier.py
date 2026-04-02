"""Forward WhatsApp conversations to a Slack channel as threads."""
from __future__ import annotations

import logging
import time
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_SLACK_POST_URL = "https://slack.com/api/chat.postMessage"

# Map phone -> (thread_ts, last_activity_time)
_active_threads: dict[str, tuple[str, float]] = {}
_SESSION_TIMEOUT = 3600  # 1 hour


def _get_thread_ts(phone: str) -> str | None:
    """Return existing thread_ts if session is still active, else None."""
    if phone in _active_threads:
        thread_ts, last_active = _active_threads[phone]
        if time.time() - last_active < _SESSION_TIMEOUT:
            return thread_ts
        del _active_threads[phone]
    return None


async def notify(direction: str, phone: str, text: str):
    """Post a message to the configured Slack channel.

    direction: 'user' for incoming, 'bot' for outgoing.
    Messages from the same phone within 1 hour are grouped in a thread.
    """
    if not settings.slack_bot_token or not settings.slack_channel_id:
        return

    if direction == "user":
        icon = ":bust_in_silhouette:"
        label = f"*[User {phone}]*"
    else:
        icon = ":robot_face:"
        label = f"*[ExcelClaw]*"

    thread_ts = _get_thread_ts(phone)

    try:
        async with httpx.AsyncClient() as client:
            if thread_ts is None:
                # Start a new thread with a session header
                header_resp = await client.post(
                    _SLACK_POST_URL,
                    headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
                    json={
                        "channel": settings.slack_channel_id,
                        "text": f":speech_balloon: *New session* — {phone}",
                        "unfurl_links": False,
                    },
                    timeout=5,
                )
                header_data = header_resp.json()
                if header_data.get("ok"):
                    thread_ts = header_data["ts"]
                    _active_threads[phone] = (thread_ts, time.time())
                else:
                    logger.warning("Slack error: %s", header_data.get("error"))
                    return

            # Post the actual message as a reply in the thread
            slack_text = f"{icon} {label}\n{text}"
            await client.post(
                _SLACK_POST_URL,
                headers={"Authorization": f"Bearer {settings.slack_bot_token}"},
                json={
                    "channel": settings.slack_channel_id,
                    "thread_ts": thread_ts,
                    "text": slack_text,
                    "unfurl_links": False,
                },
                timeout=5,
            )

            # Update last activity
            _active_threads[phone] = (thread_ts, time.time())
    except Exception:
        logger.warning("Failed to send Slack notification")
