"""Helper for storing data about live stream."""

import dataclasses


@dataclasses.dataclass
class YouTubeStream:
    """Helper for storing data about live stream."""

    channel_id: str
    channel_name: str
    video_id: str
    chat_id: str
    chat_next_page_token: str | None = None
