"Stores possible states of a Custom Game."

from enum import StrEnum


class GameState(StrEnum):
    "Enum representing possible states of a match."

    # TODO: split lobby & match states?
    # TODO: add assembling heroes & in setup (how to handle control mode & competitive?)
    # TODO: remove GAME_ prefixes
    # TODO: rename FINISHED to COMPLETE and CLOSED to ENDED
    NONE = "NONE"
    STARTED = "GAME_STARTED"
    IN_PROGRESS = "GAME_IN_PROGRESS"
    IN_BETWEEN_ROUNDS = "GAME_IN_BETWEEN_ROUNDS"
    FINISHED = "GAME_FINISHED"
    CLOSED = "GAME_CLOSED"
