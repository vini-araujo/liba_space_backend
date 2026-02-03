import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    agent_name: str
    openai_api_key: str
    openai_tts_model: str
    openai_tts_voice: str
    tavus_api_key: str
    tavus_replica_id: str
    tavus_persona_id: str


REQUIRED_ENV_VARS = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "AGENT_NAME",
    "OPENAI_API_KEY",
    "TAVUS_API_KEY",
    "TAVUS_REPLICA_ID",
    "TAVUS_PERSONA_ID",
]


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        livekit_url=_require_env("LIVEKIT_URL"),
        livekit_api_key=_require_env("LIVEKIT_API_KEY"),
        livekit_api_secret=_require_env("LIVEKIT_API_SECRET"),
        agent_name=_require_env("AGENT_NAME"),
        openai_api_key=_require_env("OPENAI_API_KEY"),
        openai_tts_model=os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts"),
        openai_tts_voice=os.getenv("OPENAI_TTS_VOICE", "ash"),
        tavus_api_key=_require_env("TAVUS_API_KEY"),
        tavus_replica_id=_require_env("TAVUS_REPLICA_ID"),
        tavus_persona_id=_require_env("TAVUS_PERSONA_ID"),
    )
