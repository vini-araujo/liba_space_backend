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
    tts_model: str


REQUIRED_ENV_VARS = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "AGENT_NAME",
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
        tts_model=os.getenv("TTS_MODEL", "cartesia/sonic-turbo"),
    )
