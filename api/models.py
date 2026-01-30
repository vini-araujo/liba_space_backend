from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    ok: bool


class ConfigResponse(BaseModel):
    livekit_url_present: bool
    livekit_api_key_present: bool
    livekit_api_secret_present: bool
    agent_name_present: bool
    tavus_key_present: bool
    tavus_replica_id_present: bool
    tavus_persona_id_present: bool


class SessionResponse(BaseModel):
    roomName: str
    livekitUrl: str
    token: str


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class SpeakResponse(BaseModel):
    ok: bool
