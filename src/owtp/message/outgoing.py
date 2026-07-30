"Stores anything related to outgoing messages from a Workshop mode."

import json
from collections.abc import Callable
from enum import Enum
from typing import TYPE_CHECKING, Any, Mapping, Protocol, TypeGuard, cast

from ...utils import EmptyData
from .alphabet import encode_string
from .types import TYPE_MAP, MessageDataType, Vector

if TYPE_CHECKING:
    from ..messages import SupportedMessageDefinition


class MessageOutState(Enum):
    "Possible states of the :class:`MessageOut`."

    NONE = 0
    SENDING = 1
    SENT = 2
    ERROR = 3


class ReservedPackets(Enum):
    "Packets reserved by `OWTP` that cannot be used by other means."

    START_END_CONFIRM = 127
    COMMA = 126
    CONNECT = 125


class MessageOut[T: Mapping[str, Any] = EmptyData]:
    def __init__(
        self,
        name: str,
        data: T,
        priority: int = 0,
        number_of_attempts: int = 5,
        is_keybind: bool = False,
        on_start: Callable[[], None] | None = None,
        on_finish: Callable[[], None] | None = None,
        on_error: Callable[[], None] | None = None,
    ):

        self.name = name
        self._data = data
        self._definition: SupportedMessageDefinition | None = None
        self._priority = priority
        self._number_of_attempts = number_of_attempts
        self._is_keybind = is_keybind
        self._on_start = on_start
        self._on_finish = on_finish
        self._on_error = on_error

        self._state = MessageOutState.NONE
        self._packets: list[int]

    @property
    def data(self):
        return self._data

    @property
    def packets(self):
        return self._packets

    @property
    def number_of_attempts(self):
        return self._number_of_attempts

    @property
    def state(self):
        return self._state

    @property
    def is_keybind(self):
        return self._is_keybind

    @property
    def priority(self):
        return self._priority

    @state.setter
    def state(self, value: MessageOutState):
        self._state = value

        match value:
            case MessageOutState.SENDING:
                if self._on_start:
                    self._on_start()
            case MessageOutState.SENT:
                if self._on_finish:
                    self._on_finish()
            case MessageOutState.ERROR:
                if self._on_error:
                    self._on_error()
            case _:
                pass

    def prepare(self, definition: SupportedMessageDefinition):
        prepared_data: list[Any] = []
        data_packets: list[int] = []
        packets: list[int] = []

        self._definition = definition

        if self._is_keybind:
            self._packets = definition.id
            return

        for name in definition.data_types:
            data_type = definition.data_types[name]
            value = self._data[name]

            if not isinstance(value, TYPE_MAP[data_type]):
                raise TypeError(
                    f"{self.name} data validation error: value {value} of key {name} is not of a type {data_type.name}"
                )

            if data_type == MessageDataType.VECTOR:
                vector: Vector = value
                value = [vector.x, vector.y, vector.z]

            prepared_data.append(value)

        if prepared_data:
            data_packets = encode_string(
                json.dumps(prepared_data, separators=(",", ":"))[1:-1]
            )

        checksum_list = definition.id + data_packets
        checksum = encode_string(
            f"{sum(checksum_list) + sum(range(1, len(checksum_list) + 1))}"
        )

        # TODO: optional args
        # TODO: automatically convert dict/class to array of key value pairs

        packets = [ReservedPackets.START_END_CONFIRM.value]
        packets += checksum
        packets.append(ReservedPackets.COMMA.value)

        packets += definition.id

        if data_packets:
            packets.append(ReservedPackets.COMMA.value)
            packets += data_packets

        packets.append(ReservedPackets.START_END_CONFIRM.value)

        self._packets = packets


class DefineMessageOut[T: Mapping[str, Any] = EmptyData](Protocol):
    name: str

    def __call__(
        self,
        data: T | None = None,
        number_of_attempts: int = 5,
        on_start: Callable[[], None] | None = None,
        on_finish: Callable[[], None] | None = None,
        on_error: Callable[[], None] | None = None,
    ) -> MessageOut[T]: ...


def define_message_out[T: Mapping[str, Any] = EmptyData](
    name: str,
    priority: int = 0,
    is_keybind: bool = False,
) -> DefineMessageOut[T]:
    def creator(
        data: T | None = None,
        number_of_attempts: int = 5,
        on_start: Callable[[], None] | None = None,
        on_finish: Callable[[], None] | None = None,
        on_error: Callable[[], None] | None = None,
    ) -> MessageOut[T]:
        return MessageOut(
            name,
            data if data is not None else cast(T, {}),
            priority,
            number_of_attempts,
            is_keybind,
            on_start,
            on_finish,
            on_error,
        )

    setattr(creator, "name", name)

    typed_creator = cast(DefineMessageOut[T], creator)
    return typed_creator


def is_message_out[T: Mapping[str, Any]](
    message: MessageOut[Any], message_class: DefineMessageOut[T]
) -> TypeGuard[MessageOut[T]]:
    "Type guard for narrowing down a type of outgoing message :class:`MessageOut` to a specified message class created by :func:`define_message_out`."
    return message.name == message_class.name
