import httpx
import pytest

from api_testing_framework.client import APIClient


class DummyTransport(httpx.BaseTransport):
    def handle_request(self, request):
        return httpx.Response(200, json={"ok": True})


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
