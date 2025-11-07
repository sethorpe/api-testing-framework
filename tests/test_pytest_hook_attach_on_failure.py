import allure
import httpx
import pytest

from api_testing_framework.client import APIClient
from api_testing_framework.exceptions import APIError


class ErrorTransport(httpx.BaseTransport):
    """Dummy transport that always returns 500 with a JSON error body."""

    def handle_request(self, request):
        return httpx.Response(500, json={"error": "internal_server_error"})


@pytest.fixture(autouse=True)
def enable_global_recording(monkeypatch):
    """Turn on the ATTACH_ON_FAILURE flag for every test in this module."""
    monkeypatch.setenv("ATTACH_ON_FAILURE", "true")
    yield
    monkeypatch.delenv("ATTACH_ON_FAILURE", raising=False)


@pytest.fixture
def api_client(request):
    """
    Override the global api_client fixture with one that uses ErrorTransport,
    and register it on the pytest node for the makereport hook.
    """
    client = APIClient(
        base_url="https://doesnotmatter.local",
        transport=ErrorTransport(),
        token="dummy-token",
    )
    # Bind it so pytest_runtest_makereport can find it:
    request.node._api_client = client
    return client


def test_pytest_hook_attaches_on_failure(monkeypatch, api_client):
    # Capture the names of all allure.attach calls:
    attached = []
    monkeypatch.setattr(
        allure,
        "attach",
        lambda content, name=None, attachment_type=None: attached.append(name),
    )

    # Invoke a GET that 500s (no per-call attach=True)
    with pytest.raises(APIError):
        api_client.get("/endpoint-that-errors")

    # Manually trigger what the pytest hook would do
    # (The real hook runs after test completion, so we simulate it here)
    api_client._attach_last_exchange_to_allure()

    # Assert that the hook attached the five expected pieces:
    expected = {
        "HTTP Request",
        "Request Headers",
        "HTTP Response Status",
        "Response Headers",
        "Response Body",
    }
    missing = expected - set(attached)
    assert not missing, f"Missing attachments: {missing}"
