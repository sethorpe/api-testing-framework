import httpx
import pytest

from api_testing_framework.spotify.client import SpotifyClient
from api_testing_framework.spotify.models import NewReleasesResponse


class DummyNewReleasesTransport(httpx.BaseTransport):
    def handle_request(self, request):
        return httpx.Response(
            200,
            json={
                "albums": {
                    "href": "https://api.example.com/browse/new-releases?limit=1",
                    "items": [
                        {
                            "album_type": "album",
                            "artists": [{"id": "artist1", "name": "Artist One"}],
                            "id": "album1",
                            "name": "Album One",
                            "release_date": "2025-05-01",
                            "total_tracks": 10,
                            "images": [
                                {
                                    "url": "https://example.com/img.jpg",
                                    "height": 640,
                                    "width": 640,
                                }
                            ],
                        }
                    ],
                    "limit": 1,
                    "next": None,
                    "offset": 0,
                    "previous": None,
                    "total": 100,
                }
            },
        )

    @pytest.fixture
    def client():
        return SpotifyClient(
            base_url="https://api.example.com",
            token="dummy-token",
            transport=DummyNewReleasesTransport(),
        )

    def test_get_new_releases_returns_valid_model(client: SpotifyClient):
        result = client.get_new_releases(limit=1)
        assert isinstance(result, NewReleasesResponse)
        album = result.albums.items[0]
        assert album.id == "album1"
        assert album.name == "Album One"
        assert result.albums.limit == 1
