import pytest

from api_testing_framework.spotify.client import SpotifyClient


@pytest.mark.integration
def test_spotify_new_releases():
    client = SpotifyClient()
    parsed = client.get_new_releases(limit=1)
    assert parsed.albums.items


@pytest.mark.integration
def test_spotify_artist_top_tracks():
    client = SpotifyClient()
    parsed = client.get_artist_top_tracks("3TVXtAsR1Inumwj472S9r4")
    assert parsed.tracks
