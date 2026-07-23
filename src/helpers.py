import os
from typing import Any, Callable, TypedDict, TypeGuard, cast

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class EventListener[**P]:
    def __init__(self):
        self._listeners: list[Callable[P, None]] = []

    def on(self, callback: Callable[P, None]):
        self._listeners.append(callback)

    def off(self, callback: Callable[P, None]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    def emit(self, *args: P.args, **kwargs: P.kwargs):
        for listener in self._listeners:
            listener(*args, **kwargs)


class EmptyData(TypedDict):
    pass


def empty_fn(*_: Any):
    return None


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
            key_value_pair_to_dict(item[1])
            if is_key_value_pair(item[1])
            else item[1]
        )

    return dictionary
