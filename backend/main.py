from pathlib import Path

from fastapi import FastAPI
from dotenv import load_dotenv

# Load env vars explicitly so startup works no matter where uvicorn is launched from.
# Precedence: repo .env fills defaults, backend/.env overrides for backend runtime.
_BACKEND_DIR = Path(__file__).resolve().parent
_ROOT_ENV_FILE = _BACKEND_DIR.parent / ".env"
_BACKEND_ENV_FILE = _BACKEND_DIR / ".env"

if _ROOT_ENV_FILE.exists():
	load_dotenv(dotenv_path=_ROOT_ENV_FILE)

if _BACKEND_ENV_FILE.exists():
	load_dotenv(dotenv_path=_BACKEND_ENV_FILE, override=True)

app = FastAPI()
from backend.routers.voice import router as voice_router

app.include_router(voice_router, prefix="/api/voice", tags=["Voice AI"])
