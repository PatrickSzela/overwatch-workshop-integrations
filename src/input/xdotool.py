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

    @classmethod
    async def is_supported(cls):
        if platform.system() != "Linux":
            return "not a Linux OS"

        if shutil.which(cls.command) is None:
            return f"'{cls.command}' executable not found"

        if "DISPLAY" not in os.environ:
            return "'DISPLAY' environmental variable not set"

        return True

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
