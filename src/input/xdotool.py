import os
import platform
import shutil

from ..logging import create_logger
from .input import IInput
from .key_map.xdotool import KEY_MAP


class Xdotool(IInput):
    name = "xdotool"
    logger = create_logger("Input.Xdotool")
    command = "xdotool"
    key_map = KEY_MAP

    @staticmethod
    async def is_supported() -> bool:
        return (
            platform.system() == "Linux"
            and shutil.which(Xdotool.command) is not None
            and "DISPLAY" in os.environ
        )

    def create_task(self, keys: list[str | int], is_press: bool):
        cmd: list[str] = [self.command]
        keyboard: list[str] = []
        mouse: list[str] = []

        for key in keys:
            if isinstance(key, str) and key.startswith("mouse"):
                mouse.append(key)
            else:
                keyboard.append(str(key))

        if keyboard:
            cmd.extend(["keydown" if is_press else "keyup", "--delay", "0"])
            cmd.extend(keyboard)

        if mouse:
            cmd.extend(["mousedown" if is_press else "mouseup"])
            cmd.extend([button.replace("mouse_", "") for button in mouse])

        return self._create_subprocess(" ".join(cmd))
