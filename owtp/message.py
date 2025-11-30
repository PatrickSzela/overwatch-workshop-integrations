import json
from enum import Enum, StrEnum
from collections.abc import Callable
from .ascii import encode_ascii_string
from .message_structure import MessageDataType, MessageStructure
from typing import Any


class MessageState(Enum):
    NONE = 0
    SENDING = 1
    SENT = 2
    ERROR = 3


class MessageName(StrEnum):
    CONNECT = "OWTP_CONNECT"
    DISCONNECT = "OWTP_DISCONNECT"
    ERROR = "OWTP_ERROR"
    CONFIRM = "OWTP_CONFIRM"
    REGISTER_MESSAGE_STRUCTURE = "OWTP_REGISTER_MESSAGE_STRUCTURE"
    TRANSMISSION_READY = "OWTP_TRANSMISSION_READY"
    TRANSMISSION_NOT_READY = "OWTP_TRANSMISSION_NOT_READY"


class MessageData(StrEnum):
    MESSAGE_NAME = "OWTP_messageName"
    ERROR_CODE = "errorCode"
    PACKETS = "packets"
    REGISTER_MESSAGE_STRUCTURE_NAME = "name"
    REGISTER_MESSAGE_STRUCTURE_ID = "id"
    REGISTER_MESSAGE_STRUCTURE_DATA_TYPES = "dataTypes"
    REGISTER_MESSAGE_STRUCTURE_INTERACTIVE = "interactive"


class ErrorCode(StrEnum):
    INVALID_PACKET = "INVALID_PACKET"
    INVALID_MESSAGE = "INVALID_MESSAGE"
    TIMED_OUT = "TIMED_OUT"


class ReservedPackets(Enum):
    START_END_CONFIRM = 127
    COMMA = 126
    CONNECT = 125


class Message:
    def __init__(
        self,
        structure: MessageStructure,
        data: dict[str, Any] = {},
        number_of_attempts: int = 5,
        on_started_sending: Callable[[], None] | None = None,
        on_sent: Callable[[], None] | None = None,
        on_error: Callable[[], None] | None = None,
    ):
        self._structure = structure
        self._data = data
        self._number_of_attempts = number_of_attempts
        self._on_started_sending = on_started_sending
        self._on_sent = on_sent
        self._on_error = on_error

        self._packets = self._generate_packets(structure.id, data)
        self._state = MessageState.NONE

    @property
    def name(self):
        return self._structure.name

    @property
    def args(self):
        return self._data

    @property
    def arg_types(self):
        return self._structure.data_types

    @property
    def packets(self):
        return self._packets

    @property
    def number_of_attempts(self):
        return self._number_of_attempts

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value: MessageState):
        self._state = value

        match value:
            case MessageState.SENDING:
                if self._on_started_sending:
                    self._on_started_sending()
            case MessageState.SENT:
                if self._on_sent:
                    self._on_sent()
            case MessageState.ERROR:
                if self._on_error:
                    self._on_error()
            case _:
                pass

    def _generate_packets(self, id: list[int], data: dict[str, Any]):
        _data: list[Any] = []
        for name in self._structure.data_types:
            data_type = self._structure.data_types[name]
            value = data[name]

            if data_type == MessageDataType.VECTOR:
                value = [round(v, 3) for v in [value["x"], value["y"], value["z"]]]

            #  = self._structure.data_types[name]
            _data.append(value)

        data_packets: list[int] = []
        if len(_data):
            string = json.dumps(_data, separators=(",", ":"))[1:-1]
            data_packets = encode_ascii_string(string)

        checksum = encode_ascii_string(
            f"{sum(id + data_packets) + sum(range(1, len(id + data_packets) + 1))}"
        )

        # TODO: optional args
        # TODO: check if types are correct
        # TODO: convert object to array of key value pairs

        packets = [ReservedPackets.START_END_CONFIRM.value]
        packets += checksum
        packets.append(ReservedPackets.COMMA.value)

        packets += id

        if data_packets:
            packets.append(ReservedPackets.COMMA.value)
            packets += data_packets

        packets.append(ReservedPackets.START_END_CONFIRM.value)

        return packets
