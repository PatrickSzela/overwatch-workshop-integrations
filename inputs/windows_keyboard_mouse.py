import asyncio
import platform
import os
import keyboard as kbd
import mouse as ms
from logger import create_logger
from .interface import IInput

logger = create_logger("Inputs.keyboard_mouse")


class KeyboardMouse(IInput):
    __name = "keyboard_mouse"
    __keys = [
        "left ctrl",
        "left shift",
        "q",
        "mouse left",
        "z",
        "f",
        "e",
    ]

    def __init__(self):
        super().__init__()

    @property
    def name(self):
        return self.__name

    @staticmethod
    def is_supported():
        return platform.system() == "Windows" or (
            # on Linux running as root is required
            platform.system() == "Linux"
            and os.getuid() == 0
        )

    def _get_buttons(self, key: int) -> list[list[str]]:
        binary = bin(key)[2:][::-1]  # remove `0b` from beginning and reverse it
        keyboard = []
        mouse = []

        for idx, char in enumerate(binary):
            if char == "1":
                key: str = self.__keys[idx]
                if key.startswith("mouse "):
                    mouse.append(key.replace("mouse ", ""))
                else:
                    keyboard.append(key)

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

    async def send_input(self, input, held_time):
        keyboard, mouse = self._get_buttons(input)

        try:
            # logger.debug(f"Pressing buttons: {keyboard} {mouse}")
            await self._press_buttons(keyboard, mouse, True)
            await asyncio.sleep(held_time)
            # logger.debug(f"Releasing buttons: {keyboard} {mouse}")
            await self._press_buttons(keyboard, mouse, False)
        except BaseException as e:
            logger.warning(
                f"Releasing buttons because of exception `{repr(e)}`: {keyboard} {mouse}"
            )
            await self._press_buttons(keyboard, mouse, False)
            raise e
