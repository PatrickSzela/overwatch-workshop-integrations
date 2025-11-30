import asyncio
import subprocess
import platform
from logger import create_logger
from .interface import IInput

logger = create_logger("Inputs.Ydotool")


class Ydotool(IInput):
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
        super().__init__()

    @property
    def name(self):
        return self.__command

    @staticmethod
    def is_supported():
        if platform.system() != "Linux":
            return False

        try:
            subprocess.call(
                #["host-spawn", "ydotool"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
                ["ydotool"], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT
            )
            return True
        except FileNotFoundError:
            return False

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

        if len(keyboard):
            cmd = f"{self.__command} key -d 0 "
            cmd += " ".join(
                [f"{button}:{"1" if is_press else "0"}" for button in keyboard]
            )
            commands.append(cmd)

        if len(mouse):
            cmd = f"{self.__command} click -D 0 "
            cmd += " ".join(
                [f"{"0x4" if is_press else "0x8"}{button[3:]}" for button in mouse]
            )
            cmd += " > /dev/null"  # ignore the random output from ydotool
            commands.append(cmd)

        return " && ".join(commands)

    async def _execute_command(self, command: str):
        await asyncio.create_subprocess_shell(
            command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

    async def send_input(self, input: int, held_time: float):
        press = self._construct_command(input, True)
        release = self._construct_command(input, False)

        try:
            # logger.debug(f"Pressing buttons: {input}")
            await self._execute_command(press)
            await asyncio.sleep(held_time)
            # logger.debug(f"Releasing buttons: {input}")
            await self._execute_command(release)
        except BaseException as e:
            logger.warning(
                f"Releasing buttons because of exception `{repr(e)}`: {input}"
            )
            await self._execute_command(release)
            raise e
