import asyncio

from rich import get_console

import config_manager
from logger import create_logger
from overwatch import Overwatch

logger = create_logger("Main")


overwatch: Overwatch | None = None
console = get_console()


async def main():
    global overwatch

    config = config_manager.initialize()

    from rich.prompt import Prompt

    from integrations.twitch import TwitchIntegration

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

    # from integrations.youtube import YouTubeIntegration

    # handles = Prompt.ask(
    #     "Enter handles for channels to join (split by comma), or leave empty",
    # )
    # video_ids = Prompt.ask(
    #     "Enter video ids for active streams (split by comma), or leave empty",
    # )

    # youtube = YouTubeIntegration(
    #     channel_handles=set(handles.split(",") if handles else []),
    #     video_ids=set(video_ids.split(",") if video_ids else []),
    # )
    # await youtube.connect()

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
