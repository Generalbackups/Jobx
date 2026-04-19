# backend/schemas/voice.py

from pydantic import BaseModel
from typing import Optional, List, Any, Dict


class VoiceSessionStartRequest(BaseModel):
    user_id: str
    draft_posting_id: Optional[str] = None


class VoiceSessionStartResponse(BaseModel):
    room_name: str
    token: str
    session_id: str


class ConversationEntry(BaseModel):
    role: str    # "user" or "assistant"
    content: str


class VoiceSessionEndPayload(BaseModel):
    session_id: str
    job_data: Dict[str, Any]
    conversation_transcript: List[ConversationEntry] = []
