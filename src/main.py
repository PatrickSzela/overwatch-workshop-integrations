import _thread
import asyncio
import threading
from argparse import ArgumentParser
from typing import Any, cast

from plugins.poll import Poll
from plugins.stream.twitch import Twitch
from plugins.stream.youtube import YouTube

from .config import Config
from .game import Game
from .input import initialize as initialize_input
from .logging import create_logger
from .plugin import IPlugin

logger = create_logger("Main")


game: Game | None = None


PLUGINS: list[type[IPlugin]] = [Poll, Twitch, YouTube]


async def _logic():
    global game

    parser = ArgumentParser(
        prog="main.py",
        description="A proof-of-concept application that allows to control Custom Game's state from external sources",
    )

    for plugin in PLUGINS:
        plugin.add_arguments(parser)

    args = parser.parse_args()

    input_method = initialize_input()

    # Initialize config
    config = Config(PLUGINS)
    config.load()

    args_dict = vars(args)

    plugins: list[IPlugin] = []
    plugin_names = {
        key.split("_")[0]
        for key in args_dict.keys()
        if args_dict[key] not in [[], None]
    }

    for plugin in PLUGINS:
        if (plugin.name.lower() in plugin_names) or plugin.always_enabled:
            cfg = cast(
                Any,
                (
                    config.config[plugin.name.lower()]
                    if plugin.config_structure()
                    else None
                ),
            )
            plugins.append(plugin(args, cfg))

    for plugin in plugins:
        await plugin.initialize(plugins)

    game = Game(
        overwatch_dir=config.config["main"]["overwatch_dir"],
        plugins=plugins,
        input_method=input_method,
    )

    # from plugins.test.test import Test
    # game = Game(
    #     overwatch_dir=config.overwatch_dir,
    #     plugins=[Test()],
    # )

    # from integrations.websocket import Websocket
    # websocket = Websocket()
    # game = Game(
    #     overwatch_dir=config.overwatch_dir,
    #     integrations=[websocket],
    # )
    # await websocket.serve()

    # this is kinda ugly, but necessary for keyboard interrupts
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        if game:
            logger.info("Cleaning up...")
            await game.cleanup()


def global_thread_excepthook(args: Any):
    logger.critical(
        "Thread '%s' crashed with exception: %s",
        args.thread.name if args.thread else "Unknown",
        args.exc_value,
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )
    _thread.interrupt_main()


threading.excepthook = global_thread_excepthook


def main():
    try:
        asyncio.run(_logic(), debug=False)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected")
