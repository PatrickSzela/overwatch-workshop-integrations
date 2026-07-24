import asyncio
from argparse import ArgumentParser, Namespace
from pathlib import PurePath
from typing import TypedDict

from twitchAPI.chat import Chat, EventData
from twitchAPI.chat import ChatMessage as TwChatMessage
from twitchAPI.oauth import UserAuthenticationStorageHelper
from twitchAPI.object.api import TwitchUser
from twitchAPI.twitch import Twitch as TwitchApi
from twitchAPI.type import AuthScope, ChatEvent

from src import PROJECT_ROOT, create_logger

from ..stream import IStream

logger = create_logger("Twitch")

TOKENS_PATH = PurePath(PROJECT_ROOT, "tokens_twitch.json")
USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]


class TwitchConfig(TypedDict):
    app_id: str
    app_secret: str


class Twitch(IStream):
    name = "Twitch"

    def __init__(
        self,
        args: Namespace,
        config: TwitchConfig,
    ):
        super().__init__(args, config)

        self._config = config
        self._channels: list[str] = list(set(args.twitch_channels))

        self._twitch: TwitchApi | None = None
        self._chat: Chat | None = None
        self._me: TwitchUser | None = None

        self._room_id_cache: dict[str, str] = {}

        self._loop = asyncio.get_event_loop()

    @staticmethod
    def add_arguments(parser: ArgumentParser):
        group = parser.add_argument_group("Twitch integration")

        group.add_argument(
            "--ttv",
            "--twitch",
            "--twitch-channels",
            help="channels to which the bot should join to",
            type=str,
            action="extend",
            nargs="+",
            dest="twitch_channels",
            metavar="CHANNEL",
        )

    @staticmethod
    def config_structure():
        return TwitchConfig

    @staticmethod
    def default_config():
        return TwitchConfig(app_id="", app_secret="")

    async def connect(self):
        logger.info("Connecting to Twitch...")

        self._twitch = await TwitchApi(
            self._config["app_id"], self._config["app_secret"]
        )
        helper = UserAuthenticationStorageHelper(
            self._twitch,
            USER_SCOPE,
            storage_path=TOKENS_PATH,
        )

        await helper.bind()

        users = self._twitch.get_users()
        me = anext(users)
        self._me = await me

        logger.info("Successfully connected to Twitch")

        self._chat = await Chat(self._twitch, no_shared_chat_messages=False)

        # self._chat.register_event(ChatEvent.READY, self._on_ready)
        self._chat.register_event(ChatEvent.MESSAGE, self._on_message)
        # self._chat.register_command("vote", self._on_vote)

        self._chat.start()
        not_joined: list[str] = await self._chat.join_room(self._channels)  # pyright: ignore[reportUnknownVariableType]

        if not_joined:
            raise RuntimeError(f"Failed to join channels: {not_joined}")

        logger.info("Successfully joined channels: %s", self._channels)

    async def disconnect(self):
        if self._chat and self._chat.is_connected():
            self._chat.stop()

        if self._twitch:
            await self._twitch.close()

    def is_connected(self) -> bool:
        if self._chat:
            return self._chat.is_connected()

        return False

    async def send_message(self, message: str):
        message = message.replace("\n", " ")
        logger.debug('Sending message in chat: "%s"', message)

        if self._chat and self._chat.is_connected():
            try:
                await asyncio.gather(
                    *(
                        self._chat.send_message(channel, f"/me {message}")
                        for channel in self._channels
                    )
                )
            except BaseException as e:
                logger.warning("Failed to send message in chat: %s", repr(e))
        else:
            logger.warning(
                "Tried sending message in chat, but we're not connected to it!"
            )

    # async def _on_ready(self, ready_event: EventData):
    #     await ready_event.chat.join_room(self._channel)
    #     logger.info("Joined %s's channel!", self._channel)

    async def _on_message(self, data: EventData):
        if not isinstance(data, TwChatMessage):
            return

        room_name = data.room.name if data.room else "???"

        # logger.info("[%s] %s: %s", room_name, data.user.name, data.text)
        self.on_message(data.text, data.user.name, room_name)
