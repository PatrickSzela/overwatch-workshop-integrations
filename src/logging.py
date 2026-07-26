import logging
import os
from datetime import datetime

from rich.logging import RichHandler

from .utils import PROJECT_ROOT

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

if not os.path.isdir(LOGS_DIR):
    os.mkdir(LOGS_DIR)


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool | logging.LogRecord:
        split_name = record.name.split(".", 1)

        if split_name[0] == "OWI":
            record.name = split_name[1]

        return True


RICH_FORMATTER = "[%(name)-15.15s] %(message)s"
RICH_HANDLER = RichHandler(rich_tracebacks=True)
RICH_HANDLER.setFormatter(logging.Formatter(RICH_FORMATTER, "[%X]"))
RICH_HANDLER.addFilter(ContextFilter())

FILE_FORMATTER = (
    "[%(asctime)s] %(levelname)-10.10s: [%(name)-15.15s] %(message)s"
)
FILE_HANDLER = logging.FileHandler(
    os.path.join(
        LOGS_DIR, f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    )
)

logging.basicConfig(
    format=FILE_FORMATTER,
    handlers=[RICH_HANDLER, FILE_HANDLER],
)


ROOT_LOGGER = logging.getLogger("OWI")


def set_log_level(level: int | str):
    ROOT_LOGGER.setLevel(level)


def create_logger(name: str):
    """Create a logger with specified `name`."""
    return ROOT_LOGGER.getChild(name)
