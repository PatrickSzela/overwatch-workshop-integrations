from abc import ABC, abstractmethod

# TODO: ensure overwatch window is focused


class IInput(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @staticmethod
    @abstractmethod
    def is_supported(self) -> bool:
        pass

    @abstractmethod
    async def send_input(self, input: int, held_time: float) -> None:
        pass
