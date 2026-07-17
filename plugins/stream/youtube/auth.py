"""User authorization module"""

import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import (  # pyright: ignore[reportMissingTypeStubs]
    InstalledAppFlow,
)

from src import PROJECT_ROOT, create_logger

logger = create_logger("YouTube.Auth")

TOKENS_PATH = os.path.join(PROJECT_ROOT, "tokens_youtube.json")
SCOPES = ["https://www.googleapis.com/auth/youtube"]


def refresh_credentials(credentials: Credentials):
    """Refreshes `credentials`."""
    logger.info("OAuth 2.0 credentials expired, refreshing...")
    credentials.refresh(Request())


def refresh_credentials_if_necessary(credentials: Credentials):
    """Refreshes `credentials` if necessary."""
    if credentials.expired:
        refresh_credentials(credentials)

    if not credentials.valid or not isinstance(credentials.token, str):
        raise RuntimeError("Invalid OAuth 2.0 credentials")


def authorize(secrets: dict[str, Any]):
    """Authorizes the user."""
    credentials: Credentials | None = None

    if os.path.isfile(TOKENS_PATH):
        try:
            credentials = Credentials.from_authorized_user_file(TOKENS_PATH)
        except BaseException:
            logger.warning(
                "Failed to generate OAuth 2.0 credentials from tokens_youtube.json file!"
            )

    if not credentials:
        try:
            flow = InstalledAppFlow.from_client_config(secrets, SCOPES)
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

    with open(TOKENS_PATH, mode="w", encoding="utf-8") as file:
        file.write(credentials.to_json())
        file.close()

    return credentials
