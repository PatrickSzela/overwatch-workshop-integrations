import os
from typing import Any, TypedDict

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)


class EmptyData(TypedDict):
    pass


def empty_fn(*_: Any):
    return None
