import asyncio
import os
import platform

import keyboard as kbd
import mouse as ms  # type: ignore

from ..logging import create_logger
from .input import IInput


class KeyboardMouse(IInput):
    name = "keyboard_mouse"
    logger = create_logger("Input.kbd_mouse")
    keys = [
        "left ctrl",
        "left shift",
        "q",
        "mouse left",
        "z",
        "f",
        "e",
    ]

    @staticmethod
    async def is_supported():
        return platform.system() == "Windows" or (
            # on Linux running as root is required
            platform.system() == "Linux" and os.getuid() == 0
        )

    def _press_buttons(
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

    def create_task(self, keys: list[str], is_press: bool):
        keyboard: list[str] = []
        mouse: list[str] = []

        for key in keys:
            if key.startswith("mouse "):
                mouse.append(key.replace("mouse ", ""))
            else:
                keyboard.append(key)

        return asyncio.to_thread(self._press_buttons, keyboard, mouse, is_press)
