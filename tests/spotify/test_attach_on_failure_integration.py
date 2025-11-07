"""
Real-world integration test for ATTACH_ON_FAILURE feature.
Tests against live Spotify API with no mocking or monkeypatching.
"""
import os

import pytest

from api_testing_framework.exceptions import APIError


@pytest.fixture(autouse=True)
def enable_attach_on_failure(monkeypatch):
    """Enable ATTACH_ON_FAILURE for this test module."""
    monkeypatch.setenv("ATTACH_ON_FAILURE", "true")
    yield
    monkeypatch.delenv("ATTACH_ON_FAILURE", raising=False)


@pytest.mark.integration
def test_attach_on_failure_with_valid_spotify_request(spotify_client):
    """
    Test ATTACH_ON_FAILURE records exchanges on successful API calls.
    Uses real Spotify API - no mocking.
    """
    # Clear any previous state
    spotify_client._last_request = None
    spotify_client._last_response = None

    # Make a real API call to Spotify
    result = spotify_client.get("/search", params={"q": "test", "type": "track", "limit": 1})

    # Verify the exchange was recorded (ATTACH_ON_FAILURE=true)
    assert spotify_client._last_request is not None, "Request should be recorded with ATTACH_ON_FAILURE=true"
    assert spotify_client._last_response is not None, "Response should be recorded with ATTACH_ON_FAILURE=true"

    # Verify request details
    assert spotify_client._last_request.method == "GET"
    assert "/search" in str(spotify_client._last_request.url)

    # Verify response details
    assert spotify_client._last_response.status_code == 200
    assert spotify_client._last_response.is_success

    # Verify actual API response structure
    assert "tracks" in result
    assert isinstance(result["tracks"], dict)


@pytest.mark.integration
def test_attach_on_failure_with_invalid_spotify_endpoint(spotify_client):
    """
    Test ATTACH_ON_FAILURE records exchanges when API call fails.
    Uses real Spotify API with invalid endpoint - no mocking.
    """
    # Clear any previous state
    spotify_client._last_request = None
    spotify_client._last_response = None

    # Make a real API call to an invalid Spotify endpoint
    with pytest.raises(APIError) as exc_info:
        spotify_client.get("/this-endpoint-does-not-exist")

    # Verify the exchange was recorded even on failure
    assert spotify_client._last_request is not None, "Request should be recorded on failure"
    assert spotify_client._last_response is not None, "Response should be recorded on failure"

    # Verify request details
    assert spotify_client._last_request.method == "GET"
    assert "/this-endpoint-does-not-exist" in str(spotify_client._last_request.url)

    # Verify response details - should be 404 or similar error
    assert not spotify_client._last_response.is_success
    assert spotify_client._last_response.status_code >= 400

    # Verify exception contains error info
    api_error = exc_info.value
    assert api_error.status_code >= 400


@pytest.mark.integration
def test_attach_on_failure_without_flag(spotify_client, monkeypatch):
    """
    Test that exchanges are NOT recorded when ATTACH_ON_FAILURE=false.
    Uses real Spotify API - no mocking.
    """
    # Disable ATTACH_ON_FAILURE
    monkeypatch.setenv("ATTACH_ON_FAILURE", "false")

    # Clear any previous state
    spotify_client._last_request = None
    spotify_client._last_response = None

    # Make a real API call to Spotify
    result = spotify_client.get("/search", params={"q": "test", "type": "track", "limit": 1})

    # Verify the exchange was NOT recorded (ATTACH_ON_FAILURE=false)
    assert spotify_client._last_request is None, "Request should NOT be recorded with ATTACH_ON_FAILURE=false"
    assert spotify_client._last_response is None, "Response should NOT be recorded with ATTACH_ON_FAILURE=false"

    # Verify API call still worked
    assert "tracks" in result
    assert isinstance(result["tracks"], dict)
