# tests/test_no_truncation.py

import allure
import httpx
import pytest

from api_testing_framework.client import APIClient


class SmallBodyTransport(httpx.BaseTransport):
    def handle_request(self, request):
        data = {"msg": "hello"}  # tiny payload
        return httpx.Response(200, json=data)


def test_small_payload_no_truncation(monkeypatch):
    attached = []
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "100")  # threshold > small body
    monkeypatch.setenv("REDACT_FIELDS", "")
    monkeypatch.setattr(
        allure,
        "attach",
        lambda content, name=None, attachment_type=None: attached.append(
            (name, content)
        ),
    )

    client = APIClient(
        base_url="https://api.example.com",
        transport=SmallBodyTransport(),
        token="dummy",
    )
    data = client.get("/small", attach=True)
    assert data == {"msg": "hello"}

    # Find the Response Body attachment
    resp_bodies = [c for (n, c) in attached if n == "Response Body"]
    assert len(resp_bodies) == 1
    assert "<truncated>" not in resp_bodies[0]
    assert '"msg": "hello"' in resp_bodies[0]
