import logging
import os
import uuid

from fastapi import FastAPI, HTTPException

from .config import get_settings
from .dispatch import dispatch_agent
from .livekit_send import send_text_to_room
from .livekit_tokens import mint_room_token
from .models import ConfigResponse, HealthResponse, SessionResponse, SpeakRequest, SpeakResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

settings = get_settings()

app = FastAPI(title="LiveKit + Tavus Prototype API")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(ok=True)


@app.get("/config", response_model=ConfigResponse)
async def config() -> ConfigResponse:
    return ConfigResponse(
        livekit_url_present=bool(os.getenv("LIVEKIT_URL")),
        livekit_api_key_present=bool(os.getenv("LIVEKIT_API_KEY")),
        livekit_api_secret_present=bool(os.getenv("LIVEKIT_API_SECRET")),
        agent_name_present=bool(os.getenv("AGENT_NAME")),
        tavus_key_present=bool(os.getenv("TAVUS_API_KEY")),
        tavus_replica_id_present=bool(os.getenv("TAVUS_REPLICA_ID")),
        tavus_persona_id_present=bool(os.getenv("TAVUS_PERSONA_ID")),
    )


@app.post("/session", response_model=SessionResponse)
async def create_session() -> SessionResponse:
    room_name = f"room-{uuid.uuid4().hex[:10]}"
    identity = f"user-{uuid.uuid4().hex[:12]}"

    try:
        await dispatch_agent(room_name)
    except Exception as exc:
        logger.exception("Failed to dispatch agent")
        raise HTTPException(status_code=500, detail="Failed to dispatch agent") from exc

    token = mint_room_token(room_name, identity=identity)
    return SessionResponse(roomName=room_name, livekitUrl=settings.livekit_url, token=token)


@app.post("/rooms/{room_name}/speak", response_model=SpeakResponse)
async def speak(room_name: str, request: SpeakRequest) -> SpeakResponse:
    try:
        await send_text_to_room(room_name, request.text)
    except Exception as exc:
        logger.exception("Failed to send speak text")
        raise HTTPException(status_code=500, detail="Failed to send speak text") from exc
    return SpeakResponse(ok=True)
