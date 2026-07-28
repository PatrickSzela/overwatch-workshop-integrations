import _thread
import asyncio
import json
import logging
import sys
import threading
from argparse import ArgumentParser
from typing import Any, cast

from .config import Config
from .game import Game
from .input import get_input_method, print_keys_diff
from .logging import create_logger, set_logging
from .plugin import IPlugin, load_plugins

logger = create_logger("Main")


async def _logic():
    parser = ArgumentParser(
        prog="main.py",
        description="A proof-of-concept application that allows to control Custom Game's state from external sources",
    )

    parser.add_argument(
        "-d",
        "--debug",
        help="enable output of debug messages to terminal",
        action="store_true",
    )

    parser.add_argument(
        "--print-keys",
        help="List all keys supported by current input method",
        action="store_true",
    )

    parser.add_argument(
        "--print-keys-diff",
        help="List differences between keys of all input methods",
        action="store_true",
    )

    parser.add_argument(
        "--print-default-config",
        help="Print out default config",
        action="store_true",
    )

    plugin_classes = load_plugins()

    for plugin in plugin_classes:
        plugin.add_arguments(parser)

    args = parser.parse_args()
    args_dict = vars(args)

    if any(k.startswith("print_") and v is True for k, v in args_dict.items()):
        set_logging(None)
    else:
        set_logging(logging.DEBUG if args.debug else logging.INFO)

    if args.print_keys_diff:
        print_keys_diff()
        sys.exit()

    args = parser.parse_args()
    input_method = await get_input_method()

    if args.print_keys:
        print(f"All supported keys by '{input_method.name}':")
        print(json.dumps(list(input_method.list_keys())))
        sys.exit()

    await input_method.initialize()

    config = Config(plugin_classes)

    if args.print_default_config:
        print(json.dumps(config.default_config(), indent=4))
        sys.exit()

    config.load()

    input_method.set_keys(config.config["keybinds"])

    plugins: list[IPlugin] = []
    plugin_names = {
        key.split("_")[0]
        for key in args_dict.keys()
        if args_dict[key] not in [[], None]
    }

    for plugin in plugin_classes:
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

    logger.info("Loaded plugins: %s", [plugin.name for plugin in plugins])
    await asyncio.gather(*(plugin.initialize(plugins) for plugin in plugins))

    c = config.config.copy()
    c.pop("plugins")

    game = Game(
        **c,
        plugins=plugins,  # pyright: ignore[reportCallIssue]
        input_method=input_method,
    )

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
