import platform
import shutil
import subprocess

from ..logging import create_logger
from .input import IInput
from .key_map.linux import KEY_MAP


class Ydotool(IInput):
    name = "ydotool"
    logger = create_logger("Input.Ydotool")
    command = "ydotool"
    key_map = KEY_MAP

    @classmethod
    async def is_supported(cls):
        if platform.system() != "Linux":
            return "not a Linux OS"

        if shutil.which(cls.command) is None:
            return f"'{cls.command}' executable not found"

        return True

    async def initialize(self):
        processes = subprocess.check_output(["ps", "aux"]).decode()

        if "ydotoold" not in processes.lower():
            self.logger.warning(
                "Ydotoold daemon is not running, don't forget to start it!"
            )

    def create_task(self, keys: list[str | int], is_press: bool):
        commands: list[str] = []
        keyboard: list[str] = []
        mouse: list[str] = []

        for key in keys:
            if isinstance(key, str) and key.startswith("0x"):
                mouse.append(key)
            else:
                keyboard.append(str(key))

        if keyboard:
            cmd = f"{self.command} key -d 0 "
            cmd += " ".join(
                [f"{button}:{'1' if is_press else '0'}" for button in keyboard]
            )
            commands.append(cmd)

        if mouse:
            cmd = f"{self.command} click -D 0 "
            cmd += " ".join(
                [
                    f"{'0x4' if is_press else '0x8'}{button[3:]}"
                    for button in mouse
                ]
            )
            cmd += " > /dev/null"  # ignore the random output from ydotool
            commands.append(cmd)

        return self._create_subprocess(" && ".join(commands))
