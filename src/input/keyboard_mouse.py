import asyncio
import platform

import keyboard as kbd
import mouse as ms  # type: ignore

from ..logging import create_logger
from .input import IInput
from .key_map.keyboard_mouse import KEY_MAP


class KeyboardMouse(IInput):
    name = "keyboard_mouse"
    logger = create_logger("Input.KbdMouse")
    key_map = KEY_MAP

    @classmethod
    async def is_supported(cls):
        if platform.system() != "Windows":
            return "not a Windows OS"

        return True

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
