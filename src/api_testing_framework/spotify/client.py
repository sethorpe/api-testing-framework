import time
from typing import Optional

import httpx

from src.api_testing_framework.auth import fetch_spotify_token
from src.api_testing_framework.client import APIClient
from src.api_testing_framework.config import get_settings
from src.api_testing_framework.spotify.models import (
    NewReleasesResponse,
    TopTracksResponse,
)


class SpotifyClient(APIClient):
    """
    Spotify-specific client: handles OAuth and endpoint helpers
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        cfg = get_settings()
        actual_base = base_url or cfg.spotify_api_base_url

        if token:
            init_token = token
            expires_at = float("inf")
        else:
            init_token, expires_in = fetch_spotify_token(
                cfg.spotify_client_id,
                cfg.spotify_client_secret,
            )
            expires_at = time.time() + expires_in - 10

        super().__init__(
            base_url=actual_base, token=init_token, timeout=timeout, transport=transport
        )

        self._token_expires_at = expires_at
        self._cfg = cfg

    def _refresh_token_if_needed(self):
        if time.time() >= self._token_expires_at:
            self._token, expires_in = fetch_spotify_token(
                self._cfg.spotify_client_id,
                self._cfg.spotify_client_secret,
            )
            self._token_expires_at = time.time() + expires_in - 10
            self._client.headers["Authorization"] = f"Bearer {self._token}"

    def get_new_releases(self, limit: int = 20) -> NewReleasesResponse:
        """
        Fetch new album releases from Spotify and return a validated model.
        """
        raw = self.get(f"/browse/new-releases?limit={limit}")
        return NewReleasesResponse.model_validate(raw)

    def get_artist_top_tracks(
        self, artist_id: str, market: str = "US"
    ) -> TopTracksResponse:
        """
        Fetch the top tracks for a given artist in the specified market.
        """
        raw = self.get(f"/artists/{artist_id}/top-tracks?market={market}")
        return TopTracksResponse.model_validate(raw)
