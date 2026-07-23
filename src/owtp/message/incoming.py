"Stores anything related to incoming messages from a Workshop mode."

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, TypeGuard, cast

from ...utils import EmptyData


@dataclass(frozen=True)
class MessageIn[T: Mapping[str, Any] = EmptyData]:
    "Incoming message from a Workshop mode."

    name: str
    data: T


class DefineMessageIn[T: Mapping[str, Any] = EmptyData](Protocol):
    "Helper for defining a type of an incoming message :class:`MessageIn`."

    name: str

    def __call__(self, data: T | None = None) -> MessageIn[T]: ...


def define_message_in[T: Mapping[str, Any] = EmptyData](
    name: str,
) -> DefineMessageIn[T]:
    "Incoming message :class:`MessageIn` creator."

    def creator(data: T | None = None) -> MessageIn[T]:
        final_data = data if data is not None else cast(T, {})
        return MessageIn(name, final_data)

    setattr(creator, "name", name)

    return cast(DefineMessageIn[T], creator)


def is_message_in[T: Mapping[str, Any]](
    message: MessageIn[Any], message_class: DefineMessageIn[T]
) -> TypeGuard[MessageIn[T]]:
    "Type guard for narrowing down a type of incoming message :class:`MessageIn` to a specified message class created by :func:`define_message_in`."
    return message.name == message_class.name
