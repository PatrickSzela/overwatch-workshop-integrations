"Stores :class:`IPlugin` interface."

from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from ..game import (
        DefineMessageIn,
        Game,
        GameState,
        MessageIn,
        MessageOut,
        SupportedMessageDefinition,
    )


class IPlugin(ABC):
    "Interface for plugin creation."

    name: ClassVar[str]
    always_enabled: ClassVar[bool] = False

    @abstractmethod
    def __init__(self, args: Namespace, config: Any | None):
        self.__game: Game | None = None

    @staticmethod
    def add_arguments(parser: ArgumentParser):
        "Registers arguments supported by the plugin."

    @staticmethod
    def config_structure() -> type[Any] | None:
        return None

    @staticmethod
    def default_config() -> Any | None:
        return None

    def incoming_messages(self) -> list[DefineMessageIn[Any]]:
        "List of incoming messages supported by the plugin."
        return []

    @property
    def game(self):
        "Reference to the current instance of :class:`Game`, if exists."
        return self.__game

    @game.setter
    def game(self, game: Game | None):
        self.__game = game

    @property
    def owtp(self):
        "Reference to the current instance of :class:`game.OWTP`, if exists."
        if not self.__game:
            return None

        return self.__game.connection

    async def initialize(self, plugins: list[IPlugin]):
        "Called when plugin's instance is being initialized."

    async def cleanup(self):
        "Called when plugin's instance is about to be destroyed."

    def on_workshop_connect(self):
        "Called when successfully connected to the Workshop mode."

    def on_workshop_connect_error(self):
        "Called when failed to connect to the Workshop mode."

    def on_workshop_disconnect(self):
        "Called after the Workshop mode has requested to disconnect."

    def on_workshop_log(self, log: str):
        "Called when Workshop mode has output something that isn't a :class:`Message` to the Workshop log file."

    def on_workshop_register_message(
        self, structure: SupportedMessageDefinition
    ):
        "Called when a message structure has been registered."

    def on_workshop_message(self, message: MessageIn):
        "Called when a message has been received from the Workshop mode."

    def on_workshop_send_message_start(self, message: MessageOut):
        "Called when message is about to be sent to the Workshop mode."

    def on_workshop_send_message_error(self, message: MessageOut, reason: str):
        "Called when failed to send message to the Workshop mode."

    def on_workshop_send_message_finish(self, message: MessageOut):
        "Called when message was successfully sent to the Workshop mode."

    def on_game_state_change(self, state: GameState):
        "Called when Custom Game's state changes."
