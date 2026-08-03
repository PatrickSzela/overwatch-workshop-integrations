import asyncio
from typing import Any

from ..input import IInput
from ..logging import create_logger
from ..utils import EventListener
from . import MessageDefinition, ModeInfo, messages
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
        self.mode_info = EventListener[[ModeInfo]]()
        self.connect = EventListener[[ModeInfo]]()
        self.disconnect = EventListener[[]]()
        self.connect_error = EventListener[[]]()
        self.log = EventListener[[str]]()
        self.message = EventListener[[MessageIn]]()
        self.register_message_definition = EventListener[[MessageDefinition]]()
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

        self._registered_msg_def: dict[str, MessageDefinition] = {}
        self._registered_msg_in: dict[str, DefineMessageIn[Any]] = {}

        self._connection = ConnectionManager(self)
        self._sender = MessageDispatcher(
            self, input_method, buttons_down_ticks, buttons_up_ticks
        )
        self._log_processor = WorkshopLogProcessor(self)

        for message in messages.MESSAGE_DEFINITIONS:
            self._register_message_definition(message)

        for message in messages.MESSAGES_IN:
            self.register_message_in(message)

    def cleanup(self):
        self._stop_event.set()
        self._log_processor.cleanup()
        self._sender.cleanup()
        self._registered_msg_def = {}

    @property
    def is_connected(self):
        return self._connection.connected

    @property
    def is_stopped(self):
        return self._stop_event.is_set()

    @property
    def registered_msg_def(self):
        return self._registered_msg_def

    @property
    def registered_messages_in(self):
        return self._registered_msg_in

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
        if cls.name in self._registered_msg_in:
            logger.warning(
                "Incoming message %s has already been registered!", cls.name
            )
        self._registered_msg_in[cls.name] = cls

    def add_workshop_output(self, lines: list[str]):
        self._log_processor.add_lines(lines)

    def _register_message_definition(self, data: MessageDefinition):
        logger.info(
            'Registering message definition "%s", id: %s, data types: %s',
            data.name,
            data.id,
            data.data_types,
        )
        self._registered_msg_def[data.name] = data
        self.events.register_message_definition.emit(data)

    async def _dispatch_message(self, message: MessageIn):
        if is_message_in(message, messages.ConnectMessage):
            self.events.mode_info.emit(message.data["mode"])
            self._connection.connect(message)
        elif is_message_in(message, messages.DisconnectMessage):
            self._connection.disconnect()
        elif is_message_in(message, messages.RegisterMessageDefinition):
            self._register_message_definition(MessageDefinition(**message.data))
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
