import asyncio
import json
from typing import Any
from websockets import Server, ServerConnection
from overwatch import GameState
from overwatch.integration import IIntegration
from owtp.message import Message
from websockets.asyncio.server import serve, broadcast


class Websocket(IIntegration):
    def __init__(self):
        super().__init__()

        self._loop = asyncio.get_event_loop()
        self.server: Server

    async def echo(self, websocket: ServerConnection):
        async for message in websocket:
            if not self.connection:
                raise RuntimeError("No connection")

            if isinstance(message, str):
                data = json.loads(message)
                print(data)
                self.connection.send_message(data['name'], data['data'])
            else:
                print(message)

    async def serve(self):
        async with serve(self.echo, "localhost", 8765) as server:
            self.server = server
            await server.serve_forever()

    def on_connect(self):
        if not self.connection:
            raise RuntimeError("No connection")

        print("Successfully established connection with the Workshop mode!")

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

        broadcast(self.server.connections, f"{name, data}")
