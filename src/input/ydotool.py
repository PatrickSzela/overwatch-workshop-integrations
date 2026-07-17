import asyncio
import platform
import shutil

from ..logging import create_logger
from .input import IInput

logger = create_logger("Input.Ydotool")


class Ydotool(IInput):
    name = "ydotool"
    __command = "ydotool"
    __keys = [
        "29",  # ctrl
        "42",  # shift
        "16",  # q
        "0xC0",  # m1
        "44",  # z
        "33",  # f
        "18",  # e
    ]

    def __init__(self):
        pass

    @staticmethod
    def is_supported():
        return (
            platform.system() == "Linux"
            and shutil.which(Ydotool.__command) is not None
        )

    def _construct_command(self, key: int, is_press: bool) -> str:
        # commands = ["host-spawn"]
        commands: list[str] = []
        binary = bin(key)[2:][::-1]  # remove `0b` from beginning and reverse it
        keyboard: list[str] = []
        mouse: list[str] = []

        for idx, char in enumerate(binary):
            if char == "1":
                key_str = self.__keys[idx]
                if key_str.startswith("0x"):
                    mouse.append(key_str)
                else:
                    keyboard.append(key_str)

        if keyboard:
            cmd = f"{self.__command} key -d 0 "
            cmd += " ".join(
                [f"{button}:{'1' if is_press else '0'}" for button in keyboard]
            )
            commands.append(cmd)

        if mouse:
            cmd = f"{self.__command} click -D 0 "
            cmd += " ".join(
                [
                    f"{'0x4' if is_press else '0x8'}{button[3:]}"
                    for button in mouse
                ]
            )
            cmd += " > /dev/null"  # ignore the random output from ydotool
            commands.append(cmd)

        return " && ".join(commands)

    async def _execute_command(self, command: str):
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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

    async def send_input(self, input: int, held_time: float):
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
