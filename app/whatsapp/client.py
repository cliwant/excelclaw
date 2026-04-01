"""WhatsApp Cloud API client for sending messages."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_http = httpx.AsyncClient(timeout=30.0)


async def send_text(to: str, body: str) -> dict:
    """Send a plain text message."""
    return await _send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    })


async def send_document(to: str, document_path: str, caption: Optional[str] = None, filename: Optional[str] = None) -> dict:
    """Upload and send a document (e.g. updated Excel file)."""
    url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{settings.whatsapp_phone_number_id}/media"
    path = Path(document_path)

    # Step 1: upload media
    with open(path, "rb") as f:
        resp = await _http.post(
            url,
            headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
            files={"file": (path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            data={"messaging_product": "whatsapp"},
        )
    resp.raise_for_status()
    media_id = resp.json()["id"]

    # Step 2: send document message
    payload: dict = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {
            "id": media_id,
            "filename": filename or path.name,
        },
    }
    if caption:
        payload["document"]["caption"] = caption
    return await _send(payload)


async def send_buttons(to: str, body: str, buttons: list[dict[str, str]]) -> dict:
    """Send an interactive message with up to 3 buttons.

    Each button: {"id": "unique_id", "title": "Button Label"}
    """
    return await _send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": btn}
                    for btn in buttons[:3]  # WhatsApp max 3 buttons
                ],
            },
        },
    })


async def send_reaction(to: str, message_id: str, emoji: str) -> dict:
    """React to a message with an emoji (e.g. acknowledge file receipt)."""
    return await _send({
        "messaging_product": "whatsapp",
        "to": to,
        "type": "reaction",
        "reaction": {
            "message_id": message_id,
            "emoji": emoji,
        },
    })


async def mark_read(message_id: str) -> dict:
    """Mark a message as read (blue checkmarks)."""
    return await _send({
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    })


async def download_media(media_id: str, dest_path: str) -> str:
    """Download a media file (e.g. uploaded Excel) to dest_path.

    Returns the local file path.
    """
    # Step 1: get download URL
    url = f"https://graph.facebook.com/{settings.whatsapp_api_version}/{media_id}"
    resp = await _http.get(url, headers=_auth_headers())
    resp.raise_for_status()
    download_url = resp.json()["url"]

    # Step 2: download file
    resp = await _http.get(download_url, headers=_auth_headers())
    resp.raise_for_status()

    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(resp.content)

    logger.info("Downloaded media %s -> %s", media_id, dest_path)
    return dest_path


# ── internal ──

async def _send(payload: dict) -> dict:
    url = f"{settings.whatsapp_api_url}/messages"
    resp = await _http.post(url, json=payload, headers=_auth_headers())
    resp.raise_for_status()
    data = resp.json()
    logger.debug("WhatsApp API response: %s", data)
    return data


def _auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.whatsapp_token}"}
