from argparse import Namespace
from typing import Any

from src import (
    DefineMessageIn,
    DefineMessageOut,
    GameState,
    IPlugin,
    MessageIn,
    MessageOut,
    ModeInfo,
    SupportedMessageDefinition,
    create_logger,
    define_message_in,
    define_message_out,
    is_message_in,
)

logger = create_logger("Test")

EchoMessage: DefineMessageIn[Any] = define_message_in("ECHO")
EchoResponse: DefineMessageOut[Any] = define_message_out("ECHO")


class Test(IPlugin):
    name = "Test mode"

    def __init__(self, args: Namespace, config: dict[str, Any]):
        super().__init__(args, config)

    def on_workshop_connect(self, mode: ModeInfo):
        logger.info(
            "Connected to %s v%s by %s (import code: %s) on %s - %s",
            mode["name"],
            mode["version"],
            mode["author"],
            mode["code"],
            mode["map"],
            mode["game_mode"],
        )

    def on_workshop_connect_error(self):
        logger.info("Failed to connect to a Workshop mode")

    def on_workshop_disconnect(self):
        logger.info("Disconnected from a Workshop mode")

    def on_workshop_log(self, log: str):
        logger.info('Workshop log received: "%s"', log)

    def on_workshop_register_message(
        self, structure: SupportedMessageDefinition
    ):
        logger.info("Workshop has registered message: %s", structure)

    def on_workshop_message(self, message: MessageIn):
        logger.info("Received message from the Workshop mode: %s", message)

        if not self.owtp:
            raise RuntimeError("Missing connection")

        if is_message_in(message, EchoMessage):
            self.owtp.add_message(EchoResponse(message.data))

    def on_workshop_send_message_start(self, message: MessageOut):
        logger.info(
            "Starting sending message to the Workshop mode: %s", message
        )

    def on_workshop_send_message_error(self, message: MessageOut, reason: str):
        logger.info(
            "Failed to send message to the Workshop mode: %s. Reason: %s",
            message,
            reason,
        )

    def on_workshop_send_message_finish(self, message: MessageOut):
        logger.info(
            "Finished sending message to the Workshop mode: %s", message
        )

    def on_game_state_change(self, state: GameState):
        logger.info('Game state changed to: "%s"', state.name)
