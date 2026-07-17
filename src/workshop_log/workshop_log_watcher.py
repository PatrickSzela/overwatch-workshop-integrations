import asyncio
import os
from collections.abc import Callable

from ..logging import create_logger
from .text_file_watcher import TextFileWatcher

logger = create_logger("WorkshopLogWatcher")


class WorkshopLogWatcher(TextFileWatcher):
    def __init__(
        self,
        directory: str,
        loop: asyncio.AbstractEventLoop,
        on_create: Callable[[str], None],
        on_modify: Callable[[list[str]], None],
        on_close: Callable[[str], None],
    ):
        self._loop = loop

        self._on_create = on_create
        self._on_modify = on_modify
        self._on_close = on_close

        if not os.path.isdir(directory):
            raise NotADirectoryError(
                f'Path "{directory}" is not a directory or doesn\'t exists!'
            )

        directory = os.path.join(directory, "Workshop")

        if not os.path.isdir(directory):
            logger.debug('"%s" doesn\'t exists - creating...', directory)
            os.mkdir(directory)

        super().__init__(directory)

    def on_create(self, path: str):
        self._loop.call_soon_threadsafe(self._on_create, path)

    def on_modify(self, lines: list[str]):
        self._loop.call_soon_threadsafe(self._on_modify, lines)

    def on_close(self, path: str):
        self._loop.call_soon_threadsafe(self._on_close, path)
