import asyncio
import json
import ssl
from argparse import ArgumentParser, Namespace
from pathlib import Path
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

logger = create_logger("WebSocket")


class WebSocket(IPlugin):
    name = "WebSocket"

    def __init__(
        self,
        args: Namespace,
        config: dict[str, Any],
    ):
        super().__init__(args, config)

        self._loop = asyncio.get_running_loop()
        self._server_task: asyncio.Task[Any] | None = None
        self._server: Server | None = None
        self._host: str = args.websocket_host or "localhost"
        self._port: int = args.websocket_port or 8080
        self._ssl_context: ssl.SSLContext | None = None

        if args.websocket_key and args.websocket_cert:
            self._ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            self._ssl_context.load_cert_chain(
                certfile=args.websocket_cert.resolve(),
                keyfile=args.websocket_key.resolve(),
            )
        elif not args.websocket_key and not args.websocket_cert:
            pass
        else:
            logger.warning(
                "Both --websocket-key-file and --websocket-cert-file must be provided together"
            )

    @staticmethod
    def add_arguments(parser: ArgumentParser):
        group = parser.add_argument_group("WebSocket integration")

        group.add_argument(
            "--ws",
            "--websocket",
            help="whether to enable WebSocket server; can be skipped if other Websocket arguments are passed",
            action="store_true",
            dest="websocket_enabled",
        )

        group.add_argument(
            "--ws-host",
            "--websocket-host",
            help="host name under which the WebSocket server should be available",
            type=str,
            metavar="HOST",
            dest="websocket_host",
        )

        group.add_argument(
            "--ws-port",
            "--websocket-port",
            help="port under which the WebSocket server should be available",
            type=int,
            metavar="PORT",
            dest="websocket_port",
        )

        group.add_argument(
            "--ws-key",
            "--websocket-key-file",
            help="path to a SSL private key file to use for a WebSocket server",
            type=Path,
            metavar="PATH",
            dest="websocket_key",
        )

        group.add_argument(
            "--ws-cert",
            "--websocket-cert-file",
            help="path to a SSL certificate file to use for a WebSocket server",
            type=Path,
            metavar="PATH",
            dest="websocket_cert",
        )

    async def initialize(self, plugins: list[IPlugin]):
        self._server_task = asyncio.create_task(self._run_server())

    async def _handle_messages(self, websocket: ServerConnection):
        ip, port, *_ = websocket.remote_address
        logger.debug("Client connected: '%s:%s'", ip, port)

        async for message in websocket:
            if not isinstance(message, str):
                logger.warning('Message is not a string: "%s"', message)
                continue

            logger.debug('Received message: "%s"', message)

            try:
                message = json.loads(message)
            except BaseException:
                logger.warning(
                    'Received message that\'s not a JSON: "%s"', message
                )
                continue

            match message:
                case {"name": str() as name, "data": dict() as data}:  # pyright: ignore[reportUnknownVariableType]
                    if not self.owtp:
                        logger.warning(
                            "Received message but not connected to a Workshop mode"
                        )
                        continue

                    self.owtp.add_message(MessageOut(name, data))  # pyright: ignore[reportUnknownArgumentType, reportArgumentType]
                case _:
                    logger.warning('Invalid message structure: "%s"', message)

        logger.debug("Client disconnected: '%s:%s'", ip, port)

    async def _run_server(self):
        async with serve(
            self._handle_messages, self._host, self._port, ssl=self._ssl_context
        ) as self._server:
            logger.info(
                "Running at ws%s://%s:%s",
                "s" if self._ssl_context else "",
                self._host,
                self._port,
            )

            if not self._ssl_context:
                logger.warning(
                    "Running unencrypted - do not expose the server to the Internet"
                )

            await self._server.serve_forever()

    async def cleanup(self):
        if self._server_task:
            if self._server and self._server.is_serving():
                self._server.close()
                logger.debug("Waiting for server to close...")
                await self._server.wait_closed()

            self._server_task.cancel()

    def on_workshop_message(self, message: MessageIn[EmptyData]):
        payload = json.dumps({"name": message.name, "data": message.data})
        logger.debug('Broadcasting payload: "%s"', payload)

        if not self._server or not self._server.is_serving():
            logger.warning(
                "Received message from Workshop but server is not running"
            )
            return

        broadcast(self._server.connections, payload)
