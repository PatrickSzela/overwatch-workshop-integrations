import asyncio
import os
from collections.abc import Callable
from logger import create_logger
from .text_file_watcher import TextFileWatcher

logger = create_logger("LogWatcher")


class WorkshopLogWatcher(TextFileWatcher):
    def __init__(
        self,
        directory,
        loop: asyncio.AbstractEventLoop,
        on_log_created: Callable[[str], None],
        on_workshop_output: Callable[[list[str]], None],
        on_log_closed: Callable[[str], None],
    ):
        self._loop = loop

        if on_log_created:
            async def _(path):
                on_log_created(path)

            self.on_log_created = _

        if on_workshop_output:
            async def _(lines):
                on_workshop_output(lines)

            self.on_workshop_output = _

        if on_log_closed:
            async def _(path):
                on_log_closed(path)

            self.on_log_closed = _

        if not os.path.isdir(directory):
            raise NotADirectoryError(
                f"Path {directory} is not a directory or doesn't exists!"
            )

        directory = os.path.join(directory, "Workshop")

        if not os.path.isdir(directory):
            os.mkdir(directory)

        super().__init__(directory)

    def on_file_created(self, path):
        asyncio.run_coroutine_threadsafe(self.on_log_created(path), self._loop)
        # self.on_log_created(path)

    def on_new_file_content(self, lines):
        asyncio.run_coroutine_threadsafe(self.on_workshop_output(lines), self._loop)
        # self.on_workshop_output(lines)

    def on_file_closed(self, path):
        asyncio.run_coroutine_threadsafe(self.on_log_closed(path), self._loop)
        # self.on_log_closed(path)

    async def on_log_created(self, path: str):
        logger.warning(f"Unimplemented `on_log_created`")

    async def on_workshop_output(self, lines: list[str]):
        logger.warning(f"Unimplemented `on_log_closed`")

    async def on_log_closed(self, path: str):
        logger.warning(f"Unimplemented `on_workshop_output`")
