import asyncio
import json
import logging
import sys
import time
from typing import Any

from livekit.agents import JobContext, WorkerOptions, cli
from livekit.agents.voice.agent import Agent
from livekit.agents.voice.agent_session import AgentSession

from .config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent")

MAX_TEXT_LENGTH = 500


def _participant_identity(room: Any) -> str | None:
    participant = getattr(room, "local_participant", None)
    identity = getattr(participant, "identity", None)
    if isinstance(identity, str):
        return identity
    return None


def _extract_text(payload: bytes | str) -> tuple[str | None, bool]:
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


def _now_ts() -> float:
    return time.time()


async def entrypoint(ctx: JobContext) -> None:
    settings = get_settings()
    await ctx.connect()
    identity = _participant_identity(ctx.room)
    logger.info("connected room=%s identity=%s", ctx.room.name, identity)

    session = AgentSession(tts=settings.tts_model)
    agent = Agent(instructions="You are a realtime TTS agent. Speak the provided text verbatim.")
    await session.start(agent=agent, room=ctx.room, record=False)

    speak_lock = asyncio.Lock()

    async def speak_text(text: str, received_at: float) -> None:
        cleaned = text.strip()
        if not cleaned:
            return
        if len(cleaned) > MAX_TEXT_LENGTH:
            logger.warning("Ignoring text longer than %s chars", MAX_TEXT_LENGTH)
            return
        logger.info("text received at %.3f: %s", received_at, cleaned)
        async with speak_lock:
            try:
                await session.interrupt()
            except Exception:
                logger.exception("Failed to interrupt current speech")
            logger.info("speaking started at %.3f", _now_ts())
            try:
                session.say(cleaned)
            except Exception:
                logger.exception("Failed to speak text")

    def on_data_received(*args: Any, **kwargs: Any) -> None:
        topic = kwargs.get("topic")
        data = kwargs.get("data")
        packet = kwargs.get("packet")
        if packet is not None and hasattr(packet, "data"):
            data = packet.data
            topic = topic or getattr(packet, "topic", None)
        if data is None and args:
            first = args[0]
            if hasattr(first, "data"):
                data = first.data
                topic = topic or getattr(first, "topic", None)
            else:
                data = first
        if topic is None and len(args) >= 4:
            topic = args[3]
        text, is_speak_type = _extract_text(data)
        if not text:
            return
        if topic != "tts" and not is_speak_type:
            return
        asyncio.create_task(speak_text(text, _now_ts()))

    try:
        ctx.room.on("data_received", on_data_received)
        logger.info("listening for LiveKit data messages")
    except Exception:
        logger.exception("failed to subscribe to data messages")

    waiters = [
        getattr(ctx, "wait_for_disconnect", None),
        getattr(ctx.room, "wait_for_disconnect", None),
    ]
    for waiter in waiters:
        if callable(waiter):
            await waiter()
            return
    await asyncio.Event().wait()


if __name__ == "__main__":
    settings = get_settings()
    if len(sys.argv) == 1:
        sys.argv.append("start")
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, agent_name=settings.agent_name))
