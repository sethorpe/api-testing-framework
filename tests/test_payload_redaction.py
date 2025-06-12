# tests/test_payload_redaction.py

import allure
import httpx
import pytest

from api_testing_framework.client import APIClient


class SensitiveTransport(httpx.BaseTransport):
    def handle_request(self, request):
        payload = {"token": "secret123", "nested": {"password": "p@ss"}}
        return httpx.Response(200, json=payload)


def test_redaction_of_fields(monkeypatch):
    attached = []
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "1000")
    monkeypatch.setenv("REDACT_FIELDS", "token,password")
    monkeypatch.setattr(
        allure,
        "attach",
        lambda content, name=None, attachment_type=None: attached.append(
            (name, content)
        ),
    )

    client = APIClient(
        base_url="https://api.example.com",
        transport=SensitiveTransport(),
        token="dummy",
    )
    data = client.get("/sensitive", attach=True)
    assert data["token"] == "secret123"  # client still returns real data

    # Check the attached, sanitized body
    resp_bodies = [c for (n, c) in attached if n == "Response Body"]
    assert len(resp_bodies) == 1
    body = resp_bodies[0]
    assert '"token": "***REDACTED***"' in body
    assert '"password": "***REDACTED***"' in body
    # Ensure no raw secrets remain
    assert "secret123" not in body
    assert "p@ss" not in body
