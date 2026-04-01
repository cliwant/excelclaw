"""WhatsApp webhook verification and message routing."""
from __future__ import annotations

import logging
from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from app.config import settings
from app.whatsapp.models import IncomingMessage, parse_webhook_payload
from app.whatsapp import client as wa
from app.agent.excel_agent import handle_message

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["whatsapp"])

# Track processed message IDs to avoid duplicates (WhatsApp retries)
_seen_messages: set[str] = set()
_MAX_SEEN = 10_000


@router.get("")
async def verify(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
):
    """WhatsApp webhook verification (GET).

    Meta sends this when you register the webhook URL.
    Must return hub.challenge as plain text if token matches.
    """
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return PlainTextResponse(hub_challenge)
    logger.warning("Webhook verification failed: mode=%s", hub_mode)
    return PlainTextResponse("Forbidden", status_code=403)


@router.post("")
async def receive(request: Request):
    """Handle incoming WhatsApp messages (POST).

    Must return 200 quickly — Meta expects < 5s response.
    Heavy processing happens in background.
    """
    payload = await request.json()
    messages = parse_webhook_payload(payload)

    for msg in messages:
        # Deduplicate retries
        if msg.message_id in _seen_messages:
            continue

        logger.info("Received %s from %s: %s", msg.msg_type, msg.from_number, msg.text or msg.document_filename or "")

        # Mark as read (non-blocking, don't let it crash the handler)
        try:
            await wa.mark_read(msg.message_id)
        except Exception:
            logger.warning("Failed to mark message as read: %s", msg.message_id)

        # Only add to seen AFTER successful processing starts
        _seen_messages.add(msg.message_id)
        if len(_seen_messages) > _MAX_SEEN:
            _seen_messages.clear()

        # Route to agent
        await _route_message(msg)

    return {"status": "ok"}


async def _route_message(msg: IncomingMessage):
    """Route an incoming message to the appropriate handler."""
    try:
        if msg.msg_type == "document" and _is_excel(msg):
            await _handle_excel_upload(msg)
        elif msg.msg_type in ("text", "interactive"):
            await _handle_text(msg)
        else:
            await wa.send_text(
                msg.from_number,
                "I can help with Excel files! Send me an .xlsx file or ask me a question about a file you've already shared.",
            )
    except Exception:
        logger.exception("Error handling message %s", msg.message_id)
        await wa.send_text(
            msg.from_number,
            "Something went wrong processing your message. Please try again.",
        )


async def _handle_excel_upload(msg: IncomingMessage):
    """Download Excel file and start/update agent session."""
    # React to acknowledge receipt
    await wa.send_reaction(msg.from_number, msg.message_id, "\U0001f4ce")  # 📎

    # Download file
    dest = f"{settings.upload_dir}/{msg.from_number}/{msg.document_filename}"
    await wa.download_media(msg.document_id, dest)

    await wa.send_text(
        msg.from_number,
        f"Got your file *{msg.document_filename}*! Let me analyze it...",
    )

    # Process through agent
    response = await handle_message(
        user_id=msg.from_number,
        text=msg.text or f"I just uploaded {msg.document_filename}. Analyze this Excel file.",
        excel_path=dest,
    )
    await _send_agent_response(msg.from_number, response)


async def _handle_text(msg: IncomingMessage):
    """Forward text/button reply to the agent."""
    response = await handle_message(
        user_id=msg.from_number,
        text=msg.text or "",
    )
    await _send_agent_response(msg.from_number, response)


async def _send_agent_response(to: str, response: dict):
    """Send agent response back via WhatsApp.

    response format:
        {"text": "...", "buttons": [...], "file": "path/to/file.xlsx", "file_caption": "..."}
    """
    # Send file if present
    if response.get("file"):
        await wa.send_document(
            to,
            response["file"],
            caption=response.get("file_caption"),
        )

    # Send buttons if present
    if response.get("buttons"):
        await wa.send_buttons(to, response["text"], response["buttons"])
    elif response.get("text"):
        # WhatsApp text limit is 4096 chars — split if needed
        text = response["text"]
        while text:
            chunk, text = text[:4096], text[4096:]
            await wa.send_text(to, chunk)


def _is_excel(msg: IncomingMessage) -> bool:
    if msg.document_mime_type and "spreadsheet" in msg.document_mime_type:
        return True
    if msg.document_filename and msg.document_filename.lower().endswith((".xlsx", ".xls", ".csv")):
        return True
    return False
