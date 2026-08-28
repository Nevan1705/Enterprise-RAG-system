"""
================================================================================
Project     : Enterprise RAG System v3
Module      : backend/app/services/chat_store.py
Author      : Enterprise AI Engineering Team
Date        : 2026-08-28
Description : Thread-safe, JSON-persisted chat session memory store.
              Maintains full conversational transcripts with citations,
              provider metadata, timestamps, and multi-format export utilities
              (JSON and formatted plain-text TXT).
================================================================================
"""
import json
import os
import threading
from datetime import datetime
from typing import Optional

from app.core.config import settings
from app.core.logger import setup_logger

# Initialize module logger and reentrant lock
logger = setup_logger(__name__)
_lock = threading.RLock()
_sessions: dict[str, dict] = {}


# -----------------------------------------------------------------------------
# 1. State Persistence & Serialization
# -----------------------------------------------------------------------------
def _load() -> None:
    """Loads chat sessions from the persistent JSON file."""
    global _sessions
    p = settings.CHAT_STORE_PATH
    if not os.path.exists(p):
        return
    try:
        with open(p, "r", encoding="utf-8") as f:
            _sessions = json.load(f)
        logger.info(f"[CHAT] Loaded {len(_sessions)} historical sessions from disk")
    except Exception as e:
        logger.error(f"[CHAT] Session load failed: {e}")


def _save() -> None:
    """Atomically persists chat sessions to disk using a temporary file swap."""
    p = settings.CHAT_STORE_PATH
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(_sessions, f, indent=2)
    os.replace(tmp, p)


# Initialize memory on startup
_load()


# -----------------------------------------------------------------------------
# 2. Session Management & Append Operations
# -----------------------------------------------------------------------------
def get_or_create(session_id: str) -> dict:
    """
    Retrieves an existing conversation session or initializes a new one.
    """
    with _lock:
        if session_id not in _sessions:
            _sessions[session_id] = {
                "session_id": session_id,
                "created_at": datetime.utcnow().isoformat(),
                "messages": [],
            }
            _save()
        return _sessions[session_id]


def append(
    session_id: str,
    role: str,
    content: str,
    sources: Optional[list[str]] = None,
    doc_ids: Optional[list[str]] = None,
    chunks_used: Optional[int] = None,
    provider: Optional[str] = None,
) -> None:
    """
    Appends a new message entry with contextual metadata to the specified session.
    """
    with _lock:
        get_or_create(session_id)
        entry: dict = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
        }
        if sources is not None:
            entry["sources"] = sources
        if doc_ids is not None:
            entry["doc_ids"] = doc_ids
        if chunks_used is not None:
            entry["chunks_used"] = chunks_used
        if provider is not None:
            entry["provider"] = provider
            
        _sessions[session_id]["messages"].append(entry)
        _save()


def get(session_id: str) -> Optional[dict]:
    """Retrieves session dictionary if it exists."""
    return _sessions.get(session_id)


# -----------------------------------------------------------------------------
# 3. Export Formats (JSON & TXT)
# -----------------------------------------------------------------------------
def export_json(session_id: str) -> Optional[str]:
    """Serializes complete session data as formatted JSON."""
    s = _sessions.get(session_id)
    return json.dumps(s, indent=2) if s else None


def export_txt(session_id: str) -> Optional[str]:
    """Formats conversation transcript into human-readable text."""
    s = _sessions.get(session_id)
    if not s:
        return None
    lines = [
        "=========================================================================",
        "           ENTERPRISE RAG INTELLIGENCE PLATFORM — CHAT TRANSCRIPT         ",
        "=========================================================================",
        f"Session ID : {session_id}",
        f"Created At : {s.get('created_at', '')}",
        "=========================================================================",
        "",
    ]
    for m in s.get("messages", []):
        role = m.get("role", "?").upper()
        lines.append(f"[{m.get('timestamp', '')}] {role}:")
        lines.append(m.get("content", ""))
        if m.get("sources"):
            lines.append(f"  • Cited Sources : {', '.join(m['sources'])}")
        if m.get("provider"):
            lines.append(f"  • LLM Provider  : {m['provider']}")
        if m.get("chunks_used") is not None:
            lines.append(f"  • Chunks Used   : {m['chunks_used']}")
        lines.append("-" * 73)
        lines.append("")
    return "\n".join(lines)
