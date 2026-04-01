"""ExcelClaw agent — processes user messages and Excel files via Claude."""
from __future__ import annotations

import json
import logging
from typing import Optional

import anthropic

from app.config import settings
from app.agent.prompts import SYSTEM_PROMPT, EXCEL_CONTEXT_TEMPLATE
from app.agent.excel_ops import summarize_excel, apply_actions
from app.agent.sessions import get_session, Session

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


async def handle_message(
    user_id: str,
    text: str,
    excel_path: Optional[str] = None,
) -> dict:
    """Process a user message and return a response dict.

    Args:
        user_id: WhatsApp phone number (used as session key)
        text: User's text message
        excel_path: Path to newly uploaded Excel file (if any)

    Returns:
        {"text": "...", "buttons": [...], "file": "path", "file_caption": "..."}
    """
    session = get_session(user_id)

    # If new Excel uploaded, analyze it and store in session
    if excel_path:
        summary = summarize_excel(excel_path)
        session.excel_path = excel_path
        session.excel_summary = summary

        excel_context = EXCEL_CONTEXT_TEMPLATE.format(
            filename=summary["filename"],
            sheet_summary=summary["sheet_summary"],
            data_preview=summary["data_preview"],
            preview_rows=5,
        )
        # Add as a system-like context message
        session.add_message("user", f"[Excel file uploaded]\n\n{excel_context}\n\nUser message: {text}")
    else:
        session.add_message("user", text)

    # Build messages for Claude
    messages = session.get_messages()

    client = _get_client()
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    raw_text = response.content[0].text
    session.add_message("assistant", raw_text)

    # Parse agent response
    return _parse_agent_response(raw_text, session)


def _parse_agent_response(raw: str, session: Session) -> dict:
    """Parse the agent's JSON response and apply any Excel actions."""
    result: dict = {"text": "", "buttons": None, "file": None, "file_caption": None}

    # Try to extract JSON from the response
    try:
        # Handle cases where Claude wraps JSON in markdown code blocks
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first and last lines (```json and ```)
            lines = [l for l in lines[1:] if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)

        parsed = json.loads(cleaned)
        result["text"] = parsed.get("text", raw)

        # Apply Excel actions if any
        actions = parsed.get("actions", [])
        if actions and session.excel_path:
            apply_actions(session.excel_path, actions)

            # Refresh summary after changes
            session.excel_summary = summarize_excel(session.excel_path)

        # Send file back if requested
        if parsed.get("send_file") and session.excel_path:
            result["file"] = session.excel_path
            result["file_caption"] = "Here's your updated file"

        # Buttons
        buttons = parsed.get("buttons")
        if buttons:
            result["buttons"] = [
                {"id": b["id"], "title": b["title"][:20]}
                for b in buttons[:3]
            ]

    except (json.JSONDecodeError, KeyError):
        # If Claude didn't return valid JSON, use raw text
        logger.debug("Agent response was not JSON, using raw text")
        result["text"] = raw

    return result
