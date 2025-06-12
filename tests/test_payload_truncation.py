import os

import allure
import httpx
import pytest

from api_testing_framework.client import APIClient


class LargeBodyTransport(httpx.BaseTransport):
    """
    Transport that returns a large JSON payload to test function
    """

    def handle_request(self, request):
        large_list = ["x" * 200] * 50
        return httpx.Response(200, json={"data": large_list})


@pytest.fixture(autouse=True)
def set_small_truncation_threshold(monkeypatch):
    """
    Reduce the truncation threshold for testing purposes
    """
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "500")
    monkeypatch.setenv("REDACT_FIELDS", "")
    yield
    monkeypatch.delenv("MAX_PAYLOAD_CHARS", raising=False)
    monkeypatch.delenv("REDACT_FIELDS", raising=False)


def test_payload_truncation(monkeypatch):
    """
    Verify that response bodies exceeding MAX_PAYLOAD_CHARS are truncated in Allure attachments.
    """
    attached = []

    def fake_attach(content, name=None, attachment_type=None):
        if name == "Response Body":
            attached.append(content)

    monkeypatch.setattr(allure, "attach", fake_attach)

    client = APIClient(
        base_url="https://api.example.com",
        transport=LargeBodyTransport(),
        token="dummy",
    )

    data = client.get("/large-payload", attach=True)

    assert "data" in data
    assert len(attached) == 1
    body_attachment = attached[0]

    assert body_attachment.endswith("<truncated>"), "Payload was not truncated"
    assert len(body_attachment) <= 550, "Truncated payload too large"
