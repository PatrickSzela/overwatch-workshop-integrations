"Contains definitions for :class:`OWTP`'s internal messages."

from typing import Any, TypedDict

from .message import (
    DefineMessageIn,
    DefineMessageOut,
    MessageDataType,
    MessageName,
    ReservedPackets,
    define_message_in,
    define_message_out,
)


class SupportedMessageDefinition:
    "Definition of a message that Workshop mode supports and can receive."

    def __init__(
        self, name: str, id: list[int], dataTypes: dict[str, int] | None = None
    ):  # pylint: disable=W0622,C0103
        self.name = name
        self.id = id
        self.data_types = (
            {key: MessageDataType(value) for key, value in dataTypes.items()}
            if dataTypes
            else {}
        )


class ConnectMessageData(TypedDict):
    "Structure of `data` in incoming message :class:`ConnectResponse`."

    interactive: bool


class SupportsMessageData(TypedDict):
    "Structure of `data` in incoming message :class:`SupportsMessage`. Represents a message that a Workshop mode supports and can receive. Converted internally into :class:`SupportedMessage`."

    name: str
    id: list[int]
    dataTypes: dict[str, int]


class ErrorMessageData(TypedDict):
    errorCode: str
    packets: list[int]


ConnectResponse: DefineMessageOut = define_message_out(MessageName.CONNECT)
ConnectMessage: DefineMessageIn[ConnectMessageData] = define_message_in(
    MessageName.CONNECT
)
TransmissionFinishedMessage: DefineMessageOut = define_message_out(
    MessageName.TRANSMISSION_FINISHED
)
DisconnectMessage: DefineMessageIn = define_message_in(MessageName.DISCONNECT)
SupportsMessage: DefineMessageIn[SupportsMessageData] = define_message_in(
    MessageName.SUPPORTS_MESSAGE
)
ConfirmMessage: DefineMessageIn = define_message_in(MessageName.CONFIRM)
ErrorMessage: DefineMessageIn[ErrorMessageData] = define_message_in(
    MessageName.ERROR
)
TransmissionReadyMessage: DefineMessageIn = define_message_in(
    MessageName.TRANSMISSION_READY
)
TransmissionNotReadyMessage: DefineMessageIn = define_message_in(
    MessageName.TRANSMISSION_NOT_READY
)

MESSAGES_IN: list[DefineMessageIn[Any]] = [
    ConnectMessage,
    DisconnectMessage,
    SupportsMessage,
    ConfirmMessage,
    ErrorMessage,
    TransmissionReadyMessage,
    TransmissionNotReadyMessage,
]


MESSAGES_OUT: list[DefineMessageOut[Any]] = [
    ConnectResponse,
    TransmissionFinishedMessage,
]

SUPPORTED_MESSAGES = [
    SupportedMessageDefinition(
        name=MessageName.CONNECT,
        id=[
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value,
        ],
    ),
    SupportedMessageDefinition(
        name=MessageName.TRANSMISSION_FINISHED,
        id=[
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value,
            ReservedPackets.CONNECT.value - 1,
        ],
    ),
]
