# agent/config.py

import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            f"Copy agent/.env.example to agent/.env and fill in all values."
        )
    return value


LIVEKIT_URL: str = _require("LIVEKIT_URL")
LIVEKIT_API_KEY: str = _require("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET: str = _require("LIVEKIT_API_SECRET")
DEEPGRAM_API_KEY: str = _require("DEEPGRAM_API_KEY")
GROQ_API_KEY: str = _require("GROQ_API_KEY")
CARTESIA_API_KEY: str = _require("CARTESIA_API_KEY")
INTERNAL_API_BASE_URL: str = _require("INTERNAL_API_BASE_URL")
INTERNAL_API_SECRET: str = _require("INTERNAL_API_SECRET")
