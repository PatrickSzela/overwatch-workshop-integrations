"Stores Custom Game manager :class:`Game`."

import asyncio
from typing import Any, TypedDict

from ..file_watcher import WorkshopLogFileWatcher
from ..input import IInput
from ..logging import create_logger
from ..owtp import (
    OWTP,
    DefineMessageIn,
    MessageIn,
    MessageOut,
    ModeInfo,
    SupportedMessageDefinition,
    define_message_in,
    is_message_in,
)
from ..plugin import IPlugin
from .player import Player
from .state import GameState

logger = create_logger("Game")


class RegisterPlayerData(TypedDict):
    name: str
    team: int
    slot: int


RegisterPlayer: DefineMessageIn[RegisterPlayerData] = define_message_in(
    "REGISTER_PLAYER"
)
GameStarted = define_message_in(GameState.STARTED)
GameInProgress = define_message_in(GameState.IN_PROGRESS)
GameInBetweenRounds = define_message_in(GameState.IN_BETWEEN_ROUNDS)
GameFinished = define_message_in(GameState.FINISHED)

MESSAGES: list[DefineMessageIn[Any]] = [
    RegisterPlayer,
    GameStarted,
    GameInProgress,
    GameInBetweenRounds,
    GameFinished,
]


class Game:
    "Manages and stores all the information about currently running Custom Game and :class:`IPlugin` plugins."

    def __init__(
        self,
        overwatch_dir: str,
        plugins: list[IPlugin],
        input_method: IInput,
        buttons_down_ticks: int,
        buttons_up_ticks: int,
        **_: Any,
    ):
        super().__init__()

        self._state: GameState = GameState.NONE
        self._players: dict[int, dict[int, Player]] = {0: {}, 1: {}, 2: {}}
        self._mode_info: ModeInfo = {
            "author": "",
            "code": "",
            "game_mode": "",
            "map": "",
            "name": "",
            "version": "",
        }
        self._connection: OWTP | None = None
        self._plugins = plugins
        self._input_method = input_method

        def on_log_create(_: str):
            self._connection = OWTP(
                self._input_method, buttons_down_ticks, buttons_up_ticks
            )
            owtp = self._connection

            owtp.events.mode_info.on(self._on_mode_info)
            owtp.events.connect.on(self._on_connect)
            owtp.events.disconnect.on(self._on_disconnect)
            owtp.events.connect_error.on(self._on_connect_error)
            owtp.events.log.on(self._on_log)
            owtp.events.message.on(self._on_message)
            owtp.events.register_supported_message.on(
                self._on_register_supported_message
            )
            owtp.events.send_message_start.on(self._on_send_message_start)
            owtp.events.send_message_finish.on(self._on_send_message_finish)
            owtp.events.send_message_error.on(self._on_send_message_error)

            for msg in MESSAGES:
                self._connection.register_message_in(msg)

            for plugin in self._plugins:
                for msg in plugin.incoming_messages():
                    self._connection.register_message_in(msg)

        def on_log_modify(lines: list[str]):
            if not self._connection:
                logger.warning(
                    "Received Workshop output, but OWTP instance wasn't created, ignoring..."
                )
                return

            self._connection.add_workshop_output(lines)

        def on_log_close(_: str):
            self._set_state(GameState.CLOSED)

            if self._connection:
                self._connection.cleanup()
                self._connection = None

        self.workshop_log_watcher = WorkshopLogFileWatcher(
            overwatch_dir,
            asyncio.get_running_loop(),
            on_log_create,
            on_log_modify,
            on_log_close,
        )

        for plugin in self._plugins:
            plugin.game = self

        logger.info("Waiting for the game to start...")

    async def cleanup(self):
        for plugin in self._plugins:
            plugin.game = None
            await plugin.cleanup()

        if self._connection:
            self._connection.cleanup()
            self._connection = None

        if self.workshop_log_watcher:
            self.workshop_log_watcher.cleanup()
            self.workshop_log_watcher = None

    @property
    def state(self):
        return self._state

    def _set_state(self, value: GameState):
        logger.info('Game state changed to: "%s"', value)
        self._state = value

        for plugin in self._plugins:
            plugin.on_game_state_change(value)

    @property
    def mode(self):
        return self._mode_info

    @property
    def connection(self):
        return self._connection

    def _register_player(self, player: Player):
        # TODO: handle when player has left the game
        logger.info(
            'Registering player "%s" (team: %s, slot: %s)',
            player.name,
            player.team,
            player.slot,
        )
        self._players[player.team][player.slot] = player

    # region Events
    def _on_mode_info(self, mode: ModeInfo):
        self._mode_info = mode

    def _on_connect(self, mode: ModeInfo):
        for plugin in self._plugins:
            plugin.on_workshop_connect(mode)

    def _on_connect_error(self):
        for plugin in self._plugins:
            plugin.on_workshop_connect_error()

    def _on_disconnect(self):
        for plugin in self._plugins:
            plugin.on_workshop_disconnect()

    def _on_log(self, log: str):
        for plugin in self._plugins:
            plugin.on_workshop_log(log)

    def _on_register_supported_message(
        self, structure: SupportedMessageDefinition
    ):
        for plugin in self._plugins:
            plugin.on_workshop_register_message(structure)

    def _on_message(self, message: MessageIn):
        if is_message_in(message, RegisterPlayer):
            player = Player(
                message.data["name"],
                message.data["team"],
                message.data["slot"],
            )
            self._register_player(player)
        elif is_message_in(message, GameStarted):
            self._set_state(GameState.STARTED)
        elif is_message_in(message, GameInProgress):
            self._set_state(GameState.IN_PROGRESS)
        elif is_message_in(message, GameInBetweenRounds):
            self._set_state(GameState.IN_BETWEEN_ROUNDS)
        elif is_message_in(message, GameFinished):
            self._set_state(GameState.FINISHED)
        else:
            # TODO: info if message wasn't handled
            for plugin in self._plugins:
                plugin.on_workshop_message(message)

    def _on_send_message_start(self, message: MessageOut):
        for plugin in self._plugins:
            plugin.on_workshop_send_message_start(message)

    def _on_send_message_error(self, message: MessageOut, reason: str):
        for plugin in self._plugins:
            plugin.on_workshop_send_message_error(message, reason)

    def _on_send_message_finish(self, message: MessageOut):
        for plugin in self._plugins:
            plugin.on_workshop_send_message_finish(message)

    # endregion
