import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Mapping

from ..input import IInput
from ..logging import create_logger
from ..utils import AsyncQueue
from . import messages
from .message import (
    DefineMessageOut,
    MessageIn,
    MessageName,
    MessageOut,
    MessageOutState,
    is_message_out,
)

if TYPE_CHECKING:
    from .owtp import OWTP

logger = create_logger("OWTP.MsgSender")

TICK = 0.016

type Response = tuple[MessageIn, asyncio.Event]


class MessageDispatcher:
    def __init__(
        self,
        owtp: "OWTP",
        input_method: IInput,
        buttons_down_ticks: int,
        buttons_up_ticks: int,
    ):
        self._owtp = owtp
        self._input_method = input_method
        self._buttons_down_ticks = buttons_down_ticks
        self._buttons_up_ticks = buttons_up_ticks

        self._currently_sent_message: MessageOut | None = None

        self._messages_queue: AsyncQueue[MessageOut] = AsyncQueue()
        self._responses_queue: asyncio.Queue[Response] = asyncio.Queue()

        self._pause_event = asyncio.Event()
        self._cancel_event = asyncio.Event()
        self._process_messages_task = asyncio.create_task(
            self._process_messages()
        )
        self._send_and_confirm_task: asyncio.Task[Any] | None = None

    def cleanup(self):
        self._responses_queue.shutdown(True)
        self._messages_queue.shutdown()

        if self._send_and_confirm_task:
            self._send_and_confirm_task.cancel()

        if self._process_messages_task:
            self._process_messages_task.cancel()

    def is_sending(self):
        return self._currently_sent_message is not None

    def _prepare_message(self, message: MessageOut):
        if message.name not in self._owtp.registered_supported_messages:
            raise RuntimeError(
                f"Cannot send message {message.name} - the Workshop mode hasn't reported that it supports it!"
            )

        message.prepare(self._owtp.registered_supported_messages[message.name])

    def put(self, message: MessageOut):
        self._prepare_message(message)

        logger.debug(
            'Adding message "%s" with data %s to the queue',
            message.name,
            message.data,
        )
        self._messages_queue.put_nowait(message, message.priority)

    def remove_of_type(self, message_type: DefineMessageOut[Any]):
        copy = self._messages_queue.items()

        if self._currently_sent_message:
            copy.append(self._currently_sent_message)

        for msg in copy:
            if is_message_out(msg, message_type):
                self.remove(msg)

    def remove_of_name(self, name: str):
        copy = self._messages_queue.items()

        if self._currently_sent_message:
            copy.append(self._currently_sent_message)

        for msg in copy:
            if msg.name == name:
                self.remove(msg)

    def remove(self, message: MessageOut):
        if self._currently_sent_message == message:
            self.cancel_current()

        if message in self._messages_queue.items():
            logger.debug(
                'Removing message "%s" with data %s from queue',
                message.name,
                message.data,
            )
            self._messages_queue.remove_nowait(message)

    def retry(self, error_code: str):
        if self._send_and_confirm_task:
            self._send_and_confirm_task.cancel(error_code)

    def is_paused(self):
        return self._pause_event.is_set()

    def pause(self, pause: bool):
        if pause:
            logger.debug(
                "Pausing transmission, %s messages left in queue",
                len(self._messages_queue.items()),
            )
            self._pause_event.set()
        else:
            logger.debug(
                "Resuming transmission, %s messages left in queue",
                len(self._messages_queue.items()),
            )
            self._pause_event.clear()

    def cancel_current(self):
        if self._currently_sent_message:
            logger.debug(
                'Cancelling currently sent message "%s"',
                self._currently_sent_message.name,
            )
            self._cancel_event.set()

    async def _pass_response_and_wait(self, message: MessageIn):
        event = asyncio.Event()
        self._responses_queue.put_nowait((message, event))
        await event.wait()

    async def _process_messages(self):
        while not self._owtp.is_stopped:
            while self._pause_event.is_set():
                await asyncio.sleep(0.1)

            message = await self._messages_queue.get()
            fail_reason = await self._send_message(message)

            self._messages_queue.task_done()

            if (
                self._messages_queue.empty()
                and not fail_reason
                and self._owtp._connection.interactive  # pyright: ignore[reportPrivateUsage] # pylint: disable=W0212
            ):
                if message.name != MessageName.TRANSMISSION_FINISHED:
                    self.put(messages.TransmissionFinishedMessage())
                else:
                    self.pause(True)

    async def _send_message(self, message: MessageOut):
        self._currently_sent_message = message
        self._cancel_event.clear()

        logger.debug(
            'Starting sending message "%s" with data %s, packets: %s',
            message.name,
            message.data,
            message.packets,
        )
        message.state = MessageOutState.SENDING
        self._owtp.events.send_message_start.emit(message)

        fail_reason = await self._send_with_retries(message)

        if fail_reason:
            logger.warning(fail_reason)
            message.state = MessageOutState.ERROR
            self._owtp.events.send_message_error.emit(message, fail_reason)

        self._currently_sent_message = None
        return fail_reason

    async def _send_with_retries(self, message: MessageOut):
        for attempt in range(message.number_of_attempts):
            if self._owtp.is_stopped:
                return f'Cancelling sending message "{message.name}" (try #{attempt + 1}) - received stop event'

            if self._cancel_event.is_set():
                return f'Cancelling sending message "{message.name}" (try #{attempt + 1}) - received cancel event'

            logger.info(
                'Sending message "%s" (try #%s)...', message.name, attempt + 1
            )

            try:
                self._send_and_confirm_task = asyncio.create_task(
                    self._send_and_confirm(message, attempt)
                )
                await self._send_and_confirm_task
                return None
            except BaseException as e:
                logger.warning(
                    'Failed sending message "%s" (try #%s): %s',
                    message.name,
                    attempt + 1,
                    repr(e),
                )

            if (
                self._send_and_confirm_task
                and not self._send_and_confirm_task.done()
            ):
                self._send_and_confirm_task.cancel()

            await asyncio.sleep(1.5)

        return f'Giving up on message "{message.name}" after sending it {message.number_of_attempts} times!'

    async def _send_and_confirm(self, message: MessageOut, attempt: int):
        for packet in message.packets:
            await self._input_method.send_input(
                packet, self._buttons_down_ticks * TICK
            )
            await asyncio.sleep(self._buttons_up_ticks * TICK)

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
        self._owtp.events.send_message_finish.emit(message)

    async def _wait_for_response(
        self,
        name: str,
        data_condition: Callable[[Mapping[str, Any]], bool] = lambda _: True,
    ):
        while not self._owtp.is_stopped:
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
