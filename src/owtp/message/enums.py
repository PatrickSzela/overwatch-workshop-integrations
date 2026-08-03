from enum import StrEnum


class MessageName(StrEnum):
    "Built-in names of supported message names."

    CONNECT = "OWTP_CONNECT"
    DISCONNECT = "OWTP_DISCONNECT"
    ERROR = "OWTP_ERROR"
    CONFIRM = "OWTP_CONFIRM"
    REGISTER_MESSAGE_DEFINITION = "OWTP_REGISTER_MESSAGE_DEFINITION"
    TRANSMISSION_READY = "OWTP_TRANSMISSION_READY"
    TRANSMISSION_NOT_READY = "OWTP_TRANSMISSION_NOT_READY"
    TRANSMISSION_FINISHED = "OWTP_TRANSMISSION_FINISHED"


class MessageData(StrEnum):
    "Built-in keys of `data` dictionary supported internally."

    MESSAGE_NAME = "OWTP_messageName"
    ERROR_CODE = "errorCode"
    PACKETS = "packets"
    REGISTER_MESSAGE_STRUCTURE_NAME = "name"
    REGISTER_MESSAGE_STRUCTURE_ID = "id"
    REGISTER_MESSAGE_STRUCTURE_DATA_TYPES = "dataTypes"
    REGISTER_MESSAGE_STRUCTURE_INTERACTIVE = "interactive"


class ErrorCode(StrEnum):
    "Error codes."

    INVALID_PACKET = "INVALID_PACKET"
    INVALID_MESSAGE = "INVALID_MESSAGE"
    TIMED_OUT = "TIMED_OUT"
