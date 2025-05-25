import time
from typing import Any, Dict, Optional

import httpx

from api_testing_framework.auth import fetch_spotify_token
from api_testing_framework.config import get_settings
from api_testing_framework.exceptions import APIError
from api_testing_framework.models import NewReleasesResponse, TopTracksResponse


class APIClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: float = 10.0,
        transport: Optional[httpx.BaseTransport] = None,
    ):
        # Determine base URL
        self.cfg = None
        if base_url is None or token is None:
            self.cfg = get_settings()

        self.base_url = (base_url or self.cfg.spotify_api_base_url).rstrip("/")
        # Fetch or use the provided token
        if token:
            self._token = token
            # Never refresh a user-supplied token
            self._token_expires_at = float("inf")
        else:
            # self.cfg must be set here
            assert self.cfg is not None
            self._token, expires_in = fetch_spotify_token(
                self.cfg.spotify_client_id,
                self.cfg.spotify_client_secret,
            )
            self._token_expires_at = time.time() + expires_in - 10  # buffer

        client_args: Dict[str, Any] = {
            "base_url": self.base_url,
            "headers": {"Authorization": f"Bearer {self._token}"},
            "timeout": timeout,
        }
        if transport is not None:
            client_args["transport"] = transport

        self._client = httpx.Client(**client_args)

    def _refresh_token_if_needed(self):
        if time.time() >= self._token_expires_at:
            self._token, expires_in = fetch_spotify_token(
                self.cfg.spotify_client_id,
                self.cfg.spotify_client_secret,
            )
            self._token_expires_at = time.time() + expires_in - 10
            self._client.headers["Authorization"] = f"Bearer {self._token}"

    def _handle_response(self, response: httpx.Response) -> dict:
        data = response.json()
        if not response.is_success:
            raise APIError(response.status_code, data.get("error", response.text), data)
        return data

    def get(self, path: str, params: Dict[str, Any] = None) -> dict:
        self._refresh_token_if_needed()
        resp = self._client.get(path, params=params)
        return self._handle_response(resp)

    def post(self, path: str, json: Dict[str, Any] = None) -> dict:
        self._refresh_token_if_needed()
        resp = self._client.post(path, json=json)
        return self._handle_response(resp)

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
