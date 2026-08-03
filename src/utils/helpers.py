import itertools
import os
from typing import Any, TypedDict

import tomllib

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

PYPROJECT_PATH = os.path.join(PROJECT_ROOT, "pyproject.toml")
PYPROJECT = tomllib.load(open(PYPROJECT_PATH, "rb"))


class EmptyData(TypedDict):
    pass


def empty_fn(*_: Any):
    return None


def flatten[T](arr: list[list[T]]) -> list[T]:
    return list(itertools.chain.from_iterable(arr))


def get_author():
    return PYPROJECT["tool"]["owi"]["author"]["name"]
