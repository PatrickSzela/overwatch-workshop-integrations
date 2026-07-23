import os
import platform
from collections.abc import Callable

from watchdog.events import (
    DirCreatedEvent,
    DirModifiedEvent,
    FileClosedEvent,
    FileCreatedEvent,
    FileModifiedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver

from ..logging import create_logger

logger = create_logger("TextFileWatcher")


class TextFileEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        on_create: Callable[[str], None],
        on_modify: Callable[[list[str]], None],
        on_close: Callable[[str], None],
    ):
        self._on_create = on_create
        self._on_modify = on_modify
        self._on_close = on_close

        self._previous_content: list[str] = []
        self._current_file_path: str = ""

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent):
        if not isinstance(event.src_path, str):
            return

        if event.is_directory or not event.src_path.endswith(".txt"):
            return

        logger.debug('Opening file: "%s"', event.src_path)
        self._current_file_path = event.src_path
        self._on_create(self._current_file_path)
        self.read_file(event.src_path)

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent):
        if not isinstance(event.src_path, str):
            raise TypeError(f'"{event.src_path}" is not a string')

        if event.src_path != self._current_file_path or event.is_directory:
            return

        self.read_file(event.src_path)

    def on_closed(self, event: FileClosedEvent):
        if event.src_path != self._current_file_path or event.is_directory:
            return

        self._previous_content = []

        logger.debug('File closed: "%s"', self._current_file_path)
        self._on_close(self._current_file_path)

    def read_file(self, path: str):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            new_content = f.readlines()

            # Find the difference (new lines)
            new_lines = []
            if len(new_content) > len(self._previous_content):
                new_lines = [
                    line.strip()
                    for line in new_content[len(self._previous_content) :]
                    if line.strip()
                ]

                self._on_modify(new_lines)
            elif len(new_content) < len(self._previous_content):
                raise RuntimeError(
                    f"Content in the log file {path} was removed - this should never happen!"
                )

            self._previous_content = new_content


class TextFileWatcher:
    def __init__(self, directory: str):
        self.directory = directory

        if not os.path.isdir(self.directory):
            raise NotADirectoryError(
                f'Path "{self.directory}" is not a directory or it doesn\'t exists!'
            )

        event_handler = TextFileEventHandler(
            on_create=self.on_create,
            on_modify=self.on_modify,
            on_close=self.on_close,
        )

        # WORKAROUND: https://github.com/gorakhargosh/watchdog/issues/915
        if platform.system() == "Windows":
            self._observer = PollingObserver(timeout=0.1)
        else:
            self._observer = Observer()

        self._observer.schedule(event_handler, self.directory, recursive=True)
        self._observer.start()

    def cleanup(self):
        self._observer.stop()
        self._observer.join()

    def on_create(self, path: str):
        pass

    def on_modify(self, lines: list[str]):
        pass

    def on_close(self, path: str):
        pass
