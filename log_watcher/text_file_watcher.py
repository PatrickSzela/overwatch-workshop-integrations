import os
import platform
from watchdog.events import (
    FileSystemEventHandler,
    DirCreatedEvent,
    FileCreatedEvent,
    DirModifiedEvent,
    FileModifiedEvent,
    FileClosedEvent,
)
from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver
from collections.abc import Callable
from logger import create_logger

logger = create_logger("TextFileWatcher")


class TextFileEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        on_file_created: Callable[[str], None],
        on_file_closed: Callable[[str], None],
        on_new_file_content: Callable[[list[str]], None],
    ):
        self._on_file_created = on_file_created
        self._on_file_closed = on_file_closed
        self._on_new_file_content = on_new_file_content

        self._previous_content: list[str] = []
        self._current_file_path: str = ""

    def on_created(self, event: DirCreatedEvent | FileCreatedEvent):
        if not isinstance(event.src_path, str):
            raise Exception()

        if event.is_directory or not event.src_path.endswith(".txt"):
            return

        self._current_file_path = event.src_path
        logger.debug(f'Opening file: "{self._current_file_path}"')
        self._on_file_created(self._current_file_path)
        self.read_file(event.src_path)

    def on_modified(self, event: DirModifiedEvent | FileModifiedEvent):
        if not isinstance(event.src_path, str):
            raise Exception()

        if event.src_path != self._current_file_path or event.is_directory:
            return

        self.read_file(event.src_path)

    def on_closed(self, event: FileClosedEvent):
        if event.src_path != self._current_file_path or event.is_directory:
            return

        self._previous_content = []

        logger.debug(f'Log file closed: "{self._current_file_path}"')
        self._on_file_closed(self._current_file_path)

    def read_file(self, path: str):
        with open(path, "r") as f:
            new_content = f.readlines()

            # Find the difference (new lines)
            new_lines = [
                line.strip()
                for line in new_content
                if line.strip()
                not in [old_line.strip() for old_line in self._previous_content]
            ]

            self._on_new_file_content(new_lines)

            self._previous_content = new_content


class TextFileWatcher:
    def __init__(self, directory: str):
        self.directory = directory

        if not os.path.isdir(self.directory):
            raise NotADirectoryError(
                f"Path {self.directory} is not a directory or doesn't exists!"
            )

        event_handler = TextFileEventHandler(
            on_file_created=self.on_file_created,
            on_file_closed=self.on_file_closed,
            on_new_file_content=self.on_new_file_content,
        )

        # WORKAROUND: https://github.com/gorakhargosh/watchdog/issues/915
        if platform.system() == "Windows":
            self.observer = PollingObserver(timeout=0.1)
        else:
            self.observer = Observer()

        self.observer.schedule(event_handler, self.directory, recursive=True)
        self.observer.start()

    def cleanup(self):
        self.observer.stop()
        self.observer.join()

    def on_file_created(self, path: str):
        pass

    def on_file_closed(self, path: str):
        pass

    def on_new_file_content(self, lines: list[str]):
        pass
