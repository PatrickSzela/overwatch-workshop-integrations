"""User authorization module"""

import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import (  # pyright: ignore[reportMissingTypeStubs]
    InstalledAppFlow,
)

from logger import create_logger

logger = create_logger("YouTube.Auth")

SCOPES = ["https://www.googleapis.com/auth/youtube"]


def refresh_credentials(credentials: Credentials):
    """Refreshes `credentials`."""
    logger.info("OAuth 2.0 credentials expired, refreshing...")
    credentials.refresh(Request())


def refresh_credentials_if_necessary(credentials: Credentials):
    """Refreshes `credentials` if necessary."""
    if credentials.expired:
        refresh_credentials(credentials)

    if not credentials.valid:
        raise RuntimeError("Invalid OAuth 2.0 credentials")


def authorize():
    """Authorizes the user."""
    credentials: Credentials | None = None

    if os.path.isfile("./youtube_creds.json"):
        try:
            credentials = Credentials.from_authorized_user_file("youtube_creds.json")
        except BaseException:  # pylint: disable=W0718
            logger.warning(
                "Failed to generate OAuth 2.0 credentials from youtube_creds.json file!"
            )

    if not credentials:
        flow = InstalledAppFlow.from_client_secrets_file("youtube_secret.json", SCOPES)

        try:
            cred = flow.run_local_server()

            if isinstance(cred, Credentials):
                credentials = cred
            else:
                raise RuntimeError("External accounts not supported!")
        except BaseException as e:
            raise RuntimeError("Failed to authorize user!") from e

    if credentials.expired:
        refresh_credentials(credentials)

    if not credentials.valid or not credentials.token:
        raise RuntimeError("Invalid OAuth 2.0 credentials!")

    with open("./youtube_creds.json", mode="w", encoding="utf-8") as file:
        file.write(credentials.to_json())
        file.close()

    return credentials
