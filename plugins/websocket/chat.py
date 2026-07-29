import asyncio
from argparse import ArgumentParser, Namespace
from typing import Any

from plugins.stream import IStream
from src import IPlugin, create_logger

from .websocket import WebSocket as WebSocketPlugin
from .websocket import WebSocketMessage

logger = create_logger("WebSocketChat")


class WebSocketChat(IStream):
    name = "WebSocketChat"

    def __init__(
        self,
        args: Namespace,
        config: dict[str, Any],
    ):
        super().__init__(args, config)

        self._loop = asyncio.get_event_loop()
        self._websocket_plugin: WebSocketPlugin | None = None

    @staticmethod
    def add_arguments(parser: ArgumentParser):
        IStream.add_arguments(parser)

        group = parser.add_argument_group("WebSocket Chat")

        group.add_argument(
            "--wsc",
            "--websocket-chat",
            help="whether to connect bot to running WebSocket server",
            action="store_true",
            dest="websocketchat",
        )

    async def initialize(self, plugins: list[IPlugin]):
        for plugin in plugins:
            if isinstance(plugin, WebSocketPlugin):
                plugin.events.message.on(self._on_message)
                self._websocket_plugin = plugin

        await super().initialize(plugins)

    async def connect(self):
        if not self._websocket_plugin:
            logger.warning("WebSocket plugin has not been loaded")
            return

        await self._websocket_plugin.wait_is_running()

    async def disconnect(self):
        pass

    def is_connected(self):
        if not self._websocket_plugin:
            return False

        return self._websocket_plugin.is_running()

    async def send_message(self, message: str):
        if self.silent or not self._websocket_plugin:
            return

        self._websocket_plugin.send_message(message)

    def _on_message(self, data: WebSocketMessage):
        self.on_message(str(data["content"]), data["client"], "")
