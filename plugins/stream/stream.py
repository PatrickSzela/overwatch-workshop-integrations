import asyncio
from abc import ABC, abstractmethod
from argparse import Namespace
from dataclasses import dataclass
from typing import Any, TypedDict

from src import (
    DefineMessageIn,
    EmptyData,
    EventListener,
    GameState,
    IPlugin,
    MessageIn,
    define_message_in,
    is_message_in,
)


class SendMessageData(TypedDict):
    message: str


SendMessage: DefineMessageIn[SendMessageData] = define_message_in(
    "SEND_MESSAGE"
)

BOT_NAME = "Overwatch Stream Integration Bot"


@dataclass
class ChatMessage:
    content: str
    user: str
    chatroom: str
    service: str


class StreamEvents:
    def __init__(self) -> None:
        self.message = EventListener[ChatMessage]()


class IStream(IPlugin, ABC):
    @abstractmethod
    def __init__(self, args: Namespace, config: Any):
        super().__init__(args, config)

        self._loop = asyncio.get_event_loop()
        self.events = StreamEvents()

    def incoming_messages(self) -> list[DefineMessageIn[Any]]:
        return [SendMessage]

    async def initialize(self, plugins: list[IPlugin]):
        if not self.is_connected():
            await self.connect()
            await self.send_message(f"{BOT_NAME}, reporting for duty! o7")

    async def cleanup(self):
        if self.is_connected():
            await self.send_message(f"{BOT_NAME}, signing off... o7")
            await self.disconnect()

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        return False

    @abstractmethod
    async def send_message(self, message: str):
        pass

    def send_message_nowait(self, message: str):
        asyncio.run_coroutine_threadsafe(self.send_message(message), self._loop)

    def on_message(self, message: str, user: str, chatroom: str):
        self.events.message.emit(
            ChatMessage(message, user, chatroom, self.name)
        )

    def on_workshop_connect(self):
        self.send_message_nowait(
            "Successfully established connection with the Workshop mode!"
        )

    def on_workshop_connect_error(self):
        self.send_message_nowait("Failed to connect with the Workshop mode!")

    def on_workshop_message(self, message: MessageIn[EmptyData]):
        if is_message_in(message, SendMessage):
            self.send_message_nowait(message.data["message"])

    def on_game_state_change(self, state: GameState):
        if not self.game:
            raise RuntimeError("Missing game instance")

        match state:
            case GameState.STARTED:
                self.send_message_nowait(
                    f"New game has started - {self.game.mode} on {self.game.map}"
                )
            # case GameState.IN_PROGRESS:
            #     self.send_message_nowait("Game is in progress")
            # case GameState.IN_BETWEEN_ROUNDS:
            #     self.send_message_nowait("Game is in between rounds")
            # case GameState.FINISHED:
            #     self.send_message_nowait("Game has been finished")
            # case GameState.CLOSED:
            #     self.send_message_nowait("Lobby has been closed")
            case _:
                pass
