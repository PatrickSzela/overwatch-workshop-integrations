import logging
import os
from datetime import datetime

from rich.logging import RichHandler

from .utils import PROJECT_ROOT

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
FILE_NAME = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
APP_LOGGER_NAME = "OWI"
RICH_FORMATTER = "[%(display_name)-15.15s] %(message)s"
FILE_FORMATTER = (
    "[%(asctime)s] %(levelname)-10.10s: [%(display_name)-15.15s] %(message)s"
)

os.makedirs(LOGS_DIR, exist_ok=True)


class DisplayNameFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "display_name"):
            if record.name.startswith(APP_LOGGER_NAME + "."):
                record.display_name = record.name.split(".", 1)[1]
            else:
                record.display_name = record.name

        return super().format(record)


class AppOnlyFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        return record.name.startswith(APP_LOGGER_NAME)


class NonAppOnlyFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        return not record.name.startswith(APP_LOGGER_NAME)


class FileFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        is_app = record.name.startswith(APP_LOGGER_NAME)

        if is_app:
            return record.levelno >= logging.DEBUG

        return record.levelno >= logging.WARNING


def _update_handler(
    handler: logging.Handler,
    fmt: str | None = None,
    datefmt: str | None = None,
    filters: list[logging.Filter] | None = None,
    level: int = logging.WARNING,
):
    handler.setFormatter(DisplayNameFormatter(fmt, datefmt))
    handler.setLevel(level)

    for f in filters or []:
        handler.addFilter(f)

    return handler


ROOT_HANDLER = _update_handler(
    handler=RichHandler(rich_tracebacks=True),
    fmt=RICH_FORMATTER,
    datefmt="[%X]",
    filters=[NonAppOnlyFilter()],
    level=logging.WARNING,
)
APP_HANDLER = _update_handler(
    handler=RichHandler(rich_tracebacks=True),
    fmt=RICH_FORMATTER,
    datefmt="[%X]",
    filters=[AppOnlyFilter()],
    level=logging.INFO,
)
FILE_HANDLER = _update_handler(
    handler=logging.FileHandler(os.path.join(LOGS_DIR, FILE_NAME), delay=True),
    fmt=FILE_FORMATTER,
    filters=[FileFilter()],
    level=logging.DEBUG,
)

logging.basicConfig(
    level=logging.DEBUG,
    handlers=[FILE_HANDLER, ROOT_HANDLER],
)

APP_LOGGER = logging.getLogger(APP_LOGGER_NAME)
APP_LOGGER.setLevel(logging.DEBUG)
APP_LOGGER.addHandler(APP_HANDLER)


def set_logging(level: int | str | None):
    if level is None:
        logging.disable(logging.CRITICAL)
        return

    APP_HANDLER.setLevel(level)
    logging.disable(logging.NOTSET)


def create_logger(name: str):
    return APP_LOGGER.getChild(name)
