"""Module for a wrapper around YouTube API v3"""

from google.oauth2.credentials import Credentials

from .grpc import YouTubeGrpcApi
from .rest import YouTubeRestApi


class YouTubeApi(YouTubeRestApi, YouTubeGrpcApi):
    """Simple wrapper around some YouTube API v3 endpoints."""

    def __init__(self, credentials: Credentials):
        self._credentials = credentials

        super().__init__()
