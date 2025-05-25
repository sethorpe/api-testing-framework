import httpx
import pytest

from api_testing_framework.client import APIClient
from api_testing_framework.models import TopTracksResponse


class DummyTopTracksTransport(httpx.BaseTransport):
    def handle_request(self, request):
        return httpx.Response(
            200,
            json={
                "tracks": [
                    {
                        "id": "trk1",
                        "name": "Track One",
                        "album": {
                            "id": "alb1",
                            "name": "Album One",
                            "album_type": "single",
                            "release_date": "2025-05-01",
                            "total_tracks": 1,
                            "images": [
                                {"url": "https://img", "height": 300, "width": 300}
                            ],
                            "artists": [{"id": "art1", "name": "Artist One"}],
                        },
                        "artists": [{"id": "art1", "name": "Artist One"}],
                        "popularity": 50,
                        "preview_url": None,
                    }
                ]
            },
        )

    @pytest.fixture
    def client():
        return APIClient(
            base_url="https://api.example.com",
            token="dummy-token",
            transport=DummyTopTracksTransport(),
        )

    def test_get_artist_top_tracks(client: APIClient):
        resp = client.get_artist_top_tracks("artist123", market="US")
        assert isinstance(resp, TopTracksResponse)
        assert resp.tracks[0].id == "trk1"
        assert resp.tracks[0].album.id == "alb1"
        assert resp.tracks[0].popularity == 50
