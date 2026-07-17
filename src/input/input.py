from abc import ABC, abstractmethod
from typing import ClassVar

# TODO: ensure overwatch window is focused


class IInput(ABC):
    name: ClassVar[str]

    @abstractmethod
    def __init__(self):
        pass

    @staticmethod
    @abstractmethod
    def is_supported() -> bool:
        pass

    @abstractmethod
    async def send_input(self, input: int, held_time: float) -> None:
        pass
