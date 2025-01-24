import asyncio
from twitchAPI.twitch import Twitch, TwitchUser
from twitchAPI.oauth import UserAuthenticator, UserAuthenticationStorageHelper
from twitchAPI.type import AuthScope, ChatEvent, ChatRoom
from twitchAPI.chat import Chat, EventData, ChatMessage, ChatSub, ChatCommand
from logger import create_logger
from overwatch.integration import IIntegration
from overwatch import GameState
from .poll import Poll

logger = create_logger("Twitch")

USER_SCOPE = [AuthScope.CHAT_READ, AuthScope.CHAT_EDIT]
BOT_TITLE = "Overwatch Stream Integration Bot"


class TwitchIntegration(IIntegration):
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        channel: str,
    ):
        super().__init__()

        self._app_id = app_id
        self._app_secret = app_secret
        self._channel = channel

        self._twitch: Twitch = None
        self._chat: Chat = None
        self._me: TwitchUser = None

        self._poll: Poll = None

        self._loop = asyncio.get_event_loop()

    def cleanup(self):
        # this is hella ugly, but works
        if self._loop.is_closed():
            asyncio.run(self.cleanup_async())
        else:
            asyncio.run_coroutine_threadsafe(self.cleanup_async(), self._loop)

    async def cleanup_async(self):
        if self._poll:
            self.cancel_poll("Exiting")
            self._poll = None

        if self._chat and self._chat.is_connected():
            await self.send_message_in_chat(f"{BOT_TITLE}, signing off... o7")
            self._chat.stop()

        if self._twitch:
            await self._twitch.close()

    async def connect(self):
        logger.info("Connecting to Twitch...")

        self._twitch = await Twitch(self._app_id, self._app_secret)
        helper = UserAuthenticationStorageHelper(self._twitch, USER_SCOPE)

        await helper.bind()

        users = self._twitch.get_users()
        me = anext(users)
        self._me = await me

        logger.info(f'Successfully connected to Twitch as user "{self._me.login}"!')

        self._chat = await Chat(self._twitch, no_shared_chat_messages=False)

        self._chat.register_event(ChatEvent.READY, self._on_ready)
        self._chat.register_command("vote", self._on_vote)

        self._chat.start()

    async def send_message_in_chat(self, message: str):
        logger.info(f"Sending message in chat: {message}")

        if self._chat and self._chat.is_connected():
            await self._chat.send_message(self._channel, f"/me {message}")
        else:
            logger.warning(
                "Tried sending message in chat, but we're not connected to it!"
            )

    def send_message_in_chat_nowait(self, message: str):
        asyncio.run_coroutine_threadsafe(self.send_message_in_chat(message), self._loop)

    async def _on_ready(self, ready_event: EventData):
        await ready_event.chat.join_room(self._channel)

        logger.info(f"Joined {self._channel}'s channel!")

        await self.send_message_in_chat(f"{BOT_TITLE}, reporting for duty! o7")

    async def _on_vote(self, cmd: ChatCommand):
        if not self._poll:
            return

        args = cmd.parameter.split(" ")

        if not len(args) or not len(cmd.parameter.strip()):
            # no choice
            return

        self._poll.add_vote(args[0], cmd.user.name, cmd.room.name)

    def start_poll(self, choices: list[str], timeout: int = 30):
        if self._poll:
            self.cancel_poll("Started another poll")

        self._poll = Poll(choices)

        choices = " | ".join(self._poll.choices_str)

        self.send_message_in_chat_nowait(
            f'New poll has started! Cast your vote by typing "!vote <choice>", where <choice> is the number corresponding to your choice: {choices}. Voting will end in {timeout} in-game seconds.'
        )

    def end_poll(self):
        if not self._poll:
            logger.warning("Tried to end poll, but no poll is running!")
            return

        winner_idx = self._poll.winner
        winner = self._poll.winner_str
        results = " | ".join(self._poll.results_str)

        self.send_message_in_chat_nowait(
            f'Poll has ended, "{winner}" won! Results: {results}'
        )

        self.connection.send_message("POLL_WINNER", {"winnerIdx": winner_idx})

        self._poll = None

    def cancel_poll(self, reason: str):
        if not self._poll:
            logger.warning(
                f"Tried to cancel poll (reason: {reason}), but no poll is running!"
            )
            return

        self.send_message_in_chat_nowait(f"Poll has been cancelled, reason: {reason}")

        self._poll = None

    # Overwatch integration part
    def on_connect(self):
        self.send_message_in_chat_nowait(
            "Successfully established connection with the Workshop mode!"
        )

    def on_error(self):
        self.send_message_in_chat_nowait("Failed to connect with the Workshop mode!")

    def on_message(self, type, data):
        match type:
            case "POLL_START":
                timeout, choices = data["timeout"], data["choices"]
                self.start_poll(choices=choices, timeout=timeout)

            case "POLL_END":
                self.end_poll()

            case "POLL_CANCEL":
                self.cancel_poll(data["reason"])

            case "SEND_MESSAGE":
                self.send_message_in_chat_nowait(data["message"])

    def on_message_error(self, message):
        self.send_message_in_chat_nowait(f"Failed sending message {message.name}!")

    def on_game_state_change(self, state):
        match state:
            case GameState.STARTED:
                self.send_message_in_chat_nowait(
                    f"New game has started - {self.overwatch.mode} on {self.overwatch.map}"
                )
            case GameState.IN_PROGRESS:
                # self.send_message_in_chat_nowait("Game is in progress")
                pass
            case GameState.IN_BETWEEN_ROUNDS:
                # self.send_message_in_chat_nowait("Game is in between rounds")
                pass
            case GameState.FINISHED:
                self.send_message_in_chat_nowait("Game has been finished")
            case GameState.CLOSED:
                self.cancel_poll("Lobby has been closed")
                # self.send_message_in_chat_nowait("Lobby has been closed")
