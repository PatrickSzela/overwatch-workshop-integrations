"""Module for a wrapper around gRPC part of YouTube API v3"""

import asyncio
from abc import ABC
from datetime import datetime, timezone
from typing import Callable, NoReturn, cast

import grpc
from google.oauth2.credentials import Credentials
from grpc.aio import Channel

from src.logging import create_logger

from ..auth import refresh_credentials_if_necessary
from ..stream import YouTubeStream
from .generated.stream_list_pb2 import (  # pylint: disable = no-name-in-module
    LiveChatMessageListRequest,
    LiveChatMessageListResponse,
)
from .generated.stream_list_pb2_grpc import V3DataLiveChatMessageServiceStub

logger = create_logger("YouTube.API.gRPC")

URL = "dns:///youtube.googleapis.com:443"


class YouTubeGrpcApi(ABC):
    """Wrapper around gRPC part of YouTube API v3"""

    _credentials: Credentials

    def __init__(self):
        self._connected = False
        self._loop = asyncio.get_running_loop()
        self._start_date = datetime.now().replace(tzinfo=timezone.utc)
        self._grpc_channel: Channel
        self._handle_messages_tasks: list[asyncio.Task[NoReturn]] = []
        self._stub: V3DataLiveChatMessageServiceStub
        self.on_message: Callable[[str, str, YouTubeStream], None] | None = None

    async def connect(self):
        """Establish gRPC connection to YouTube API"""

        creds = grpc.ssl_channel_credentials()
        self._grpc_channel = grpc.aio.secure_channel(URL, creds)

        await self._grpc_channel.channel_ready()

        self._connected = True
        self._stub = V3DataLiveChatMessageServiceStub(self._grpc_channel)

    async def disconnect(self):
        """Close gRPC connection"""
        self._connected = False

        for task in self._handle_messages_tasks:
            task.cancel()

        await self._grpc_channel.close()

    def is_connected(self):
        return self._connected

    async def join_chat(self, streams: list[YouTubeStream]):
        self._handle_messages_tasks = [
            self._loop.create_task(self._handle_messages(stream))
            for stream in streams
        ]

        await asyncio.gather(
            *(stream.chat_joined_event.wait() for stream in streams)
        )

    async def _handle_messages(self, stream: YouTubeStream):
        while True:
            request = LiveChatMessageListRequest(
                part=["snippet", "authorDetails"],
                live_chat_id=stream.chat_id,
                max_results=200,
                page_token=stream.chat_next_page_token,
            )

            refresh_credentials_if_necessary(self._credentials)
            metadata = (("authorization", "Bearer " + self._credentials.token),)  # type: ignore

            resp = cast(
                grpc.aio.UnaryStreamCall[
                    LiveChatMessageListRequest, LiveChatMessageListResponse
                ],
                self._stub.StreamList(request, metadata=metadata),
            )

            async for response in resp:
                for message in response.items:
                    author = message.author_details.display_name
                    text = message.snippet.display_message
                    date = datetime.fromisoformat(
                        message.snippet.published_at
                    ).replace(tzinfo=timezone.utc)

                    if date < self._start_date:
                        continue

                    if self.on_message:
                        self.on_message(text, author, stream)

                if not stream.chat_joined_event.is_set():
                    stream.chat_joined_event.set()

                stream.chat_next_page_token = response.next_page_token

                if not stream.chat_next_page_token:
                    break
