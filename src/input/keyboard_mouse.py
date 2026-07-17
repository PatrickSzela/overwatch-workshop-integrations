import asyncio
import os
import platform

import keyboard as kbd
import mouse as ms  # type: ignore

from ..logging import create_logger
from .input import IInput

logger = create_logger("Input.keyboard_mouse")


class KeyboardMouse(IInput):
    name = "keyboard_mouse"
    __keys = [
        "left ctrl",
        "left shift",
        "q",
        "mouse left",
        "z",
        "f",
        "e",
    ]

    @staticmethod
    def is_supported():
        return platform.system() == "Windows" or (
            # on Linux running as root is required
            platform.system() == "Linux" and os.getuid() == 0
        )

    def _get_buttons(self, key: int) -> list[list[str]]:
        binary = bin(key)[2:][::-1]  # remove `0b` from beginning and reverse it
        keyboard: list[str] = []
        mouse: list[str] = []

        for idx, char in enumerate(binary):
            if char == "1":
                key_str = self.__keys[idx]
                if key_str.startswith("mouse "):
                    mouse.append(key_str.replace("mouse ", ""))
                else:
                    keyboard.append(key_str)

        return [keyboard, mouse]

    async def _press_buttons(
        self, keyboard: list[str], mouse: list[str], is_press: bool
    ):
        if is_press:
            for button in keyboard:
                kbd.press(button)

            for button in mouse:
                ms.press(button)
        else:
            for button in keyboard:
                kbd.release(button)

            for button in mouse:
                ms.release(button)

    async def send_input(self, input: int, held_time: float):
        keyboard, mouse = self._get_buttons(input)

        try:
            logger.debug("Pressing buttons: %s", input)
            await self._press_buttons(keyboard, mouse, True)
            await asyncio.sleep(held_time)
            logger.debug("Releasing buttons: %s", input)
            await self._press_buttons(keyboard, mouse, False)
        except BaseException as e:
            logger.warning(
                "Releasing buttons because of exception %s:", repr(e)
            )
            await self._press_buttons(keyboard, mouse, False)
            raise e
