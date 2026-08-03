import math
import random
from argparse import Namespace
from collections import Counter
from typing import Any, TypedDict

from plugins.stream import ChatMessage, IStream
from src import (
    DefineMessageIn,
    DefineMessageOut,
    EmptyData,
    GameState,
    IPlugin,
    MessageIn,
    create_logger,
    define_message_in,
    define_message_out,
    is_message_in,
)

logger = create_logger("Poll")


class PollStartData(TypedDict):
    timeout: float
    choices: list[str]


class PollCancelData(TypedDict):
    reason: str


class PollWinnerData(TypedDict):
    winnerIdx: int


PollStart: DefineMessageIn[PollStartData] = define_message_in("POLL_START")
PollEnd = define_message_in("POLL_END")
PollCancel: DefineMessageIn[PollCancelData] = define_message_in("POLL_CANCEL")
PollWinner: DefineMessageOut[PollWinnerData] = define_message_out("POLL_WINNER")


class Poll(IPlugin):
    name = "Poll"
    always_enabled = True

    def __init__(
        self,
        args: Namespace,
        config: dict[str, Any],
    ):
        super().__init__(args, config)

        self._choices: list[str]
        self._votes: dict[tuple[str, str], int]
        self._winner: int | None
        self._in_progress: bool = False
        self._streams: list[IStream] = []

    async def initialize(self, plugins: list[IPlugin]):
        for plugin in plugins:
            if isinstance(plugin, IStream):
                plugin.events.message.on(self.on_message)
                self._streams.append(plugin)

    async def cleanup(self):
        # if self._in_progress:
        #     self.cancel_poll("Exiting")

        for stream in self._streams:
            stream.events.message.off(self.on_message)

    def incoming_messages(self) -> list[DefineMessageIn[Any]]:
        return [PollStart, PollEnd, PollCancel]

    def send_message(self, message: str):
        for stream in self._streams:
            stream.send_message_nowait(message)

    def on_message(self, message: ChatMessage):
        msg = message.content.strip()

        if msg.isnumeric() and self._in_progress:
            self.add_vote(msg, message.user, message.chatroom, message.service)

    def start_poll(self, choices: list[str], timeout: float):
        if self._in_progress:
            self.cancel_poll("Started another poll")

        self._choices = choices
        self._votes = {}
        self._winner = None
        self._in_progress = True

        choices_str = [
            f"{idx + 1}. {choice}" for idx, choice in enumerate(self._choices)
        ]
        choices_str = " | ".join(choices_str)

        self.send_message(
            f"New poll has started! Cast your vote by sending the number corresponding to your choice in chat:\n{choices_str}. Poll will end in {math.ceil(timeout)} in-game seconds."
        )

    def end_poll(self):
        if not self.owtp:
            raise RuntimeError("Missing connection")

        if not self._in_progress:
            logger.warning(
                "Tried to end a poll while one hasn't been started yet"
            )
            return

        winner, results = self.get_winner()
        winner_str = self._choices[winner]
        results_str = [
            f"{choice}: {results[i]}" for i, choice in enumerate(self._choices)
        ]
        results_str = " | ".join(results_str)

        logger.info('Poll has ended, "%s" won! Results: %s', winner_str, results_str)
        self.send_message(
            f'Poll has ended, "{winner_str}" won! Results: {results_str}'
        )

        def on_finish():
            self._in_progress = False

        self.owtp.add_message(
            PollWinner(
                {"winnerIdx": winner}, on_finish=on_finish, on_error=on_finish
            )
        )

    def cancel_poll(self, reason: str):
        if not self._in_progress:
            logger.warning(
                "Tried to cancel a poll while one hasn't been started yet"
            )
            return

        if not self.owtp:
            raise RuntimeError("Missing connection")

        self.owtp.remove_messages_of_type(PollWinner)

        self.send_message(f"Poll has been cancelled, reason: {reason}")
        self._in_progress = False

    def add_vote(self, choice: str, voter: str, channel: str, service: str):
        def info(text: str):
            logger.info(
                "'%s' (%son %s) %s",
                voter,
                f"in {channel}'s chat " if channel else "",
                service,
                text,
            )

        try:
            val = int(choice) - 1

            if val >= len(self._choices) or val < 0:
                raise IndexError()
        except BaseException as e:
            info(f'casted an invalid vote "{choice}": {repr(e)}')
            return

        if (voter, service) in self._votes:
            info(f"has changed their vote to {choice}")
        else:
            info(f"voted for {choice}")

        self._votes[(voter, service)] = val

    def get_winner(self):
        counted_votes: list[int] = [0] * len(self._choices)
        for idx, count in Counter(self._votes.values()).items():
            counted_votes[idx] = count

        max_result = max(counted_votes)

        # since there can be more than one winner, get all choices that have max counts and pick a random one
        max_indices = [
            i for i, x in enumerate(counted_votes) if x == max_result
        ]
        self._winner = random.choice(max_indices)

        return self._winner, counted_votes

    def on_workshop_disconnect(self):
        if self._in_progress:
            self.cancel_poll("Disconnected from the Workshop mode")

    def on_workshop_message(self, message: MessageIn[EmptyData]):
        if is_message_in(message, PollStart):
            timeout, choices = message.data["timeout"], message.data["choices"]
            self.start_poll(choices, timeout)

        elif is_message_in(message, PollEnd):
            self.end_poll()

        elif is_message_in(message, PollCancel):
            self.cancel_poll(message.data["reason"])

    def on_game_state_change(self, state: GameState):
        if not self.game:
            raise RuntimeError("Missing game instance")

        match state:
            case GameState.ENDED:
                if self._in_progress:
                    self.cancel_poll("Lobby has been closed")
            case _:
                pass
