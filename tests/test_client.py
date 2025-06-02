import allure
import httpx
import pytest

from api_testing_framework.client import APIClient
from api_testing_framework.exceptions import APIError


class DummyTransport(httpx.BaseTransport):
    def handle_request(self, request):
        return httpx.Response(200, json={"ok": True})


class ErrorTransport(httpx.BaseTransport):
    """A dummy transport that always returns HTTP 500 with a JSON body"""

    def handle_request(self, request):
        return httpx.Response(500, json={"error": "internal_server_error"})


@pytest.fixture
def client():
    return APIClient(
        transport=DummyTransport(),
        base_url="https://api.example.com",
        token="token",
        timeout=1.0,
    )


def test_get_returns_response(client):
    data = client.get("/foo")
    assert data == {"ok": True}


def test_allure_attachment(client):
    data = client.get("/bar", attach=True)
    assert data == {"ok": True}


def test_allure_without_attachment(client):
    data = client.get("/foo")
    assert data == {"ok": True}


def test_attach_on_500_response(monkeypatch):
    """
    Verify that when the server returns a 500, calling client.get(..., attach=True)
    raises APIError and triggers Allure attachments for request/response.
    """
    attached = []

    def fake_attach(content, name, attachment_type):
        attached.append((name, content))

    monkeypatch.setattr(allure, "attach", fake_attach)

    client = APIClient(
        base_url="https://api.example.com",
        transport=ErrorTransport(),
        token="dummy-token",
    )

    with pytest.raises(APIError):
        client.get("/endpoint-that-errors", attach=True)

    assert attached, "Expected at least one Allure attachment on 500 error"

    attachment_names = {name for (name, _) in attached}
    expected_names = {
        "HTTP Request",
        "Request Headers",
        "HTTP Response Status",
        "Response Headers",
        "Response Body",
    }

    assert expected_names.issubset(
        attachment_names
    ), f"Missing attachment(s): {expected_names - attachment_names}"
