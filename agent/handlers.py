import asyncio
import inspect
import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn

from .config import get_settings

logger = logging.getLogger(__name__)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


@dataclass
class SpeechHandler:
    session: Any
    tts_model: str | None
    max_text_length: int
    _lock: asyncio.Lock

    @classmethod
    def build(cls, session: Any) -> "SpeechHandler":
        settings = get_settings()
        return cls(
            session=session,
            tts_model=settings.tts_model,
            max_text_length=settings.max_text_length,
            _lock=asyncio.Lock(),
        )

    async def speak(self, text: str) -> None:
        if not text:
            return
        cleaned = text.strip()
        if not cleaned:
            return
        if len(cleaned) > self.max_text_length:
            logger.warning("Ignoring text longer than %s chars", self.max_text_length)
            return

        async with self._lock:
            try:
                await _maybe_await(self.session.interrupt())
            except Exception:
                logger.exception("Failed to interrupt existing speech")
            try:
                if self.tts_model:
                    await _maybe_await(self.session.say(cleaned, tts_model=self.tts_model))
                else:
                    await _maybe_await(self.session.say(cleaned))
                logger.info("Started speaking: %s", cleaned)
            except TypeError:
                await _maybe_await(self.session.say(cleaned))
                logger.info("Started speaking: %s", cleaned)


def _extract_text_from_payload(payload: bytes | str) -> tuple[str | None, bool]:
    if isinstance(payload, bytes):
        try:
            payload = payload.decode("utf-8")
        except Exception:
            return None, False
    payload = payload.strip()
    if not payload:
        return None, False
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return payload, False
    if isinstance(data, dict):
        if data.get("type") == "speak" and isinstance(data.get("text"), str):
            return data["text"], True
        if isinstance(data.get("text"), str):
            return data["text"], False
    if isinstance(data, str):
        return data, False
    return None, False


def _extract_text_from_event(*args: Any, **kwargs: Any) -> str | None:
    if "text" in kwargs and isinstance(kwargs["text"], str):
        return kwargs["text"]
    for arg in args:
        if isinstance(arg, str):
            return arg
        if hasattr(arg, "text") and isinstance(arg.text, str):
            return arg.text
        if hasattr(arg, "message") and isinstance(arg.message, str):
            return arg.message
    return None


def _register_text_stream(room: Any, callback: Callable[..., None]) -> None:
    for event_name in ("text_stream", "text_stream_received", "text_received"):
        try:
            room.on(event_name, callback)
            logger.info("Subscribed to text stream event '%s'", event_name)
            return
        except Exception:
            continue
    logger.info("Text stream events not available in this SDK")


def attach_livekit_handlers(room: Any, handler: SpeechHandler) -> None:
    def on_data_received(*args: Any, **kwargs: Any) -> None:
        topic = kwargs.get("topic")
        data = kwargs.get("data")
        if data is None and args:
            data = args[0]
        if topic is None and len(args) >= 4:
            topic = args[3]
        text, is_speak_type = _extract_text_from_payload(data)
        if not text:
            return
        if topic != "tts" and not is_speak_type:
            return
        if text:
            asyncio.create_task(handler.speak(text))

    def on_text_stream(*args: Any, **kwargs: Any) -> None:
        text = _extract_text_from_event(*args, **kwargs)
        if text:
            asyncio.create_task(handler.speak(text))

    try:
        room.on("data_received", on_data_received)
        logger.info("Subscribed to LiveKit data messages")
    except Exception:
        logger.exception("Failed to subscribe to data messages")

    _register_text_stream(room, on_text_stream)


class _SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


async def start_local_http_server(handler: SpeechHandler) -> None:
    settings = get_settings()
    app = FastAPI()

    @app.post("/speak")
    async def speak(request: _SpeakRequest) -> dict[str, bool]:
        asyncio.create_task(handler.speak(request.text))
        return {"ok": True}

    config = uvicorn.Config(
        app,
        host=settings.http_host,
        port=settings.http_port,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())
    logger.info("Agent HTTP fallback listening on http://%s:%s", settings.http_host, settings.http_port)
