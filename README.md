# JobAI

Voice AI Job Posting Assistant with:
1. FastAPI backend
2. LiveKit agent worker
3. React + Vite frontend

## Prerequisites

1. Python 3.11+
2. Node.js 20+
3. Git Bash (Windows)
4. Valid env files:
   1. `agent/.env`
   2. `backend/.env`
   3. `frontend/.env.local`

Use `.env.example` files as templates.

## One-time setup

```bash
cd /d/atom/jobai
python -m venv agent/.venv
source agent/.venv/Scripts/activate
pip install -r backend/requirements.txt
pip install -r agent/requirements.txt

cd /d/atom/jobai/frontend
npm install
```

## Run locally (3 terminals)

```bash
# Terminal 1: backend
cd /d/atom/jobai
source agent/.venv/Scripts/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

```bash
# Terminal 2: agent worker
cd /d/atom/jobai/agent
source .venv/Scripts/activate
python agent_worker.py start
```

```bash
# Terminal 3: frontend
cd /d/atom/jobai/frontend
npm start -- --host 127.0.0.1 --port 4180
```

If port `4180` is busy, Vite automatically uses the next available port.

## API smoke test

Run this after all 3 services are up:

```bash
curl -i -X POST http://127.0.0.1:4180/api/voice/start-session \
  -H "Content-Type: application/json" \
  -d '{"user_id":"browser_test_user"}'
```

Expected: `HTTP 200` with `room_name`, `token`, and `session_id`.

## Browser test

1. Open the frontend URL shown by Vite.
2. Click **Start Voice Assistant**.
3. Allow microphone access.
4. Confirm the agent responds in voice.
5. Confirm fields update in realtime while speaking.

## Notes

1. `Unchecked runtime.lastError` at page load is usually from a browser extension, not app logic.
2. `installHook.js` references come from React DevTools wrappers.
3. PyTorch is optional for your current flow. If you later hit explicit torch runtime errors:

```bash
cd /d/atom/jobai/agent
source .venv/Scripts/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

