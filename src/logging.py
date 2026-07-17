import logging
import os
from datetime import datetime

from rich.logging import RichHandler

from .helpers import PROJECT_ROOT

LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")

if not os.path.isdir(LOGS_DIR):
    os.mkdir(LOGS_DIR)


RICH_FORMATTER = "[%(name)-15.15s] %(message)s"
RICH_HANDLER = RichHandler(rich_tracebacks=True)
RICH_HANDLER.setFormatter(logging.Formatter(RICH_FORMATTER, "[%X]"))

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


def create_logger(name: str):
    """Create a logger with specified `name`."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    return logger
