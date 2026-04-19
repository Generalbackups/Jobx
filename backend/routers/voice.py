# backend/routers/voice.py

import uuid
import datetime
import logging
import os

from fastapi import APIRouter, HTTPException, Header, Depends

from livekit.api import (
    AccessToken,
    VideoGrants,
    RoomConfiguration,
    RoomAgentDispatch,
)

from backend.schemas.voice import (
    VoiceSessionStartRequest,
    VoiceSessionStartResponse,
    VoiceSessionEndPayload,
)
from backend.services.voice_session_store import (
    create_session,
    complete_session,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Environment variables ────────────────────────────────────────────────────
# These MUST be set. If they are not set, the endpoints will fail at runtime
# with a clear error rather than a cryptic downstream failure.

def _get_livekit_api_key() -> str:
    v = os.getenv("LIVEKIT_API_KEY")
    if not v:
        raise RuntimeError("LIVEKIT_API_KEY environment variable is not set.")
    return v

def _get_livekit_api_secret() -> str:
    v = os.getenv("LIVEKIT_API_SECRET")
    if not v:
        raise RuntimeError("LIVEKIT_API_SECRET environment variable is not set.")
    return v

def _get_internal_secret() -> str:
    v = os.getenv("INTERNAL_API_SECRET")
    if not v:
        raise RuntimeError("INTERNAL_API_SECRET environment variable is not set.")
    return v


# ── Helper: build the LiveKit JWT ────────────────────────────────────────────

def _build_livekit_token(
    user_id: str,
    room_name: str,
    session_id: str,
    draft_posting_id: str | None,
) -> str:
    """
    Build a signed LiveKit JWT access token.

    Key behaviors:
    - The token grants the recruiter (user_id as identity) permission to join
      the specific room (room_name).
    - The token embeds a RoomAgentDispatch config. When the frontend connects
      to the room using this token, LiveKit Cloud automatically dispatches
      the agent named "job-posting-agent" to the room. No separate API call
      to LiveKit's dispatch endpoint is needed.
    - The metadata JSON passed to the agent contains session_id, user_id, and
      draft_posting_id. The agent worker reads this on startup to initialize
      its session context.
    - Token TTL is 1 hour. After 1 hour the token cannot be used to join rooms.
    """
    import json

    metadata = json.dumps({
        "session_id": session_id,
        "user_id": user_id,
        "draft_posting_id": draft_posting_id,
    })

    token = (
        AccessToken(
            api_key=_get_livekit_api_key(),
            api_secret=_get_livekit_api_secret(),
        )
        .with_identity(user_id)
        .with_ttl(datetime.timedelta(hours=1))
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_room_config(
            RoomConfiguration(
                agents=[
                    RoomAgentDispatch(
                        agent_name="job-posting-agent",  # MUST match agent_name in agent_worker.py
                        metadata=metadata,
                    )
                ]
            )
        )
        .to_jwt()
    )
    return token


# ── Endpoint 1: Start Session ────────────────────────────────────────────────

@router.post("/start-session", response_model=VoiceSessionStartResponse)
async def start_voice_session(body: VoiceSessionStartRequest):
    """
    Called by the React frontend when the recruiter clicks "Start Voice Assistant".

    Steps:
    1. Generate a unique session_id and room_name.
    2. Build a signed LiveKit JWT with agent dispatch embedded.
    3. Store the session record in the session store (status: active).
    4. Return token, room_name, session_id to the frontend.

    The frontend uses the returned token to connect to the LiveKit room.
    LiveKit Cloud reads the RoomAgentDispatch in the token and automatically
    dispatches the agent worker to the room on first connection.
    """
    session_id = str(uuid.uuid4())
    room_name = f"job-posting-{session_id}"

    try:
        token = _build_livekit_token(
            user_id=body.user_id,
            room_name=room_name,
            session_id=session_id,
            draft_posting_id=body.draft_posting_id,
        )
    except RuntimeError as e:
        logger.error(f"Failed to build LiveKit token: {e}")
        raise HTTPException(status_code=500, detail="Voice session configuration error.")

    await create_session(
        session_id=session_id,
        user_id=body.user_id,
        room_name=room_name,
    )

    logger.info(f"Voice session created: session_id={session_id}, user_id={body.user_id}, room={room_name}")

    return VoiceSessionStartResponse(
        room_name=room_name,
        token=token,
        session_id=session_id,
    )


# ── Endpoint 2: End Session (Internal — Agent Only) ──────────────────────────

@router.post("/end-session")
async def end_voice_session(
    body: VoiceSessionEndPayload,
    x_internal_token: str = Header(default=None, alias="X-Internal-Token"),
):
    """
    Called ONLY by the Python agent worker process when a voice session completes.
    This is NOT called by the frontend.

    Security: Protected by the X-Internal-Token header. The value must match
    the INTERNAL_API_SECRET environment variable exactly. Requests without
    this header or with an incorrect value are rejected with 403 Forbidden.

    The agent sends this request AFTER publishing the session_complete
    DataChannel message to the frontend. This endpoint is a server-side
    audit record and backup — the frontend already has the data from
    the DataChannel message and does not need to poll this endpoint.
    """
    # ── Security check ──────────────────────────────────────────────────────
    # This block must not be removed or weakened. The endpoint receives
    # potentially sensitive job data and must only accept requests from
    # the trusted agent worker process.
    expected_secret = _get_internal_secret().strip()
    provided_secret = (x_internal_token or "").strip()

    if not provided_secret or provided_secret != expected_secret:
        logger.warning(
            f"Rejected /end-session request with invalid X-Internal-Token "
            f"for session_id={body.session_id}"
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    # ── Store the final job data ─────────────────────────────────────────────
    transcript_dicts = [entry.model_dump() for entry in body.conversation_transcript]
    record = await complete_session(
        session_id=body.session_id,
        job_data=body.job_data,
        conversation_transcript=transcript_dicts,
    )

    if record is None:
        # Session not found — agent may have sent an unknown session_id
        logger.error(f"end-session called for unknown session_id={body.session_id}")
        raise HTTPException(status_code=404, detail="Session not found.")

    logger.info(
        f"Voice session completed: session_id={body.session_id}, "
        f"fields_collected={len([v for v in body.job_data.values() if v])}"
    )

    return {"status": "ok"}
