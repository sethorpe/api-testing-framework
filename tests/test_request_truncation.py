# tests/test_request_truncation.py

import allure
import httpx
import pytest

from api_testing_framework.client import APIClient


class LargePostTransport(httpx.BaseTransport):
    def handle_request(self, request):
        # Echo back the JSON we sent
        try:
            import json

            body = json.loads(request.content.decode("utf-8"))
        except Exception:
            body = {}
        return httpx.Response(200, json=body)


def test_request_body_truncation(monkeypatch):
    attached = []
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "100")
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
        transport=LargePostTransport(),
        token="dummy",
    )

    # Build a large JSON body
    large_data = {"data": ["x" * 50 for _ in range(5)]}  # ~250 chars
    response = client.post("/echo", json=large_data, attach=True)
    assert response == large_data

    # Extract Request Body attachment
    req_bodies = [c for (n, c) in attached if n == "Request Body"]
    assert len(req_bodies) == 1
    body = req_bodies[0]
    assert "<truncated>" in body
    assert len(body) <= 150  # threshold + marker
