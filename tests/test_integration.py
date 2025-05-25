import pytest
from pydantic import ValidationError

from api_testing_framework.client import APIClient
from api_testing_framework.config import get_settings
from api_testing_framework.models import NewReleasesResponse


@pytest.mark.integration
def test_spotify_new_releases():
    client = APIClient()
    raw = client.get("/browse/new-releases?limit=1")
    try:

        parsed = NewReleasesResponse.model_validate(raw)
        assert parsed.albums.items, "Expect at least one album"
        first = parsed.albums.items[0]
        assert first.id
        assert first.name

    except ValidationError as e:
        raise


@pytest.mark.integration
def test_spotify_artist_top_tracks():
    client = APIClient()
    parsed = client.get_artist_top_tracks("3TVXtAsR1Inumwj472S9r4")
    assert parsed.tracks, "Expected at least one track"
    assert parsed.tracks[0].id
    assert parsed.tracks[0].name
