import asyncio
import json
from collections.abc import Callable
from logger import create_logger
from inputs import input
from typing import Any, TypeGuard, cast
from .message import Message, MessageState, ReservedPackets, MessageName, MessageData
from .message_structure import MessageStructure, MessageDataType

logger = create_logger("OWTP")


DELAY_BETWEEN_DOWN_AND_UP_BUTTONS = 0.016 * 4
DELAY_BEFORE_NEXT_INPUTS = 0.016 * 2

MESSAGES = {
    "CONNECT": {
        "id": [
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value,
        ]
    },
    "TRANSMISSION_FINISHED": {
        "id": [
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value - 1,
        ],
    },
}

type Response = tuple[str, dict[str, Any], asyncio.Event]


def is_key_value_pair(data: Any) -> TypeGuard[list[tuple[str, Any]]]:
    if not isinstance(data, list):
        return False

    casted = cast(list[Any], data)

    return all(
        isinstance(item, list)
        and len(item) == 2  # type: ignore
        and isinstance(item[0], str)
        for item in casted
    )


def key_value_pair_to_dict(data: list[tuple[str, Any]]) -> dict[str, Any]:
    dictionary: dict[str, Any] = {}

    for item in data:
        dictionary[item[0]] = (
            key_value_pair_to_dict(item[1]) if is_key_value_pair(item[1]) else item[1]
        )

    return dictionary


