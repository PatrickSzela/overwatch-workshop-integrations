"""Module for a wrapper around REST part of YouTube API v3"""

import json
from abc import ABC
from enum import StrEnum
from http import HTTPMethod
from typing import Any

import requests
from google.oauth2.credentials import Credentials

from src.logging import create_logger

from ..auth import refresh_credentials_if_necessary
from ..stream import YouTubeStream

logger = create_logger("YouTube.API.REST")


# import logging
# log = logging.getLogger("urllib3")
# log.setLevel(logging.DEBUG)

URL = "https://www.googleapis.com/youtube/v3"


class YouTubeRestEndpoint(StrEnum):
    """Enum of supported YouTube API v3 REST endpoints."""

    CHANNELS = "channels"
    PLAYLIST_ITEMS = "playlistItems"
    VIDEOS = "videos"
    LIVE_CHAT_MESSAGES = "liveChat/messages"


class YouTubeRestApi(ABC):
    """Wrapper around REST part of YouTube API v3"""

    _credentials: Credentials

    def _call(
        self,
        method: HTTPMethod,
        endpoint: YouTubeRestEndpoint,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ):
        """Call an `endpoint` with provided `params` and `body`."""

        refresh_credentials_if_necessary(self._credentials)

        response = requests.request(
            method=method.value,
            url=f"{URL}/{endpoint.value}",
            params=params,
            data=json.dumps(body) if body else None,
            headers={"Authorization": f"Bearer {self._credentials.token}"},
            timeout=3,
        )

        response.raise_for_status()

        return response.json()

    def get_channel_id_from_handle(self, handle: str):
        """
        Retrieve channel ID for channel with `handle`.
        """

        channels = self._call(
            method=HTTPMethod.GET,
            endpoint=YouTubeRestEndpoint.CHANNELS,
            params={"part": "id,snippet", "forHandle": handle},
        )

        match channels:
            case {"items": [{"id": str() as channel_id}, *_]}:
                return channel_id
            case _:
                raise RuntimeError(
                    f"Failed to find a channel for handle {handle}"
                )

    def get_live_stream_video_id(self, channel_id: str):
        """
        Retrieve video ID of latest live stream (running or not) in the "Live" tab for channel with ID `channel_id`.

        Since this retrieves items from the "Live" tab, it's only possible to retrieve public streams. Additionally, YouTube allows to run multiple live streams at the same time, but we only return the first stream found. Even with these restrictions, this should cover 99.9% of cases.

        In case this way stops working, there are 2 other (not implemented) ways of retrieving currently active live stream:
        - scrape `https://youtube.com/{handle}/live`,
        - use expensive `/search` endpoint.
        """

        playlist_items = self._call(
            method=HTTPMethod.GET,
            endpoint=YouTubeRestEndpoint.PLAYLIST_ITEMS,
            params={
                "part": "contentDetails",
                "playlistId": f"UULV{channel_id[2:]}",
            },
        )

        match playlist_items:
            case {
                "items": [
                    {"contentDetails": {"videoId": str() as video_id}},
                    *_,
                ]
            }:
                return video_id
            case _:
                raise RuntimeError(
                    f"Failed to retrieve ID of latest live stream for channel with ID {channel_id}"
                )

    def get_live_streams(self, video_ids: list[str]):
        """Generate `YouTubeStream` wrappers for specified video IDs `video_ids`."""

        streams: list[YouTubeStream] = []

        data = {
            "part": "snippet,liveStreamingDetails",
            "id": ",".join(video_ids),
        }

        videos = self._call(
            method=HTTPMethod.GET,
            endpoint=YouTubeRestEndpoint.VIDEOS,
            params=data,
        )

        items: Any

        match videos:
            case {"items": _items}:
                items = _items
            case _:
                raise RuntimeError(
                    f"Failed to retrieve details about videos {video_ids}"
                )

        for idx, item in enumerate(items):
            match item:
                case {
                    "snippet": {
                        "channelId": str() as channel_id,
                        "channelTitle": str() as channel_name,
                    },
                    "id": str() as video_id,
                    "liveStreamingDetails": {
                        "activeLiveChatId": str() as chat_id
                    },
                }:
                    stream = YouTubeStream(
                        channel_id=channel_id,
                        channel_name=channel_name,
                        video_id=video_id,
                        chat_id=chat_id,
                    )
                    streams.append(stream)

                case _:
                    raise RuntimeError(
                        f"Failed to generate YouTubeStream wrapper for video ID {video_ids[idx]} - video isn't a stream or stream is offline?"
                    )

        if len(streams) != len(video_ids):
            found_video_ids = [stream.video_id for stream in streams]
            diff = list(set(video_ids) - set(found_video_ids))
            raise RuntimeError(f"Unable to get chat IDs for streams: {diff}")

        return streams

    def send_message(
        self,
        streams: YouTubeStream | list[YouTubeStream],
        message: str,
    ):
        """Sends `message` in all provided `streams` chats."""

        if not isinstance(streams, list):
            streams = [streams]

        if len(message) > 200:
            logger.warning(
                'Message has exceeded the 200 character limit, slicing it: "%s"',
                message,
            )
            message = message[:200]

        for stream in streams:
            self._call(
                method=HTTPMethod.POST,
                endpoint=YouTubeRestEndpoint.LIVE_CHAT_MESSAGES,
                params={"part": "snippet"},
                body={
                    "snippet": {
                        "liveChatId": stream.chat_id,
                        "type": "textMessageEvent",
                        "textMessageDetails": {"messageText": message},
                    }
                },
            )
