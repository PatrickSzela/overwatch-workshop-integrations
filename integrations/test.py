import random
from typing import Any
from overwatch import GameState
from overwatch.integration import IIntegration
from owtp.message import Message


class Test(IIntegration):
    def __init__(self):
        super().__init__()

    def on_connect(self):
        if not self.connection:
            raise RuntimeError("No connection")
        
        print("Successfully established connection with the Workshop mode!")

        # TODO: remove
        if self.connection.is_message_structure_registered("TEST"):
            self.connection.send_message(
                "TEST",
                {
                    "true": True,
                    "false": False,
                    "zero": 0,
                    "positiveNumber": 123.45,
                    "negativeNumber": -123.45,
                    "emptyString": "",
                    "string": "test",
                },
                number_of_attempts=1,
            )

    def on_error(self):
        print("Failed to connect with the Workshop mode!")

    def on_message_error(self, message: Message):
        print(f"Failed to send message `{message.name}`")

    def on_game_state_change(self, state: GameState):
        if not self.overwatch:
            raise RuntimeError("No Overwatch instance")
        
        match state:
            case GameState.STARTED:
                print(
                    f"New game has started - {self.overwatch.mode} on {self.overwatch.map}"
                )
            case GameState.IN_PROGRESS:
                print("Game is in progress")
            case GameState.IN_BETWEEN_ROUNDS:
                print("Game is in between rounds")
            case GameState.FINISHED:
                print("Game has been finished")
            case GameState.CLOSED:
                print("Lobby has been closed")
            case _:
                pass

    def on_message(self, name: str, data: dict[str, Any]):
        if not self.connection:
            raise RuntimeError("No connection")
        
        match name:
            case "POLL_START":
                timeout, choices = data["timeout"], data["choices"]
                print(
                    f"Poll has been started! Available choices: {choices}. Voting will end in {timeout} secs."
                )
                self.choices: list[str] = choices

            case "POLL_END":
                winner = random.choice(self.choices)
                idx = self.choices.index(winner)
                print(f"Poll has been ended! Sending winner: `{winner}` (index {idx})")
                self.connection.send_message(
                    "POLL_WINNER",
                    {"winnerIdx": idx},
                )

            case "POLL_CANCEL":
                print(f"Poll has been cancelled, reason: {data['reason']}")

            case "SEND_MESSAGE":
                print(data["message"])

            case _:
                pass
