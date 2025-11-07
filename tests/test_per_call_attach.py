import allure
import httpx
import pytest

from api_testing_framework.client import APIClient
from api_testing_framework.exceptions import APIError


class ErrorTransport(httpx.BaseTransport):
    """Always return HTTP 500 with a JSON error body."""

    def handle_request(self, request):
        return httpx.Response(500, json={"error": "server_error"})


class BodyTransport(httpx.BaseTransport):
    """Always returns HTTP 400 with a JSON error body."""

    def handle_request(self, request):
        return httpx.Response(400, json={"error": "bad_request"})


def test_per_call_attach_on_error(monkeypatch):
    # Capture all attachment names
    attached = []
    monkeypatch.setattr(
        allure, "attach", lambda content, name, attachment_type: attached.append(name)
    )

    # Create a client that will error
    client = APIClient(
        base_url="https://api.example.com",
        transport=ErrorTransport(),
        token="dummy-token",
    )

    # Call with attach=True; expect APIError and attachments recorded immediately
    with pytest.raises(APIError):
        client.get("/endpoint-fails", attach=True)

    # Verify we saw the key HTTP attachment names
    expected = {
        "HTTP Request",
        "Request Headers",
        "HTTP Response Status",
        "Response Headers",
        "Response Body",
    }
    missing = expected - set(attached)
    assert not missing, f"Missing attachments: {missing}"


def test_per_call_attach_post_with_body(monkeypatch):
    attached = []

    # Define a fake attach that accepts keyword args
    def fake_attach(content, name=None, attachment_type=None):
        attached.append(name)

    monkeypatch.setattr(allure, "attach", fake_attach)

    client = APIClient(
        base_url="https://api.example.com",
        transport=BodyTransport(),
        token="dummy-token",
    )

    with pytest.raises(APIError):
        client.post("/fails", json={"foo": "bar"}, attach=True)

    # Now you *should* see Request Body attached, along with the others
    expected = {
        "HTTP Request",
        "Request Headers",
        "Request Body",
        "HTTP Response Status",
        "Response Headers",
        "Response Body",
    }
    missing = expected - set(attached)
    assert not missing, f"Missing attachments: {missing}"
