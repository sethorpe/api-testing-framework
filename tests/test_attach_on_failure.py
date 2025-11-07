import os

import allure
import httpx
import pytest

from api_testing_framework.client import APIClient
from api_testing_framework.exceptions import APIError


class ErrorTransport(httpx.BaseTransport):
    """Always returns HTTP 500 with a simple JSON error body"""

    def handle_request(self, request):
        return httpx.Response(500, json={"error": "internal_server_error"})


@pytest.fixture(autouse=True)
def enable_attach_on_failure(monkeypatch):
    """
    Automatically enable the ATTACH_ON_FAILURE flag for this test module.
    """
    monkeypatch.setenv("ATTACH_ON_FAILURE", "true")
    yield
    monkeypatch.delenv("ATTACH_ON_FAILURE", raising=False)


def test_http_exchange_attached_on_error(monkeypatch, request):
    attached = []

    monkeypatch.setattr(
        allure, "attach", lambda content, name, attachment_type: attached.append(name)
    )

    client = APIClient(
        base_url="https://api.example.com",
        transport=ErrorTransport(),
        token="dummy-token",
    )
    request.node._api_client = client

    # Make API call that errors (with ATTACH_ON_FAILURE=true)
    with pytest.raises(APIError):
        client.get("/endpoint-that-errors")

    # Manually trigger what the pytest hook would do
    # (The real hook runs after test completion, so we simulate it here)
    client._attach_last_exchange_to_allure()

    expected = {
        "HTTP Request",
        "Request Headers",
        "HTTP Response Status",
        "Response Headers",
        "Response Body",
    }
    assert expected.issubset(
        set(attached)
    ), f"Missing attachments: {expected - set(attached)}"
