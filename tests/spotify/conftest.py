import pytest

from api_testing_framework.config import get_settings
from api_testing_framework.spotify.client import SpotifyClient

CFG = get_settings()


@pytest.fixture(scope="session")
def spotify_client():
    """
    Fixture for real SpotifyClient integration tests.
    Skips if SPOTIFY_CLIENT_ID/SECRET are not set.
    """
    if not CFG.spotify_client_id or not CFG.spotify_client_secret:
        pytest.skip("Spotify credentials not set; skipping integration tests")
    return SpotifyClient(
        base_url=CFG.spotify_api_base_url,
    )


@pytest.fixture
def api_client(request):
    """
    Provide a SpotifyClient (or a generic APIClient subclass). If ATTACH_ON_FAILURE is set,
    APIClient will record each exchane. We attach this instance to the test node so
    a pytest hook can retrieve and attach exchanges only on failure.
    """

    # cfg = get_settings()
    client = SpotifyClient(base_url=CFG.spotify_api_base_url, token=None)

    request.node._api_client = client
    return client
