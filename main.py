import asyncio
from rich import get_console
from overwatch import Overwatch
from logger import create_logger
import config_manager

logger = create_logger("Main")


overwatch: Overwatch | None = None
console = get_console()


async def main():
    global overwatch

    config = config_manager.initialize()

    from integrations.twitch import TwitchIntegration
    from rich.prompt import Prompt
    channel = Prompt.ask(
        "Enter name of the Twitch channel to join",
        default=(config.twitch_last_channel),
    )
    config.twitch_last_channel = channel
    config.save_if_necessary()

    twitch = TwitchIntegration(
        channel=channel,
        app_id=config.twitch_app_id,
        app_secret=config.twitch_app_secret,
    )

    await twitch.connect()

    overwatch = Overwatch(
        overwatch_dir=config.overwatch_dir,
        integrations=[twitch],
    )

    # from integrations.test import Test
    # overwatch = Overwatch(
    #     overwatch_dir=config.overwatch_dir,
    #     integrations=[Test()],
    # )

    # from integrations.websocket import Websocket
    # websocket = Websocket()
    # overwatch = Overwatch(
    #     overwatch_dir=config.overwatch_dir,
    #     integrations=[websocket],
    # )
    # await websocket.serve()

    # this is kinda ugly, but necessary for keyboard interrupts
    try:
        while True:
            await asyncio.sleep(1)
    except BaseException:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main(), debug=False)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt detected...")
    finally:
        logger.info("Cleaning up...")
        if overwatch:
            overwatch.cleanup()
