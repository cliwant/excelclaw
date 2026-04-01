"""In-memory session management for WhatsApp conversations.

Each WhatsApp phone number gets its own session with:
- Conversation history (for Claude context)
- Current Excel file path and summary
- Session metadata
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

# Max conversation turns to keep in context (to manage token usage)
MAX_HISTORY = 30

# Sessions expire after 24 hours of inactivity
SESSION_TTL = 24 * 60 * 60


@dataclass
class Session:
    user_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    messages: list[dict] = field(default_factory=list)
    excel_path: Optional[str] = None
    excel_summary: Optional[dict] = None

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})
        self.last_active = time.time()
        # Trim old messages but always keep the first (Excel context) if present
        if len(self.messages) > MAX_HISTORY:
            # Keep first message (may contain Excel context) + recent messages
            self.messages = [self.messages[0]] + self.messages[-(MAX_HISTORY - 1):]

    def get_messages(self) -> list[dict]:
        return list(self.messages)

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.last_active) > SESSION_TTL

    @property
    def has_excel(self) -> bool:
        return self.excel_path is not None


# ── Session store (in-memory for prototype, swap to Redis/DB for prod) ──

_sessions: dict[str, Session] = {}


def get_session(user_id: str) -> Session:
    """Get or create a session for a user."""
    session = _sessions.get(user_id)
    if session is None or session.is_expired:
        session = Session(user_id=user_id)
        _sessions[user_id] = session
    return session


def clear_session(user_id: str):
    """Remove a user's session."""
    _sessions.pop(user_id, None)


def active_session_count() -> int:
    """Return number of non-expired sessions."""
    _cleanup()
    return len(_sessions)


def _cleanup():
    """Remove expired sessions."""
    expired = [uid for uid, s in _sessions.items() if s.is_expired]
    for uid in expired:
        del _sessions[uid]
