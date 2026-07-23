import asyncio
import json
from argparse import Namespace
from typing import Any

from websockets import Server, ServerConnection
from websockets.asyncio.server import broadcast, serve

from src import (
    EmptyData,
    IPlugin,
    MessageIn,
    MessageOut,
    create_logger,
)

logger = create_logger("Websocket")


class Websocket(IPlugin):
    def __init__(
        self,
        args: Namespace,
        config: dict[str, Any],
    ):
        super().__init__(args, config)

        self._loop = asyncio.get_running_loop()
        self._server_task: asyncio.Task[Any] | None = None
        self.server: Server

    async def echo(self, websocket: ServerConnection):
        async for message in websocket:
            if not self.owtp:
                raise RuntimeError("No connection")

            if not isinstance(message, str):
                raise TypeError(f"Message is not a string: {message}")

            message = json.loads(message)
            logger.debug("Received data: %s", message)

            match message:
                case {"name": str() as name, "data": dict() as data}:  # pyright: ignore[reportUnknownVariableType]
                    self.owtp.add_message(MessageOut(name, data))  # pyright: ignore[reportUnknownArgumentType, reportArgumentType]
                case _:
                    raise TypeError(f"Invalid message structure: {message}")

    async def initialize(self, plugins: list[IPlugin]):
        self._server_task = asyncio.create_task(self._run_server())

    async def _run_server(self):
        async with serve(self.echo, "localhost", 8765) as server:
            self.server = server
            await server.serve_forever()

    async def cleanup(self):
        if self._server_task:
            self._server_task.cancel()

    def on_workshop_message(self, message: MessageIn[EmptyData]):
        payload = json.dumps({"name": message.name, "data": message.data})
        broadcast(self.server.connections, payload)
