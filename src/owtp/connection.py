from typing import TYPE_CHECKING

from ..logging import create_logger
from . import messages
from .message import MessageIn

if TYPE_CHECKING:
    from .owtp import OWTP

OWTP_VERSION = "0.2.0"

logger = create_logger("OWTP.ConnectMgr")


class ConnectionManager:
    def __init__(self, owtp: "OWTP"):
        self._owtp = owtp
        self.connected = False
        self.interactive = False

    def connect(self, message: MessageIn[messages.ConnectMessageData]):
        if self.connected:
            logger.warning(
                "Tried connecting to the Workshop mode but we're already connected! Ignoring..."
            )
            return

        self.interactive = message.data["interactive"]
        logger.info("Establishing connection with the Workshop mode...")

        if message.data["version"] != OWTP_VERSION:
            logger.warning(
                "OWTP version mismatch: Workshop mode supports %s, but application uses %s",
                message.data["version"],
                OWTP_VERSION,
            )

        def on_connected():
            self.connected = True
            logger.info("Successfully connected with the Workshop mode")
            self._owtp.events.connect.emit(message.data["mode"])

        def on_not_connected():
            self.connected = False
            logger.warning(
                "Failed to establish connection with the Workshop mode"
            )
            self._owtp.events.connect_error.emit()

        self._owtp.add_message(
            messages.ConnectResponse(
                number_of_attempts=5,
                on_finish=on_connected,
                on_error=on_not_connected,
            )
        )

    def disconnect(self):
        if not self.connected:
            logger.warning(
                "Tried disconnecting from the Workshop mode but we're not connected! Ignoring..."
            )
            return

        logger.info("Workshop mode requested disconnect...")
        self._owtp.events.disconnect.emit()
        self.connected = False
