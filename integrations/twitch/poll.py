import random
from logger import create_logger

logger = create_logger("Twitch.Poll")


class Poll:
    def __init__(self, choices: list[str]):
        self._choices = choices

        self._votes: list[int] = [0] * len(choices)
        self._voters: list[str] = []
        self._winner: int = None

    def add_vote(self, vote: int, voter: str, channel: str = None):
        def info(text: str):
            logger.info(f"{voter} (in {channel}'s chat) {text}")

        try:
            vote = int(vote)

            if vote > len(self._choices) or vote <= 0:
                raise IndexError()
        except BaseException as e:
            info(f"casted an invalid vote `{vote}` - {repr(e)}")

        if voter in self._voters:
            info(f"tried to vote multiple times")
            return

        idx = vote - 1
        self._votes[idx] += 1
        self._voters.append(voter)

        info(f"voted for {self._choices[idx]}")

    @property
    def winner(self):
        if self._winner is not None:
            return self._winner

        max_val = max(self._votes)
        max_indices = [i for i, x in enumerate(self._votes) if x == max_val]
        self._winner = random.choice(max_indices)
        return self._winner

    @property
    def winner_str(self):
        return self._choices[self.winner]

    @property
    def results_str(self):
        return [f"{choice}: {self._votes[i]}" for i, choice in enumerate(self._choices)]

    @property
    def choices_str(self):
        return [f"{idx + 1}. {choice}" for idx, choice in enumerate(self._choices)]
