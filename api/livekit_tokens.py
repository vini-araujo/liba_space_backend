import uuid

from livekit import api

from .config import get_settings


def mint_room_token(room_name: str, identity: str | None = None) -> str:
    settings = get_settings()
    user_identity = identity or f"user-{uuid.uuid4().hex[:12]}"
    token = api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
    if hasattr(token, "with_identity"):
        token.with_identity(user_identity)
    else:
        try:
            token.identity = user_identity
        except Exception:
            pass

    video_grants = api.VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True,
    )
    if hasattr(token, "with_grants"):
        token.with_grants(video_grants)
    elif hasattr(token, "add_grant"):
        token.add_grant(video_grants)

    return token.to_jwt()
