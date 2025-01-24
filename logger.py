import os
import logging
import datetime
from rich.logging import RichHandler

if not os.path.isdir("./logs"):
    os.mkdir("./logs")


richHandler = RichHandler(rich_tracebacks=True)
richHandler.setFormatter(logging.Formatter("[%(name)-10.10s] %(message)s", "[%X]"))


logging.basicConfig(
    format="[%(asctime)s] %(levelname)-10.10s: [%(name)-15.15s] %(message)s",
    handlers=[
        richHandler,
        logging.FileHandler(f"logs/{datetime.datetime.now()}.log".replace(":", "_")),
    ],
)


def create_logger(name):
    logger = logging.getLogger(name)

    # if logger.hasHandlers():
    #     return logger

    # if richHandler in logger.handlers:
    #     return logger

    logger.setLevel(logging.DEBUG)

    # handler = logging.StreamHandler()
    # formatter = logging.Formatter("[%(asctime)s] %(levelname)s: [%(name)s] %(message)s")

    # handler.setFormatter(formatter)
    # logger.addHandler(handler)

    # logger.addHandler(richHandler)

    return logger
