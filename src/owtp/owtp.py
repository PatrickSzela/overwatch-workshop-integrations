import asyncio
from typing import Any

from ..input import IInput
from ..logging import create_logger
from ..utils import EventListener
from . import SupportedMessageDefinition, messages
from .connection import ConnectionManager
from .dispatcher import MessageDispatcher
from .log_processor import WorkshopLogProcessor
from .message import (
    DefineMessageIn,
    DefineMessageOut,
    MessageIn,
    MessageOut,
    is_message_in,
)

logger = create_logger("OWTP")


class OWTPEvents:
    def __init__(self):
        self.connect = EventListener[[]]()
        self.disconnect = EventListener[[]]()
        self.connect_error = EventListener[[]]()
        self.log = EventListener[[str]]()
        self.message = EventListener[[MessageIn]]()
        self.register_supported_message = EventListener[
            [SupportedMessageDefinition]
        ]()
        self.send_message_start = EventListener[[MessageOut]]()
        self.send_message_finish = EventListener[[MessageOut]]()
        self.send_message_error = EventListener[[MessageOut, str]]()


class OWTP:
    def __init__(
        self,
        input_method: IInput,
        buttons_down_ticks: int,
        buttons_up_ticks: int,
    ):
        self.events = OWTPEvents()

        self._stop_event = asyncio.Event()

        self._registered_supported_messages: dict[
            str, SupportedMessageDefinition
        ] = {}
        self._registered_messages_in: dict[str, DefineMessageIn[Any]] = {}

        self._connection = ConnectionManager(self)
        self._sender = MessageDispatcher(
            self, input_method, buttons_down_ticks, buttons_up_ticks
        )
        self._log_processor = WorkshopLogProcessor(self)

        for message in messages.SUPPORTED_MESSAGES:
            self._register_supported_message(message)

        for message in messages.MESSAGES_IN:
            self.register_message_in(message)

    def cleanup(self):
        self._stop_event.set()
        self._log_processor.cleanup()
        self._sender.cleanup()
        self._registered_supported_messages = {}

    @property
    def is_connected(self):
        return self._connection.connected

    @property
    def is_stopped(self):
        return self._stop_event.is_set()

    @property
    def registered_supported_messages(
        self,
    ):
        return self._registered_supported_messages

    @property
    def registered_messages_in(self):
        return self._registered_messages_in

    def pause(self, pause: bool):
        self._sender.pause(pause)

    def add_message(self, message: MessageOut):
        self._sender.put(message)

    def remove_message(self, message: MessageOut):
        self._sender.remove(message)

    def remove_messages_of_type(self, message_type: DefineMessageOut[Any]):
        self._sender.remove_of_type(message_type)

    def cancel_current_message(self):
        self._sender.cancel_current()

    def register_message_in(self, cls: DefineMessageIn):
        if cls.name in self._registered_messages_in:
            logger.warning(
                "Incoming message %s has already been registered!", cls.name
            )
        self._registered_messages_in[cls.name] = cls

    def add_workshop_output(self, lines: list[str]):
        self._log_processor.add_lines(lines)

    def _register_supported_message(self, data: SupportedMessageDefinition):
        logger.debug(
            'Registering supported message "%s", id: %s, data types: %s',
            data.name,
            data.id,
            data.data_types,
        )
        self._registered_supported_messages[data.name] = data
        self.events.register_supported_message.emit(data)

    async def _dispatch_message(self, message: MessageIn):
        if is_message_in(message, messages.ConnectMessage):
            self._connection.connect(message)
        elif is_message_in(message, messages.DisconnectMessage):
            self._connection.disconnect()
        elif is_message_in(message, messages.SupportsMessage):
            self._register_supported_message(
                SupportedMessageDefinition(**message.data)
            )
        elif is_message_in(message, messages.ConfirmMessage):
            await self._sender._pass_response_and_wait(message)  # pyright: ignore[reportPrivateUsage] # pylint: disable=W0212
        elif is_message_in(message, messages.ErrorMessage):
            self._sender.retry(message.data["errorCode"])
        elif is_message_in(message, messages.TransmissionReadyMessage):
            self.pause(False)
        elif is_message_in(message, messages.TransmissionNotReadyMessage):
            self.pause(True)
        else:
            self.events.message.emit(message)
