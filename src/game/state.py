"Stores possible states of a Custom Game."

from enum import IntEnum, StrEnum


class GameStateMessage(StrEnum):
    GAME_STATE_CHANGE = "GAME_STATE_CHANGE"


class GameState(IntEnum):
    "Enum representing possible states of a match."

    # TODO: split lobby & match states?
    # TODO: add assembling heroes & in setup (how to handle control mode & competitive?)
    NONE = 0
    STARTED = 1
    IN_PROGRESS = 2
    IN_BETWEEN_ROUNDS = 3
    COMPLETE = 4
    ENDED = 5