class OWTP:
    def __init__(
        self,
        # TODO: types
        on_connect: Callable[[], None] | None,
        on_disconnect: Callable[[], None] | None,
        on_error: Callable[[], None] | None,
        on_log: Callable[[str], None] | None,
        on_message: Callable[[str, dict[str, Any]], None] | None,
        on_message_structure_registered: Callable[[MessageStructure], None] | None,
        on_message_started_sending: Callable[[Message], None] | None,
        on_message_sent: Callable[[Message], None] | None,
        on_message_error: Callable[[Message], None] | None,
    ):
        self._connected = False
        self._interactive = False
        self._registered_message_structures: dict[str, MessageStructure] = {}

        self._process_queues_stop_event: asyncio.Event = asyncio.Event()

        self._workshop_output_queue: asyncio.Queue[str] = asyncio.Queue()
        self._process_workshop_output_queue_task: asyncio.Task[Any] = (
            asyncio.create_task(self._process_workshop_output_queue())
        )

        self._messages_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._responses_queue: asyncio.Queue[Response] = asyncio.Queue()
        self._process_messages_pause_event: asyncio.Event = asyncio.Event()
        self._process_messages_queue_task: asyncio.Task[Any] = asyncio.create_task(
            self._process_messages_queue()
        )

        self._send_message_task: asyncio.Task[Any] | None = None

        if on_connect:
            self.on_connect = on_connect

        if on_disconnect:
            self.on_disconnect = on_disconnect

        if on_error:
            self.on_error = on_error

        if on_log:
            self.on_log = on_log

        if on_message:
            self.on_message = on_message

        if on_message_structure_registered:
            self.on_message_structure_registered = on_message_structure_registered

        if on_message_started_sending:
            self.on_message_started_sending = on_message_started_sending

        if on_message_sent:
            self.on_message_sent = on_message_sent

        if on_message_error:
            self.on_message_error = on_message_error

        for name in MESSAGES:
            self.register_message_structure(
                MessageStructure(name=name, id=MESSAGES[name]["id"])
            )

    @property
    def connected(self):
        return self._connected

    def _connect(self):
        if self._connected:
            logger.warning(
                "Tried connecting to the Workshop mode but we're already connected! Ignoring..."
            )
            return

        logger.info("Establishing connection with the Workshop mode...")

        def on_connected():
            self._connected = True
            logger.info("Established connection with the Workshop mode!")
            self.on_connect()

        def on_not_connected():
            self._connected = False
            logger.warning("Failed to establish connection with the Workshop mode!")
            self.on_error()

        self.send_message(
            name="CONNECT",
            number_of_attempts=5,
            on_sent=on_connected,
            on_error=on_not_connected,
        )

    def _disconnect(self):
        if not self._connected:
            logger.warning(
                "Tried disconnecting from the Workshop mode but we're not connected! Ignoring..."
            )
            return

        logger.info("Workshop mode requested disconnect...")
        self._connected = False

    def cleanup(self):
        if self._workshop_output_queue:
            self._workshop_output_queue.shutdown(True)

        if self._responses_queue:
            self._responses_queue.shutdown(True)

        if self._messages_queue:
            self._messages_queue.shutdown(True)

        if self._process_queues_stop_event:
            self._process_queues_stop_event.set()

        if self._send_message_task:
            self._send_message_task.cancel()

        if self._process_workshop_output_queue_task:
            self._process_workshop_output_queue_task.cancel()

        if self._process_messages_queue_task:
            self._process_messages_queue_task.cancel()

        self._registered_message_structures = {}

    def register_message_structure(self, data: MessageStructure):
        logger.info(
            f"Registering message structure `{data.name}`, id: {data.id}, data types: {data.data_types}"
        )
        self._registered_message_structures[data.name] = data
        self.on_message_structure_registered(data)

    def is_message_structure_registered(self, name: str):
        return name in self._registered_message_structures

    # region Events
    def on_connect(self):
        pass

    def on_disconnect(self):
        pass

    def on_error(self):
        pass

    def on_log(self, __log: str):
        pass

    def on_message(self, __name: str, __data: dict[str, Any]):
        # logger.warning(f"Unhandled message `{name}` with data `{data}`")
        pass

    def on_message_structure_registered(self, __structure: MessageStructure):
        pass

    def on_message_started_sending(self, __message: Message):
        pass

    def on_message_sent(self, __message: Message):
        pass

    def on_message_error(self, __message: Message):
        pass

    # endregion

    # region Queue & sending inputs
    def send_message(
        self,
        name: str,
        data: dict[str, Any] = {},
        number_of_attempts: int = 5,
        on_sent: Callable[[], None] | None = None,
        on_error: Callable[[], None] | None = None,
    ):
        if name not in self._registered_message_structures:
            raise Exception(f"Unknown message: {name}")

        message = Message(
            structure=self._registered_message_structures[name],
            data=data,
            number_of_attempts=number_of_attempts,
            on_sent=on_sent,
            on_error=on_error,
        )
        logger.debug(
            f"Adding to queue message `{message.name}` with data `{message.args}`, packets: {message.packets}"
        )
        self._messages_queue.put_nowait(message)

    def _retry_sending_message(self, errorCode: str):
        if self._send_message_task:
            self._send_message_task.cancel(errorCode)

    def pause_sending_messages(self, pause: bool):
        if pause and not self._process_messages_pause_event.is_set():
            self._process_messages_pause_event.set()
        elif not pause and self._process_messages_pause_event.is_set():
            self._process_messages_pause_event.clear()

    async def _process_messages_queue(self):
        fail_reason: str = ""

        while not self._process_queues_stop_event.is_set():
            message = await self._messages_queue.get()

            while self._process_messages_pause_event.is_set():
                await asyncio.sleep(0.1)

            logger.info(
                f"Starting sending message `{message.name}` with data `{message.args}`"
            )
            message.state = MessageState.SENDING
            self.on_message_started_sending(message)

            attempts = 0

            for i in range(message.number_of_attempts + 1):
                attempts = i
                if i >= message.number_of_attempts:
                    fail_reason = f"Giving up on message `{message.name}` after sending it {i} times!"
                    break

                if self._process_queues_stop_event.is_set():
                    fail_reason = f"Cancelling sending message `{message.name}` (try #{i + 1}) - received stop event"
                    break

                logger.debug(f"Sending message `{message.name}` (try #{i + 1})...")

                try:
                    self._send_message_task = asyncio.create_task(
                        self._send_message_logic(message)
                    )
                    await self._send_message_task
                    break
                except BaseException as e:
                    logger.warning(
                        f"Failed sending message `{message.name}` (try #{i + 1}): {repr(e)}"
                    )

            if fail_reason:
                logger.warning(fail_reason)
                message.state = MessageState.ERROR
                self.on_message_error(message)
            else:
                logger.info(
                    f"Command `{message.name}` has been successfully sent after {attempts + 1} tries"
                )

            self._messages_queue.task_done()

            if self._messages_queue.empty() and not fail_reason and self._interactive:
                if message.name != "TRANSMISSION_FINISHED":
                    self.send_message("TRANSMISSION_FINISHED")
                else:
                    self.pause_sending_messages(True)

    async def _send_message_logic(self, message: Message):
        # Phase 1 - sending packets
        await self._send_packets(message)
        logger.debug(
            f"Finished sending packets of message `{message.name}`, awaiting for confirmation..."
        )

        # # Phase 2 - awaiting for packets confirmation
        # await asyncio.wait_for(
        #     self._wait_for_response(
        #         name=MessageName.PACKETS_CONFIRMED.value,
        #         dataCondition=lambda data: data[MessageData.PACKETS.value]
        #         == message.packets,
        #     ),
        #     1.5,
        # )
        # logger.debug(
        #     f"All sent packets of message `{message.name}` were correct! Sending confirmation..."
        # )

        # # Phase 3 - sending confirmation
        # await self._send_confirmation(message)
        # logger.debug(f"Confirmation for message `{message.name}` sent")

        # Phase 4 - awaiting for confirmation received
        # await self._wait_for_response(name=MessageName.CONFIRMATION_RECEIVED.value)
        await asyncio.wait_for(
            self._wait_for_response(
                name=MessageName.CONFIRM.value,
            ),
            1.5,
        )

        # Finished
        message.state = MessageState.SENT
        self.on_message_sent(message)

    async def _send_packets(self, message: Message):
        for idx in range(len(message.packets)):
            await input.send_input(
                message.packets[idx], DELAY_BETWEEN_DOWN_AND_UP_BUTTONS
            )
            await asyncio.sleep(DELAY_BEFORE_NEXT_INPUTS)

    async def _send_confirmation(self, message: Message):
        for _ in range(2):
            await input.send_input(
                ReservedPackets.START_END_CONFIRM.value,
                DELAY_BETWEEN_DOWN_AND_UP_BUTTONS,
            )
            await asyncio.sleep(DELAY_BEFORE_NEXT_INPUTS)

    async def _wait_for_response(
        self,
        name: str,
        dataCondition: Callable[[dict[str, Any]], bool] = lambda _: True,
    ):
        while not self._process_queues_stop_event.is_set():
            _name, _data, event = await self._responses_queue.get()

            logger.debug(f"Handling response `{_name}` with data `{_data}`")

            is_ok = _name == name and dataCondition(_data)

            if not is_ok:
                # TODO: put back response to the queue for the other message to handle it? although technically that should never happen
                logger.warning(
                    f"Response of `{_name}` and data `{_data}` has been skipped, condition evaluation failed"
                )

            self._responses_queue.task_done()
            event.set()

            if is_ok:
                return

    async def _pass_response_and_wait(self, name: str, data: dict[str, Any]):
        if not self._responses_queue:
            logger.warning(f"Unable to pass response `{name}` with data `{data}`")
            return
        event = asyncio.Event()
        self._responses_queue.put_nowait((name, data, event))
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
                logger.error(
                    f"Caught exception while handling workshop output: {repr(e)}"
                )

            self._workshop_output_queue.task_done()

    async def _handle_workshop_output(self, line: str):
        try:
            line = line.split("] ", 1)[1]
            arr: list[Any] = json.loads(line)

            if not is_key_value_pair(arr):
                raise TypeError(f"{line} is not a key-value pair structure")

            data: dict[str, Any] = key_value_pair_to_dict(arr)
            name = data[MessageData.MESSAGE_NAME.value]
            del data[MessageData.MESSAGE_NAME.value]

            if not isinstance(name, str):
                raise TypeError(
                    f"Name of the message must be a string, but passed `{name}`"
                )
        except Exception:
            # logger.info(f"Unhandled Workshop output: {line}")
            self.on_log(line)
            return

        logger.debug(f"Received message `{name}` with data `{data}`")
        await self._handle_message_and_wait(name, data)

    async def _handle_message_and_wait(self, name: str, data: dict[str, Any]):
        match name:
            case MessageName.CONNECT.value:
                self._interactive = data[MessageData.REGISTER_MESSAGE_STRUCTURE_INTERACTIVE.value]
                self._connect()

            case MessageName.DISCONNECT.value:
                self._disconnect()

            case MessageName.REGISTER_MESSAGE_STRUCTURE.value:
                name, id, data_types = (
                    data[MessageData.REGISTER_MESSAGE_STRUCTURE_NAME.value],
                    data[MessageData.REGISTER_MESSAGE_STRUCTURE_ID.value],
                    data[MessageData.REGISTER_MESSAGE_STRUCTURE_DATA_TYPES.value],
                )

                structure = MessageStructure(
                    name=name,
                    id=id,
                    data_types={
                        key: MessageDataType(value) for key, value in data_types.items()
                    },
                )
                self.register_message_structure(structure)

            case MessageName.CONFIRM.value:
                await self._pass_response_and_wait(name, data)

            case MessageName.ERROR.value:
                self._retry_sending_message(data[MessageData.ERROR_CODE.value])

            case MessageName.TRANSMISSION_READY.value:
                self.pause_sending_messages(False)

            case MessageName.TRANSMISSION_NOT_READY.value:
                self.pause_sending_messages(True)

            case _:
                self.on_message(name, data)

    # endregion
