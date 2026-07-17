import asyncio
import os
import platform
import shutil

from ..logging import create_logger
from .input import IInput

logger = create_logger("Input.KwinNested")
WAYLAND_SOCKET = "wayland-nested"


class KwinNested(IInput):
    name = "kwin_nested"
    __command = "xdotool"
    __keys = [
        "Control_L",  # ctrl
        "Shift_L",  # shift
        "q",  # q
        "mouse_1",  # m1
        "z",  # z
        "f",  # f
        "e",  # e
    ]

    def __init__(self):
        pass

    @staticmethod
    def is_supported() -> bool:
        return (
            platform.system() == "Linux"
            and shutil.which(KwinNested.__command) is not None
            and os.path.exists("/run/user/1000/wayland-nested")
            and os.path.exists("/tmp/.X11-unix/X1")
        )

    def _construct_command(self, key: int, is_press: bool) -> str:
        cmd: list[str] = [self.__command]
        binary = bin(key)[2:][::-1]  # remove `0b` from beginning and reverse it
        keyboard: list[str] = []
        mouse: list[str] = []

        for idx, char in enumerate(binary):
            if char == "1":
                key_str = self.__keys[idx]
                if key_str.startswith("mouse"):
                    mouse.append(key_str)
                else:
                    keyboard.append(key_str)

        if keyboard:
            cmd.extend(["keydown" if is_press else "keyup", "--delay", "0"])
            cmd.extend(keyboard)

        if mouse:
            cmd.extend(["mousedown" if is_press else "mouseup"])
            cmd.extend([button.replace("mouse_", "") for button in mouse])

        return " ".join(cmd)

    async def _execute_command(self, command: str):
        env = os.environ.copy()
        env["WAYLAND_DISPLAY"] = WAYLAND_SOCKET
        env["DISPLAY"] = ":1"

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.warning(
                'Command "%s" failed with exit code %d, stderr: %s, stdout: %s',
                command,
                proc.returncode,
                stderr.decode().strip(),
                stdout.decode().strip(),
            )

    async def send_input(self, input: int, held_time: float) -> None:
        press = self._construct_command(input, True)
        release = self._construct_command(input, False)

        try:
            logger.debug("Pressing buttons: %s", input)
            await self._execute_command(press)
            await asyncio.sleep(held_time)
            logger.debug("Releasing buttons: %s", input)
            await self._execute_command(release)
        except BaseException as e:
            logger.warning(
                "Releasing buttons because of exception: %s", repr(e)
            )
            await self._execute_command(release)
            raise e
