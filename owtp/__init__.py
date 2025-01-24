import asyncio
import json
from collections.abc import Callable
from logger import create_logger
from inputs import input
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
}


def key_value_pair_to_dict(data: any):
    if isinstance(data, list) and len(data):
        if all(
            [
                isinstance(item, list) and len(item) == 2 and isinstance(item[0], str)
                for item in data
            ]
        ):
            dict = {}
            for item in data:
                dict[item[0]] = key_value_pair_to_dict(item[1])
            return dict
        else:
            return [key_value_pair_to_dict(item) for item in data]

    return data


class OWTP:
    def __init__(
        self,
        # TODO: types
        on_connect: Callable[[], None] = None,
        on_disconnect: Callable[[], None] = None,
        on_error: Callable[[], None] = None,
        on_log: Callable[[], None] = None,
        on_message: Callable[[], None] = None,
        on_message_structure_registered: Callable[[], None] = None,
        on_message_started_sending: Callable[[], None] = None,
        on_message_sent: Callable[[], None] = None,
        on_message_error: Callable[[], None] = None,
    ):
        self._connected = False
        self._registered_message_structures: dict[str, MessageStructure] = {}

        self._process_queues_stop_event: asyncio.Event = asyncio.Event()

        self._workshop_output_queue: asyncio.Queue = asyncio.Queue()
        self._process_workshop_output_queue_task: asyncio.Task = asyncio.create_task(
            self._process_workshop_output_queue()
        )

        self._messages_queue: asyncio.Queue = asyncio.Queue()
        self._responses_queue: asyncio.Queue = asyncio.Queue()
        self._process_messages_queue_task: asyncio.Task = asyncio.create_task(
            self._process_messages_queue()
        )

        self._send_message_task: asyncio.Task = None

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
            number_of_attempts=10,
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

    def on_log(self, log: str):
        pass

    def on_message(self, name: str, data: dict[str, any]):
        # logger.warning(f"Unhandled message `{name}` with data `{data}`")
        pass

    def on_message_structure_registered(self, structure: MessageStructure):
        pass

    def on_message_started_sending(self, message: Message):
        pass

    def on_message_sent(self, message: Message):
        pass

    def on_message_error(self, message: Message):
        pass

    # endregion

    # region Queue & sending inputs
    def send_message(
        self,
        name: str,
        data: dict[str, any] = {},
        number_of_attempts: int = 5,
        on_sent: Callable[[None], None] = None,
        on_error: Callable[[None], None] = None,
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
        self._send_message_task.cancel(errorCode)

    async def _process_messages_queue(self):
        fail_reason: str = None

        while not self._process_queues_stop_event.is_set():
            message = await self._messages_queue.get()

            if not isinstance(message, Message):
                raise TypeError(
                    "Item passed to the messages queue must be of `Message` type"
                )

            logger.info(f"Starting sending message `{message.name}` with data `{message.args}`")
            message.state = MessageState.SENDING
            self.on_message_started_sending(message)

            for attempt in range(message.number_of_attempts + 1):
                if attempt >= message.number_of_attempts:
                    fail_reason = f"Giving up on message `{message.name}` after sending it {attempt} times!"
                    break

                if self._process_queues_stop_event.is_set():
                    fail_reason = f"Cancelling sending message `{message.name}` (try #{attempt + 1}) - received stop event"
                    break

                logger.debug(
                    f"Sending message `{message.name}` (try #{attempt + 1})..."
                )

                try:
                    self._send_message_task = asyncio.create_task(
                        self._send_message_logic(message)
                    )
                    await self._send_message_task
                    break
                except BaseException as e:
                    logger.warning(
                        f"Failed sending message `{message.name}` (try #{attempt + 1}): {repr(e)}"
                    )

            if fail_reason:
                logger.warning(fail_reason)
                message.state = MessageState.ERROR
                self.on_message_error(message)
            else:
                logger.info(
                    f"Command `{message.name}` has been successfully sent after {attempt + 1} tries"
                )

            self._messages_queue.task_done()

    async def _send_message_logic(self, message: Message):
        # Phase 1 - sending packets
        await self._send_packets(message)
        logger.debug(
            f"Finished sending packets of message `{message.name}`, awaiting for confirmation..."
        )

        # Phase 2 - awaiting for packets confirmation
        await asyncio.wait_for(
            self._wait_for_response(
                name=MessageName.PACKETS_CONFIRMED.value,
                dataCondition=lambda data: data[MessageData.PACKETS.value]
                == message.packets,
            ),
            1.5,
        )
        logger.debug(
            f"All sent packets of message `{message.name}` were correct! Sending confirmation..."
        )

        # Phase 3 - sending confirmation
        await self._send_confirmation(message)
        logger.debug(f"Confirmation for message `{message.name}` sent")

        # Phase 4 - awaiting for confirmation received
        await self._wait_for_response(name=MessageName.CONFIRMATION_RECEIVED.value)

        # Finished
        message.state = MessageState.SENT
        self.on_message_sent(message)

    async def _send_packets(self, message: Message):
        for idx in range(len(message._packets)):
            await input.send_input(
                message._packets[idx], DELAY_BETWEEN_DOWN_AND_UP_BUTTONS
            )
            await asyncio.sleep(DELAY_BEFORE_NEXT_INPUTS)

    async def _send_confirmation(self, message: Message):
        await input.send_input(
            ReservedPackets.START_END_CONFIRM.value, DELAY_BETWEEN_DOWN_AND_UP_BUTTONS
        )

    async def _wait_for_response(
        self,
        name: str,
        dataCondition: Callable[[dict[str, any]], bool] = lambda _: True,
    ):
        while not self._process_queues_stop_event.is_set():
            _name, _data, event = await self._responses_queue.get()

            logger.debug(f"Handling response `{_name}` with data `{_data}`")

            if not isinstance(event, asyncio.Event):
                raise Exception()

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

    async def _pass_response_and_wait(self, name: str, data: dict[str, any]):
        if not self._responses_queue:
            logger.warning(f"Unable to pass response `{name}` with data `{data}`")
            return
        event = asyncio.Event()
        self._responses_queue.put_nowait([name, data, event])
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
            arr: list[any] = json.loads(line)
            data: dict[str, any] = key_value_pair_to_dict(arr)
            name = data[MessageData.MESSAGE_NAME.value]
            del data[MessageData.MESSAGE_NAME.value]

            if not isinstance(name, str):
                raise TypeError(
                    f"Name of the message must be a string, but passed `{name}`"
                )
        except:
            # logger.info(f"Unhandled Workshop output: {line}")
            self.on_log(line)
            return

        logger.debug(f"Received message `{name}` with data `{data}`")
        await self._handle_message_and_wait(name, data)

    async def _handle_message_and_wait(self, name: str, data: dict[str, any]):
        match name:
            case MessageName.CONNECT.value:
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

            case (
                MessageName.PACKETS_CONFIRMED.value
                | MessageName.CONFIRMATION_RECEIVED.value
            ):
                await self._pass_response_and_wait(name, data)

            case MessageName.ERROR.value:
                self._retry_sending_message(data[MessageData.ERROR_CODE.value])

            case _:
                self.on_message(name, data)

    # endregion
