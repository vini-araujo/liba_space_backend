import asyncio
import logging
from typing import Any, Callable

from livekit import api as livekit_api

from .config import get_settings

logger = logging.getLogger(__name__)


def _resolve_service(api: Any) -> Any:
    for name in ("room", "room_service", "rooms"):
        service = getattr(api, name, None)
        if service is not None:
            return service
    return api


def _resolve_method(service: Any) -> Callable[..., Any] | None:
    for name in ("send_data", "send_data_packet", "send_data_to_room"):
        method = getattr(service, name, None)
        if callable(method):
            return method
    return None


def _data_kind() -> Any:
    kind = getattr(livekit_api, "DataPacketKind", None)
    if kind is None:
        return None
    return getattr(kind, "RELIABLE", None) or getattr(kind, "Reliable", None) or kind


async def _maybe_close(api: Any) -> None:
    close = getattr(api, "aclose", None)
    if callable(close):
        await close()
        return
    close = getattr(api, "close", None)
    if callable(close):
        result = close()
        if asyncio.iscoroutine(result):
            await result


async def send_text_to_room(room_name: str, text: str) -> None:
    settings = get_settings()
    api = livekit_api.LiveKitAPI(
        settings.livekit_url,
        settings.livekit_api_key,
        settings.livekit_api_secret,
    )
    try:
        service = _resolve_service(api)
        method = _resolve_method(service)
        if method is None:
            raise RuntimeError("LiveKit API client does not expose send_data")

        request_cls = getattr(livekit_api, "SendDataRequest", None)
        kind = _data_kind()
        data = text.encode("utf-8")
        if request_cls is not None:
            if kind is None:
                request = request_cls(room=room_name, data=data, topic="tts")
            else:
                request = request_cls(room=room_name, data=data, topic="tts", kind=kind)
            await method(request)
        else:
            kwargs = {"room": room_name, "data": data, "topic": "tts"}
            if kind is not None:
                kwargs["kind"] = kind
            await method(**kwargs)
        logger.info("Sent data packet to room %s", room_name)
    finally:
        await _maybe_close(api)
