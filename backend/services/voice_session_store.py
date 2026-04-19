# backend/services/voice_session_store.py

import asyncio
from typing import Optional
from datetime import datetime, timezone


# In-memory store. Key: session_id (str), Value: session record dict.
# Replace with Redis in production for multi-process deployments.
_sessions: dict[str, dict] = {}
_lock = asyncio.Lock()


async def create_session(session_id: str, user_id: str, room_name: str) -> dict:
    """
    Create a new session record. Called when a recruiter starts a voice session.
    Returns the created record.
    """
    record = {
        "session_id": session_id,
        "user_id": user_id,
        "room_name": room_name,
        "status": "active",           # "active" | "complete" | "error"
        "job_data": None,             # populated by complete_session()
        "conversation_transcript": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }
    async with _lock:
        _sessions[session_id] = record
    return record


async def get_session(session_id: str) -> Optional[dict]:
    """
    Retrieve a session record by session_id.
    Returns None if session_id is not found.
    """
    return _sessions.get(session_id)


async def complete_session(
    session_id: str,
    job_data: dict,
    conversation_transcript: list,
) -> Optional[dict]:
    """
    Mark a session as complete and store the final job data.
    Called by the /api/voice/end-session endpoint when the agent POSTs results.
    Returns the updated record, or None if session_id is not found.
    """
    async with _lock:
        record = _sessions.get(session_id)
        if record is None:
            return None
        record["status"] = "complete"
        record["job_data"] = job_data
        record["conversation_transcript"] = conversation_transcript
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
    return record


async def get_session_job_data(session_id: str) -> Optional[dict]:
    """
    Convenience method: return only the job_data for a completed session.
    Returns None if session not found or not yet complete.
    """
    record = _sessions.get(session_id)
    if record is None or record["status"] != "complete":
        return None
    return record["job_data"]
