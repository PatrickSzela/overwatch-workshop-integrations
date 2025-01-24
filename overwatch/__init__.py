import asyncio
from logger import create_logger
from owtp import OWTP
from overwatch.player import Player
from overwatch.integration import IIntegration, GameState
from log_watcher.log_watcher import WorkshopLogWatcher

logger = create_logger("Overwatch")


class Overwatch(IIntegration):
    def __init__(self, overwatch_dir: str, integrations: list[IIntegration] = []):
        super().__init__()

        self._state: GameState = GameState.NONE
        self._players: dict[int, dict[int, Player]] = {0: {}, 1: {}, 2: {}}
        self._mode: str = None
        self._map: str = None
        self._connection: OWTP = None
        self._integrations = integrations

        def on_log_created(path: str):
            self._connection = OWTP(
                on_connect=self.on_connect,
                on_disconnect=self.on_disconnect,
                on_error=self.on_error,
                on_log=self.on_log,
                on_message=self.on_message,
                on_message_structure_registered=self.on_message_structure_registered,
                on_message_started_sending=self.on_message_started_sending,
                on_message_sent=self.on_message_sent,
                on_message_error=self.on_message_error,
            )

        def on_workshop_output(lines: list[str]):
            if not self._connection:
                logger.warning(
                    f"Received Workshop output, but OWTP instance wasn't created, ignoring..."
                )
                return

            self._connection.add_workshop_output(lines)

        def on_log_closed(path: str):
            self.state = GameState.CLOSED

            if self._connection:
                self._connection.cleanup()
                self._connection = None

        self.workshopLogWatcher = WorkshopLogWatcher(
            directory=overwatch_dir,
            loop=asyncio.get_running_loop(),
            on_log_created=on_log_created,
            on_log_closed=on_log_closed,
            on_workshop_output=on_workshop_output,
        )

        for integration in self._integrations:
            integration.update_integration(self)

        print("Waiting for the game to start...")

    def cleanup(self):
        for integration in self._integrations:
            integration.update_integration(None)
            integration.cleanup()

        if self._connection:
            self._connection.cleanup()
            self._connection = None

        if self.workshopLogWatcher:
            self.workshopLogWatcher.cleanup()
            self.workshopLogWatcher = None

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value: GameState):
        logger.info(f"Game state updated to: {value}")
        self._state = value
        self.on_game_state_change(value)

    @property
    def mode(self):
        return self._mode

    @property
    def map(self):
        return self._map

    @property
    def connection(self):
        return self._connection

    def _register_player(self, player: Player):
        # TODO: handle when player has left the game
        logger.info(
            f"Adding player `{player.name}` (team: {player.team}, slot: {player.slot})"
        )
        self._players[player.team][player.slot] = player

    # region Events
    def on_connect(self):
        for integration in self._integrations:
            integration.on_connect()

    def on_disconnect(self):
        for integration in self._integrations:
            integration.on_disconnect()

    def on_error(self):
        for integration in self._integrations:
            integration.on_error()

    def on_log(self, log):
        for integration in self._integrations:
            integration.on_log(log)

    def on_message(self, name, data):
        match name:
            case "REGISTER_PLAYER":
                name, team, slot = data["name"], data["team"], data["slot"]
                player = Player(name, team, slot)
                self._register_player(player)

            case GameState.STARTED.value:
                self._mode = data["mode"]
                self._map = data["map"]
                self.state = GameState.STARTED

            case GameState.IN_PROGRESS.value:
                self.state = GameState.IN_PROGRESS

            case GameState.IN_BETWEEN_ROUNDS.value:
                self.state = GameState.IN_BETWEEN_ROUNDS

            case GameState.FINISHED.value:
                self.state = GameState.FINISHED

        # TODO: info if message wasn't handled
        for integration in self._integrations:
            integration.on_message(name, data)

    def on_message_structure_registered(self, structure):
        for integration in self._integrations:
            integration.on_message_structure_registered(structure)

    def on_message_started_sending(self, message):
        for integration in self._integrations:
            integration.on_message_started_sending(message)

    def on_message_sent(self, message):
        for integration in self._integrations:
            integration.on_message_sent(message)

    def on_message_error(self, message):
        for integration in self._integrations:
            integration.on_message_error(message)

    def on_game_state_change(self, state):
        for integration in self._integrations:
            integration.on_game_state_change(state)

    # endregion
