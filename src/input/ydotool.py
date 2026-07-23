import platform
import shutil
import subprocess

from ..logging import create_logger
from .input import IInput


class Ydotool(IInput):
    name = "ydotool"
    logger = create_logger("Input.Ydotool")
    command = "ydotool"
    keys = [
        "29",  # ctrl
        "42",  # shift
        "16",  # q
        "0xC0",  # m1
        "44",  # z
        "33",  # f
        "18",  # e
    ]

    @staticmethod
    async def is_supported():
        return (
            platform.system() == "Linux"
            and shutil.which(Ydotool.command) is not None
        )

    def __init__(self) -> None:
        processes = subprocess.check_output(["ps", "aux"]).decode()

        if "ydotoold" not in processes.lower():
            self.logger.warning(
                "Ydotoold daemon is not running, don't forget to start it!"
            )

    def create_task(self, keys: list[str], is_press: bool):
        commands: list[str] = []
        keyboard: list[str] = []
        mouse: list[str] = []

        for key in keys:
            if key.startswith("0x"):
                mouse.append(key)
            else:
                keyboard.append(key)

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
