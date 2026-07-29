import itertools
import os
from typing import Any, TypedDict

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


class EmptyData(TypedDict):
    pass


def empty_fn(*_: Any):
    return None


def flatten[T](arr: list[list[T]]) -> list[T]:
    return list(itertools.chain.from_iterable(arr))
