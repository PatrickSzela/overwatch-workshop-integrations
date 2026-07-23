"""Helper for storing data about live stream."""

import asyncio
from dataclasses import dataclass, field


@dataclass
class YouTubeStream:
    """Helper for storing data about live stream."""

    channel_id: str
    channel_name: str
    video_id: str
    chat_id: str
    chat_next_page_token: str | None = None
    chat_joined_event: asyncio.Event = field(default_factory=asyncio.Event)
