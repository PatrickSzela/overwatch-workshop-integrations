import asyncio
import json
from collections.abc import Callable
from typing import Any, Mapping

from ..helpers import EventListener, is_key_value_pair, key_value_pair_to_dict
from ..input import IInput
from ..logging import create_logger
from . import SupportedMessageDefinition, messages
from .message import (
    DefineMessageIn,
    DefineMessageOut,
    MessageData,
    MessageIn,
    MessageName,
    MessageOut,
    MessageOutState,
    is_message_in,
    is_message_out,
)

logger = create_logger("OWTP")

TICK = 0.016
DELAY_BETWEEN_DOWN_AND_UP_BUTTONS = TICK * 4
DELAY_BEFORE_NEXT_INPUTS = TICK * 2


type Response = tuple[MessageIn, asyncio.Event]


class OWTPEvents:
    def __init__(self) -> None:
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
    ):
        self._connected = False
        self._interactive = False
        self._message_being_sent: MessageOut | None = None
        self._registered_supported_messages: dict[
            str, SupportedMessageDefinition
        ] = {}
        self._registered_messages_in: dict[str, DefineMessageIn[Any]] = {}

        self._process_queues_stop_event: asyncio.Event = asyncio.Event()

        self._workshop_output_queue: asyncio.Queue[str] = asyncio.Queue()
        self._process_workshop_output_queue_task: asyncio.Task[Any] = (
            asyncio.create_task(self._process_workshop_output_queue())
        )

        self._messages_queue: asyncio.Queue[MessageOut] = asyncio.Queue()
        # since asyncio Queue doesn't support removing items, let's do this the ugly way
        self._messages_queue_list: list[MessageOut] = []
        self._responses_queue: asyncio.Queue[Response] = asyncio.Queue()
        self._process_messages_pause_event: asyncio.Event = asyncio.Event()
        self._process_messages_cancel_event: asyncio.Event = asyncio.Event()
        self._process_messages_queue_task: asyncio.Task[Any] = (
            asyncio.create_task(self._process_messages_queue())
        )

        self._send_message_task: asyncio.Task[Any] | None = None

        self._input_method = input_method
        self.events = OWTPEvents()

        for message in messages.SUPPORTED_MESSAGES:
            self._register_supported_message(message)

        for message in messages.MESSAGES_IN:
            self.register_message_in(message)

    @property
    def connected(self):
        return self._connected

    def cleanup(self):
        self._workshop_output_queue.shutdown(True)
        self._responses_queue.shutdown(True)
        self._messages_queue.shutdown(True)
        self._process_queues_stop_event.set()

        for task in (
            self._send_message_task,
            self._process_workshop_output_queue_task,
            self._process_messages_queue_task,
        ):
            if task:
                task.cancel()

        self._registered_supported_messages = {}

    def _connect(self, message: MessageIn[messages.ConnectMessageData]):
        if self._connected:
            logger.warning(
                "Tried connecting to the Workshop mode but we're already connected! Ignoring..."
            )
            return

        self._interactive = message.data["interactive"]

        logger.info("Establishing connection with the Workshop mode...")

        def on_connected():
            self._connected = True
            logger.info("Successfully connected with the Workshop mode")
            self.events.connect.emit()

        def on_not_connected():
            self._connected = False
            logger.warning(
                "Failed to establish connection with the Workshop mode"
            )
            self.events.connect_error.emit()

        self.send_message(
            messages.ConnectResponse(
                number_of_attempts=5,
                on_finish=on_connected,
                on_error=on_not_connected,
            )
        )

    def _disconnect(self):
        if not self._connected:
            logger.warning(
                "Tried disconnecting from the Workshop mode but we're not connected! Ignoring..."
            )
            return

        logger.info("Workshop mode requested disconnect...")
        self.events.disconnect.emit()
        self._connected = False

    def _register_supported_message(self, data: SupportedMessageDefinition):
        logger.debug(
            'Registering supported message "%s", id: %s, data types: %s',
            data.name,
            data.id,
            data.data_types,
        )
        self._registered_supported_messages[data.name] = data
        self.events.register_supported_message.emit(data)

    def register_message_in(self, cls: DefineMessageIn):
        if cls.name in self._registered_messages_in:
            logger.warning(
                "Incoming message %s has already been registered!", cls.name
            )

        self._registered_messages_in[cls.name] = cls

    # region Queue & sending inputs
    def send_message(self, message: MessageOut):
        if message.name not in self._registered_supported_messages:
            raise RuntimeError(
                f"Cannot send message {message.name} - the Workshop mode hasn't reported that it supports it!"
            )

        message.prepare(self._registered_supported_messages[message.name])

        logger.debug(
            'Adding message "%s" with data %s to the queue',
            message.name,
            message.data,
        )

        self._messages_queue.put_nowait(message)
        self._messages_queue_list.append(message)

    def _retry_sending_message(self, error_code: str):
        if self._send_message_task:
            self._send_message_task.cancel(error_code)

    def _pause_sending_messages(self, pause: bool):
        if pause:
            self._process_messages_pause_event.set()
        else:
            self._process_messages_pause_event.clear()

    def remove_messages_of_type(self, message_type: DefineMessageOut[Any]):
        msg_list = self._messages_queue_list

        if self._message_being_sent:
            msg_list.append(self._message_being_sent)

        for msg in msg_list:
            if is_message_out(msg, message_type):
                self.remove_message(msg)

    def remove_message(self, message: MessageOut):
        if self._message_being_sent == message:
            self.cancel_sending_message()

        if message in self._messages_queue_list:
            self._messages_queue_list.remove(message)

    def cancel_sending_message(self):
        self._process_messages_cancel_event.set()

    async def _process_messages_queue(self):
        while not self._process_queues_stop_event.is_set():
            msg = await self._messages_queue.get()

            if msg not in self._messages_queue_list:
                continue

            self._message_being_sent = msg
            self._messages_queue_list.remove(msg)
            self._process_messages_cancel_event.clear()

            while self._process_messages_pause_event.is_set():
                await asyncio.sleep(0.1)

            logger.debug(
                'Starting sending message "%s" with data %s, packets: %s',
                msg.name,
                msg.data,
                msg.packets,
            )
            msg.state = MessageOutState.SENDING
            self.events.send_message_start.emit(msg)

            fail_reason = await self._send_with_retries(msg)

            if fail_reason:
                logger.warning(fail_reason)
                msg.state = MessageOutState.ERROR
                self.events.send_message_error.emit(msg, fail_reason)

            self._messages_queue.task_done()

            if (
                self._messages_queue.empty()
                and not fail_reason
                and self._interactive
            ):
                if msg.name != "TRANSMISSION_FINISHED":
                    self.send_message(messages.TransmissionFinishedMessage())
                else:
                    self._pause_sending_messages(True)

            self._message_being_sent = None

    async def _send_with_retries(self, message: MessageOut):
        for attempt in range(message.number_of_attempts):
            if self._process_queues_stop_event.is_set():
                return f'Cancelling sending message "{message.name}" (try #{attempt + 1}) - received stop event'

            if self._process_messages_cancel_event.is_set():
                return f'Cancelling sending message "{message.name}" (try #{attempt + 1}) - received cancel event'

            logger.info(
                'Sending message "%s" (try #%s)...', message.name, attempt + 1
            )

            try:
                self._send_message_task = asyncio.create_task(
                    self._send_and_confirm(message, attempt)
                )
                await self._send_message_task
                return
            except BaseException as e:
                logger.warning(
                    'Failed sending message "%s" (try #%s): %s',
                    message.name,
                    attempt + 1,
                    repr(e),
                )

            await asyncio.sleep(1.5)

        return f'Giving up on message "{message.name}" after sending it {message.number_of_attempts} times!'

    async def _send_and_confirm(self, message: MessageOut, attempt: int):
        for packet in message.packets:
            await self._input_method.send_input(
                packet, DELAY_BETWEEN_DOWN_AND_UP_BUTTONS
            )
            await asyncio.sleep(DELAY_BEFORE_NEXT_INPUTS)

        logger.debug(
            'Finished sending packets of message "%s", awaiting for confirmation...',
            message.name,
        )

        await asyncio.wait_for(
            self._wait_for_response(MessageName.CONFIRM.value),
            1.5,
        )

        logger.info(
            'Message "%s" has been successfully sent after %s tries',
            message.name,
            attempt + 1,
        )

        message.state = MessageOutState.SENT
        self.events.send_message_finish.emit(message)

    async def _wait_for_response(
        self,
        name: str,
        data_condition: Callable[[Mapping[str, Any]], bool] = lambda _: True,
    ):
        while not self._process_queues_stop_event.is_set():
            message, event = await self._responses_queue.get()

            logger.debug(
                'Handling response "%s" with data %s',
                message.name,
                message.data,
            )

            is_ok = message.name == name and data_condition(message.data)

            if not is_ok:
                # TODO: put back response to the queue for the other message to handle it? although technically that should never happen
                logger.warning(
                    'Response of "%s" and data %s has been skipped, condition evaluation failed',
                    message.name,
                    message.data,
                )

            self._responses_queue.task_done()
            event.set()

            if is_ok:
                return

    async def _pass_response_and_wait(self, message: MessageIn):
        event = asyncio.Event()
        self._responses_queue.put_nowait((message, event))
        await event.wait()

    # endregion

    # region Handle workshop output
    def add_workshop_output(self, lines: list[str]):
        for line in lines:
            self._workshop_output_queue.put_nowait(line)

    async def _process_workshop_output_queue(self):
        while not self._process_queues_stop_event.is_set():
            line = await self._workshop_output_queue.get()

            try:
                await self._handle_workshop_output(line)
            except BaseException as e:
                logger.error("Failed to handle Workshop output: %s", repr(e))

            self._workshop_output_queue.task_done()

    def _parse_workshop_output(self, line: str) -> tuple[str, dict[str, Any]]:
        payload = line.split("] ", 1)[1]
        arr: list[Any] = json.loads(payload)

        if not is_key_value_pair(arr):
            raise TypeError(
                f"The following Workshop output is not a key-value pair structure: {line}"
            )

        data: dict[str, Any] = key_value_pair_to_dict(arr)
        name = data.pop(MessageData.MESSAGE_NAME.value)

        if not isinstance(name, str):
            raise TypeError(
                f"Name of the message must be a string, but passed {name}"
            )

        return name, data

    async def _handle_workshop_output(self, line: str):
        try:
            name, data = self._parse_workshop_output(line)
        except Exception:
            logger.info('Workshop log: "%s"', line)
            self.events.log.emit(line)
            return

        message_class = self._registered_messages_in.get(name)
        if not message_class:
            logger.warning('Unregistered message "%s" - skipping', name)
            return

        try:
            message = message_class(data=data)
        except Exception as e:
            logger.warning(
                'Failed to handle message "%s" (%s) - skipping', name, repr(e)
            )
            return

        logger.debug('Received message "%s" with data %s', name, data)
        await self._dispatch_message(message)

    async def _dispatch_message(self, message: MessageIn):
        if is_message_in(message, messages.ConnectMessage):
            self._connect(message)
        elif is_message_in(message, messages.DisconnectMessage):
            self._disconnect()
        elif is_message_in(message, messages.SupportsMessage):
            self._register_supported_message(
                SupportedMessageDefinition(**message.data)
            )
        elif is_message_in(message, messages.ConfirmMessage):
            await self._pass_response_and_wait(message)
        elif is_message_in(message, messages.ErrorMessage):
            self._retry_sending_message(message.data["errorCode"])
        elif is_message_in(message, messages.TransmissionReadyMessage):
            self._pause_sending_messages(False)
        elif is_message_in(message, messages.TransmissionNotReadyMessage):
            self._pause_sending_messages(True)
        else:
            self.events.message.emit(message)

    # endregion
