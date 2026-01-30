# LiveKit + Tavus Backend Skeleton

Minimal backend skeleton for a realtime prototype. Includes LiveKit token minting, agent dispatch, data-message based text delivery, and low-latency TTS audio in the LiveKit room.

## Setup
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e .
cp .env.example .env
```
Fill in `.env` with your credentials. `AGENT_NAME` must match the worker. Set `TTS_MODEL` to a low-latency model supported by your provider.

## Run
Terminal A (agent worker):
```bash
uv run python -m agent.main
```

Terminal B (API service):
```bash
uv run uvicorn api.main:app --reload --port 8000
```

## Smoke tests
```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/session
```
Expected `/session` response includes `{ roomName, livekitUrl, token }`.

## Speak test (no frontend)
```bash
# 1) Create a session
curl -X POST http://localhost:8000/session

# 2) Send text to the agent
curl -X POST http://localhost:8000/rooms/<roomName>/speak \
  -H "Content-Type: application/json" \
  -d '{"text":"testing 1 2"}'
```
The agent logs should show text receipt and speaking timestamps, and audio should be audible in the LiveKit room.

## Env validation
If required environment variables are missing, the server will fail fast with a clear startup error.
