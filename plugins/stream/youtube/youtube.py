import asyncio
from argparse import ArgumentParser, Namespace
from typing import Any, TypedDict

from src import create_logger

from ..stream import IStream
from .api import YouTubeApi
from .auth import authorize
from .stream import YouTubeStream

# Cloud Client library for YouTube isn't available (yet), and no wrapper exists that handles livestreams exists so this mess has to stay for now...
# https://docs.cloud.google.com/apis/docs/client-libraries-explained


logger = create_logger("YouTube")


class YouTubeConfig(TypedDict):
    secrets: dict[str, Any]


class YouTube(IStream):
    name = "YouTube"

    def __init__(
        self,
        args: Namespace,
        config: YouTubeConfig,
    ):
        super().__init__(args, config)

        self._config = config
        self._youtube: YouTubeApi | None = None
        self._streams: list[YouTubeStream] = []
        self._loop = asyncio.get_event_loop()
        self._channel_handles: set[str] = set(args.youtube_handle or [])
        self._video_ids: set[str] = set(args.youtube_video_id or [])

    @staticmethod
    def add_arguments(parser: ArgumentParser):
        IStream.add_arguments(parser)

        group = parser.add_argument_group("Chat integration - YouTube Live Stream")

        group.add_argument(
            "--yt",
            "--youtube",
            "--youtube-handle",
            help="channel handle (with or without @) of currently live channel to which the bot should join to",
            type=str,
            action="extend",
            nargs="+",
            dest="youtube_handle",
            metavar="HANDLE",
        )
        group.add_argument(
            "--yt-vid",
            "--youtube-video",
            "--youtube-video-id",
            help="video ID of live stream to which the bot should join to; you can retrieve the ID from live stream's URL",
            type=str,
            action="extend",
            nargs="+",
            dest="youtube_video_id",
            metavar="VIDEO_ID",
        )

    @staticmethod
    def config_structure():
        return YouTubeConfig

    @staticmethod
    def default_config():
        return YouTubeConfig(secrets={})

    async def connect(self):
        logger.info("Connecting to YouTube...")

        self._youtube = YouTubeApi(authorize(self._config["secrets"]))
        self._youtube.on_message = self._on_message

        video_ids = self._video_ids

        # TODO: parallelize this
        for handle in self._channel_handles:
            handle = handle if handle.startswith("@") else f"@{handle}"

            try:
                channel_id = await self._youtube.get_channel_id_from_handle(
                    handle
                )
                video_id = await self._youtube.get_live_stream_video_id(
                    channel_id
                )
                video_ids.add(video_id)
            except BaseException as e:
                raise RuntimeError(
                    f"Failed to get an active stream for channel with handle {handle} - if the stream is unlisted or private, provide video ID instead"
                ) from e

        self._streams = await self._youtube.get_live_streams(list(video_ids))

        await self._youtube.connect()
        logger.info("Successfully connected to YouTube")

        await self._youtube.join_chat(self._streams)
        logger.info(
            "Successfully joined channels: %s",
            [stream.channel_name for stream in self._streams],
        )

    async def disconnect(self):
        if self._youtube:
            await self._youtube.disconnect()

    def is_connected(self) -> bool:
        if self._youtube:
            return self._youtube.is_connected()

        return False

    async def send_message(self, message: str):
        if self.silent:
            return

        messages = message.split("\n")
        message = message.replace("\n", " ")
        logger.debug('Sending message in chat: "%s"', message)

        if self._youtube:
            try:
                for msg in messages:
                    await self._youtube.send_message(self._streams, msg)
            except BaseException as e:
                logger.warning("Failed to send message in chat: %s", repr(e))
        else:
            logger.warning(
                "Tried sending message in chat, but we're not connected to it!"
            )

    def _on_message(self, message: str, author: str, stream: YouTubeStream):
        # logger.info("[%s] %s: %s", stream.channel_name, author, message)
        self.on_message(message, author, stream.channel_name)
