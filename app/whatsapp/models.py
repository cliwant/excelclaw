"""Pydantic-free lightweight models for WhatsApp Cloud API webhook payloads."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class IncomingMessage:
    """Parsed representation of a single WhatsApp user message."""
    from_number: str          # sender phone number (e.g. "14155238886")
    message_id: str           # WhatsApp message ID
    timestamp: str
    msg_type: str             # "text", "document", "image", "interactive", ...
    text: Optional[str] = None
    # document fields
    document_id: Optional[str] = None
    document_filename: Optional[str] = None
    document_mime_type: Optional[str] = None
    # interactive reply
    button_reply_id: Optional[str] = None
    button_reply_title: Optional[str] = None


def parse_webhook_payload(payload: dict) -> list[IncomingMessage]:
    """Extract IncomingMessage list from a WhatsApp Cloud API webhook payload.

    Returns an empty list if the payload contains no user messages
    (e.g. status updates, delivery receipts).
    """
    messages: list[IncomingMessage] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for msg in value.get("messages", []):
                m = IncomingMessage(
                    from_number=msg["from"],
                    message_id=msg["id"],
                    timestamp=msg.get("timestamp", ""),
                    msg_type=msg["type"],
                )

                if msg["type"] == "text":
                    m.text = msg["text"]["body"]

                elif msg["type"] == "document":
                    doc = msg["document"]
                    m.document_id = doc.get("id")
                    m.document_filename = doc.get("filename")
                    m.document_mime_type = doc.get("mime_type")
                    m.text = doc.get("caption")  # optional caption

                elif msg["type"] == "interactive":
                    interactive = msg["interactive"]
                    if interactive["type"] == "button_reply":
                        reply = interactive["button_reply"]
                        m.button_reply_id = reply["id"]
                        m.button_reply_title = reply["title"]
                        m.text = reply["title"]

                messages.append(m)

    return messages
