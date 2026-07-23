import asyncio
import json
from typing import TYPE_CHECKING, Any

from ..logging import create_logger
from ..utils import is_key_value_pair, key_value_pair_to_dict
from .message import MessageData

if TYPE_CHECKING:
    from .owtp import OWTP

logger = create_logger("OWTP.LogProcess")


class WorkshopLogProcessor:
    def __init__(self, owtp: "OWTP"):
        self._owtp = owtp
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._task = asyncio.create_task(self._process_queue())

    def cleanup(self):
        self._queue.shutdown(True)
        if self._task:
            self._task.cancel()

    def add_lines(self, lines: list[str]):
        for line in lines:
            self._queue.put_nowait(line)

    async def _process_queue(self):
        while not self._owtp._stop_event.is_set():  # pyright: ignore[reportPrivateUsage] # pylint: disable=W0212
            line = await self._queue.get()

            try:
                await self._handle_line(line)
            except BaseException as e:
                logger.error("Failed to handle Workshop output: %s", repr(e))

            self._queue.task_done()

    def parse_workshop_output(self, line: str) -> tuple[str, dict[str, Any]]:
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

    async def _handle_line(self, line: str):
        try:
            name, data = self.parse_workshop_output(line)
        except Exception:
            logger.info('Workshop log: "%s"', line)
            self._owtp.events.log.emit(line)
            return

        message_class = self._owtp.registered_messages_in.get(name)

        if not message_class:
            logger.warning('Unregistered message "%s" - skipping', name)
            return

        try:
            message = message_class(data)
        except Exception as e:
            logger.warning(
                'Failed to handle message "%s" (%s) - skipping', name, repr(e)
            )
            return

        logger.debug('Received message "%s" with data %s', name, data)
        await self._owtp._dispatch_message(message)  # pyright: ignore[reportPrivateUsage] # pylint: disable=W0212
