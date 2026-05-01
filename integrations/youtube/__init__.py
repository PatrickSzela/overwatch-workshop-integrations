from __future__ import annotations

import asyncio
from typing import Any

from logger import create_logger
from overwatch import GameState
from overwatch.integration import IIntegration

from .api.api import YouTubeApi
from .auth import authorize
from .stream import YouTubeStream

# Cloud Client library for YouTube isn't available (yet), and no wrapper exists that handles livestreams exists so this mess has to stay for now...
# https://docs.cloud.google.com/apis/docs/client-libraries-explained


logger = create_logger("YouTube")


BOT_TITLE = "Overwatch Stream Integration Bot"


class YouTubeIntegration(IIntegration):
    def __init__(self, channel_handles: set[str], video_ids: set[str]):
        super().__init__()

        # self._stream_id: str = stream_id
        self._youtube: YouTubeApi | None = None
        self._channel_handles: set[str] = channel_handles
        self._video_ids: set[str] = video_ids
        self._streams: list[YouTubeStream] = []
        self._loop = asyncio.get_event_loop()

    def cleanup(self):
        # this is hella ugly, but works
        if self._loop.is_closed():
            asyncio.run(self.cleanup_async())
        else:
            asyncio.run_coroutine_threadsafe(self.cleanup_async(), self._loop)

    async def cleanup_async(self):
        if self._youtube:
            await self._youtube.disconnect()
            self.send_message_in_chat(f"{BOT_TITLE}, signing off... o7")

    async def connect(self):
        self._youtube = YouTubeApi(authorize())
        self._youtube.on_message = self._on_message

        video_ids = self._video_ids

        for handle in self._channel_handles:
            handle = handle if handle.startswith("@") else f"@{handle}"

            try:
                channel_id = self._youtube.get_channel_id_from_handle(handle)
                video_id = self._youtube.get_live_stream_video_id(channel_id)
                video_ids.add(video_id)
            except BaseException as e:
                raise RuntimeError(
                    f"Failed to get an active stream for channel with handle {handle}"
                ) from e

        self._streams = self._youtube.get_live_streams(list(video_ids))

        await self._youtube.connect(self._streams)

        self.send_message_in_chat(f"{BOT_TITLE}, reporting for duty! o7")

    def send_message_in_chat(self, message: str):
        # return
        if self._youtube:
            self._youtube.send_message(self._streams, message)

    def _on_message(self, message: str, author: str, stream: YouTubeStream):
        logger.info("[%s] %s: %s", stream.channel_name, author, message)

    def on_message(self, name: str, data: dict[str, Any]):
        match name:
            # case "POLL_START":
            #     timeout, choices = data["timeout"], data["choices"]
            #     self.start_poll(choices=choices, timeout=timeout)

            # case "POLL_END":
            #     self.end_poll()

            # case "POLL_CANCEL":
            #     self.cancel_poll(data["reason"])

            case "SEND_MESSAGE":
                self.send_message_in_chat(data["message"])

            case _:
                pass

    def on_game_state_change(self, state: GameState):
        if not self.overwatch:
            raise RuntimeError("Missing Overwatch instance")

        match state:
            case GameState.STARTED:
                self.send_message_in_chat(
                    f"New game has started - {self.overwatch.mode} on {self.overwatch.map}"
                )
            case GameState.IN_PROGRESS:
                # self.send_message_in_chat_nowait("Game is in progress")
                pass
            case GameState.IN_BETWEEN_ROUNDS:
                # self.send_message_in_chat_nowait("Game is in between rounds")
                pass
            case GameState.FINISHED:
                self.send_message_in_chat("Game has been finished")
            # case GameState.CLOSED:
            #     self.cancel_poll("Lobby has been closed")
            # self.send_message_in_chat_nowait("Lobby has been closed")
            case _:
                pass
