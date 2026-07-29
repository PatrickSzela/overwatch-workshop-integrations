import asyncio
from abc import ABC, abstractmethod
from logging import Logger
from typing import TYPE_CHECKING, Any, Awaitable, ClassVar, cast

from ..utils import flatten

if TYPE_CHECKING:
    from ..config import KeybindsConfig


class IInput(ABC):
    name: ClassVar[str]
    logger: Logger
    keys: list[list[Any]]
    key_map: dict[str, Any]
    key_order: list[str] = [
        "move_slow",
        "move_fast",
        "move_down",
        "spectate_lock_on",
        "disable_camera_blending",
        "modify_fov",
        "move_up",
    ]

    async def initialize(self):
        pass

    async def cleanup(self):
        pass

    def set_keys(self, keybinds: "KeybindsConfig") -> None:
        self.keys = []

        for key in self.key_order:
            keys = cast(str, keybinds[key]).split("+")

            for key in keys:
                if key not in self.key_map:
                    raise KeyError(f"Unknown key '{key}'")

            self.keys.append([self.key_map[key] for key in keys])

    def list_keys(self):
        return self.key_map.keys()

    @classmethod
    @abstractmethod
    async def is_supported(cls) -> bool | str:
        pass

    @abstractmethod
    def create_task(self, keys: list[Any], is_press: bool) -> Awaitable[Any]:
        pass

    async def _create_subprocess(self, command: str):
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            self.logger.warning(
                'Command "%s" failed with exit code %d, stderr: %s, stdout: %s',
                command,
                proc.returncode,
                stderr.decode().strip(),
                stdout.decode().strip(),
            )

    async def send_input(self, key: int, held_time: float) -> None:
        binary = bin(key)[2:][::-1]  # remove `0b` from beginning and reverse it
        keys = flatten(
            [self.keys[idx] for idx, char in enumerate(binary) if char == "1"]
        )

        press = self.create_task(keys, True)
        release = self.create_task(keys, False)

        try:
            self.logger.debug("Pressing buttons: %s", key)
            await press

            await asyncio.sleep(held_time)

            self.logger.debug("Releasing buttons: %s", key)
            await release
        except BaseException as e:
            self.logger.warning(
                "Releasing buttons because of exception: %s", repr(e)
            )
            await release
            raise e
