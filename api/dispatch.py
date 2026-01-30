import asyncio
import logging
from typing import Any, Callable

from livekit import api as livekit_api

from .config import get_settings

logger = logging.getLogger(__name__)


def _resolve_service(api: Any) -> Any:
    for name in ("agent_dispatch", "agent", "agents"):
        service = getattr(api, name, None)
        if service is not None:
            return service
    return api


def _resolve_method(service: Any) -> Callable[..., Any] | None:
    method = getattr(service, "create_dispatch", None)
    if callable(method):
        return method
    for name in ("dispatch", "dispatch_agent", "start_agent"):
        candidate = getattr(service, name, None)
        if callable(candidate):
            return candidate
    return None


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


async def dispatch_agent(room_name: str) -> None:
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
            raise RuntimeError("LiveKit API client does not expose create_dispatch")

        request_cls = getattr(livekit_api, "CreateAgentDispatchRequest", None)
        if request_cls is None:
            request_cls = getattr(livekit_api, "AgentDispatchRequest", None)
        if request_cls is not None:
            request = request_cls(room=room_name, agent_name=settings.agent_name)
            await method(request)
        else:
            await method(room=room_name, agent_name=settings.agent_name)
        logger.info("Dispatched agent %s into room %s", settings.agent_name, room_name)
    finally:
        await _maybe_close(api)
