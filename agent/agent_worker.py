# agent/agent_worker.py
#
# Entry point for the LiveKit agent worker process.
# Run with: python agent_worker.py start
# This process must run alongside the FastAPI server (as a separate process or container).
# It does NOT import FastAPI and has no HTTP server of its own.

import asyncio
import json
import logging
from dotenv import load_dotenv

# Load .env from the agent/ directory itself.
# This must happen before any config imports.
load_dotenv()

from livekit import agents, rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    JobContext,
    TurnHandlingOptions,
)
from livekit.plugins import silero, groq
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# These imports will resolve once job_posting_agent.py and models.py are populated.
from job_posting_agent import JobPostingAgent
from models import JobPostingData

logger = logging.getLogger("agent_worker")
logging.basicConfig(level=logging.INFO)


# ── AgentServer setup ────────────────────────────────────────────────────────
# AgentServer registers this worker process with LiveKit Cloud.
# When the FastAPI backend creates a token with RoomAgentDispatch(agent_name="job-posting-agent"),
# LiveKit Cloud dispatches a job to this worker and calls the rtc_session handler below.

server = AgentServer()


# ── Prewarm: load Silero VAD model once at startup ───────────────────────────
# Silero VAD requires loading a model file. We do this once at worker startup
# (prewarm) so it is ready immediately when a session starts, rather than
# loading it on first use (which adds latency to the first session).

def prewarm(proc: agents.JobProcess):
    logger.info("Prewarming Silero VAD model...")
    proc.userdata["vad"] = silero.VAD.load()
    logger.info("Silero VAD model loaded.")


server.setup_fnc = prewarm


# ── RTC Session handler ───────────────────────────────────────────────────────
# This function is called by LiveKit once for each dispatched job (i.e. once per
# recruiter voice session). ctx.room is the LiveKit room the recruiter has joined.
# ctx.job.metadata contains the JSON string set by FastAPI in the access token.

@server.rtc_session(agent_name="job-posting-agent")
async def job_posting_session(ctx: JobContext):
    # ── Parse metadata from the access token ────────────────────────────────
    # FastAPI embeds {"session_id": "...", "user_id": "...", "draft_posting_id": "..."}
    # in the token. If metadata is missing or malformed, log and use defaults.
    try:
        metadata = json.loads(ctx.job.metadata) if ctx.job.metadata else {}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse job metadata — using empty defaults.")
        metadata = {}

    session_id = metadata.get("session_id", "unknown")
    user_id = metadata.get("user_id", "unknown")
    draft_posting_id = metadata.get("draft_posting_id")

    logger.info(
        f"Voice session started | session_id={session_id} | "
        f"user_id={user_id} | room={ctx.room.name}"
    )

    # ── Initialize userdata with session context ─────────────────────────────
    # JobPostingData is a plain Python dataclass (NOT Pydantic).
    # It is passed as `userdata` to AgentSession so all @function_tool methods
    # can read and write fields via `context.userdata`.
    initial_userdata = JobPostingData(
        session_id=session_id,
        recruiter_user_id=user_id,
    )

    # ── Build the AgentSession ───────────────────────────────────────────────
    # This wires together the STT → LLM → TTS → VAD pipeline.
    # Model setup:
    #   STT:  "deepgram/nova-3:en"
    #   LLM:  groq.LLM(model="llama-3.3-70b-versatile")
    #   TTS:  "cartesia/<model>:<voice_id>"
    #
    # IMPORTANT — Cartesia voice_id:
    # Replace the UUID below with a voice ID from https://app.cartesia.ai/voices
    # Pick a professional English voice. The format is:
    #   "cartesia/sonic-2024-10-19:<voice-uuid>"
    # The placeholder below will cause TTS to fail until replaced.
    CARTESIA_VOICE_STRING = "cartesia/sonic-3:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc"

    session = AgentSession[JobPostingData](
        userdata=initial_userdata,
        stt="deepgram/nova-3:en",
        llm=groq.LLM(model="llama-3.3-70b-versatile"),
        tts=CARTESIA_VOICE_STRING,
        vad=ctx.proc.userdata["vad"],
        turn_handling=TurnHandlingOptions(
            turn_detection=MultilingualModel(),
        ),
    )

    # ── Register DataChannel listener for messages FROM the frontend ─────────
    # The frontend sends {"type": "end_session"} when the recruiter clicks
    # "End Session". We handle it here by triggering the agent's finalize logic.
    # This must be registered BEFORE session.start() to avoid missing early messages.
    @ctx.room.on("data_received")
    def on_data_received(data_packet: rtc.DataPacket):
        try:
            message = json.loads(data_packet.data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Received non-JSON DataChannel message — ignoring.")
            return

        msg_type = message.get("type")
        logger.info(f"DataChannel message received | type={msg_type}")

        if msg_type == "end_session":
            # Schedule finalize_session on the event loop.
            # We cannot call the @function_tool directly from here; instead we
            # set a flag on the agent that on_enter's background task will check,
            # or we trigger a generate_reply with finalization instructions.
            # The cleanest approach: inject a user message that triggers the tool.
            asyncio.ensure_future(
                session.generate_reply(
                    instructions=(
                        "The recruiter has clicked the End Session button. "
                        "Immediately call the finalize_session tool to save all collected "
                        "data and close the session. Do not ask any more questions."
                    )
                )
            )

    # ── Start the session ────────────────────────────────────────────────────
    await session.start(
        room=ctx.room,
        agent=JobPostingAgent(),
    )

    # ── Connect to the room ──────────────────────────────────────────────────
    # ctx.connect() must be called AFTER session.start().
    # It joins the room as a participant and begins receiving/sending media.
    await ctx.connect()

    logger.info(f"Agent connected to room | session_id={session_id}")


# ── CLI entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    agents.cli.run_app(server)
