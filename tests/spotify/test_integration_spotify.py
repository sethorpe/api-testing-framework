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


@pytest.mark.integration
def test_spotify_artist_top_tracks_w_attachments(spotify_client: SpotifyClient):
    artist_id = "6eUKZXaKkcviH0Ku9w2n3V"
    response = spotify_client.get_artist_top_tracks(artist_id=artist_id, attach=True)
    assert response.tracks
    tracks = response.tracks
    assert isinstance(tracks, list) and len(tracks) > 0

    for track in tracks:
        assert track.id and track.name and isinstance(track.popularity, int)


@pytest.mark.integration
def test_spotify_new_releases_w_attachments(spotify_client: SpotifyClient):
    response = spotify_client.get_new_releases(limit=3, attach=True)
    assert response.albums.items
    items = response.albums.items
    assert isinstance(items, list) and len(items) == 3

    for album in items:
        assert album.id and album.name
