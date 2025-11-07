import os

import allure
import pytest

from api_testing_framework.spotify.client import SpotifyClient
from api_testing_framework.spotify.models import NewReleasesResponse


@pytest.mark.integration
def test_payload_truncation_integration(
    spotify_client: SpotifyClient, assert_truncated_response_after_test, request
):
    allure.dynamic.label("nodeid", request.node.nodeid)

    os.environ["MAX_PAYLOAD_CHARS"] = "50"
    os.environ["REDACT_FIELDS"] = ""

    data = spotify_client.get_new_releases(limit=1, attach=True)
    assert isinstance(data, NewReleasesResponse)
