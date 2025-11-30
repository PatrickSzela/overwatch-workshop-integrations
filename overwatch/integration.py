from enum import StrEnum
from typing import Any
from owtp.message import Message
from owtp.message_structure import MessageStructure
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from overwatch import Overwatch


class GameState(StrEnum):
    # TODO: add assembling heroes & in setup (how to handle control mode & competitive?)
    NONE = "NONE"
    STARTED = "GAME_STARTED"
    IN_PROGRESS = "GAME_IN_PROGRESS"
    IN_BETWEEN_ROUNDS = "GAME_IN_BETWEEN_ROUNDS"
    FINISHED = "GAME_FINISHED"
    CLOSED = "GAME_CLOSED"


class IIntegration:
    def __init__(self):
        self.__overwatch: "Overwatch | None"

    def cleanup(self):
        pass

    def update_integration(self, overwatch: "Overwatch | None"):
        self.__overwatch = overwatch

    @property
    def connection(self):
        if not self.__overwatch:
            return None
        return self.__overwatch.connection

    @property
    def overwatch(self):
        return self.__overwatch

    def on_connect(self):
        """Called when successfully connected to the Workshop mode"""
        pass

    def on_disconnect(self):
        """Called after Workshop mode has requested to disconnect"""
        pass

    def on_error(self):
        """Called when failed to connect to the Workshop mode"""
        pass

    def on_log(self, log: str):
        """Called when Workshop mode has used Log To Inspector, messages are excluded"""
        pass

    def on_message(self, name: str, data: dict[str, Any]):
        """Called when message has been received"""
        pass

    def on_message_structure_registered(self, structure: MessageStructure):
        """Called when a message structure has been registered"""
        pass

    def on_message_started_sending(self, message: Message):
        """Called when message is about to be sent"""
        pass

    def on_message_sent(self, message: Message):
        """Called when message was successfully sent"""
        pass

    def on_message_error(self, message: Message):
        """Called when failed to send message"""
        pass

    def on_game_state_change(self, state: GameState):
        """Called when game's state changes"""
        pass
