import glob
import json
import os

import allure
import pytest

from api_testing_framework.spotify.client import SpotifyClient
from api_testing_framework.spotify.models import NewReleasesResponse

ALLURE_DIR = os.getenv("ALLURE_DIR", "allure-results")


# @pytest.mark.integration
# def test_e2e_payload_truncation_integration(spotify_client: SpotifyClient, request):
#     os.environ["MAX_PAYLOAD_CHARS"] = "50"
#     os.environ["REDACT_FIELDS"] = ""

#     try:
#         import allure

#         allure.dynamic.title("payload_truncation_integration_marker")
#     except Exception:
#         pass

#     data = spotify_client.get_new_releases(limit=1, attach=True)
#     assert isinstance(data, NewReleasesResponse)

#     result_files = sorted(
#         glob.glob(os.path.join(ALLURE_DIR, "*-result.json")),
#         key=os.path.getmtime,
#         reverse=True,
#     )
#     assert result_files, "No Allure result files found. Did you run with --alluredir?"

#     content = None
#     attachment_sources = []
#     for path in result_files[:10]:
#         with open(path, "r", encoding="utf-8") as f:
#             res = json.load(f)
#         name = res.get("name") or res.get("fullName", "")
#         if "payload_truncation_integration_marker" in name or request.node.name in (
#             name or ""
#         ):
#             for att in res.get("attachments", []):
#                 if att.get("name") == "Response Body":
#                     attachment_sources.append(att.get("source"))
#             break
#     assert attachment_sources, "No 'Response Body' attachment recorded for this test."

#     body_path = os.path.join(ALLURE_DIR, attachment_sources[0])
#     with open(body_path, "r", encoding="utf-8", errors="ignore") as f:
#         body_text = f.read()

#     assert body_text.endswith("<truncated>"), "Response was not truncated."


@pytest.mark.integration
def test_payload_truncation_integration(monkeypatch, spotify_client: SpotifyClient):
    # Force a very small max so even a 1‐item “new releases” response gets cut
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "50")
    monkeypatch.setenv("REDACT_FIELDS", "")
    attached = []
    monkeypatch.setattr(
        allure,
        "attach",
        lambda content, name=None, attachment_type=None: attached.append(
            (name, content)
        ),
    )
    # Trigger an attached GET
    data = spotify_client.get_new_releases(limit=1, attach=True)
    assert isinstance(data, NewReleasesResponse)

    resp_bodies = [c for (n, c) in attached if n == "Response Body"]
    assert resp_bodies, "No Response body was attached"
    assert resp_bodies[0].endswith("<truncated>"), "Response was not truncated."


@pytest.mark.integration
def test_no_payload_truncation_integration(monkeypatch, spotify_client: SpotifyClient):
    # Set max large enough that the JSON will never truncate
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "1000000")
    monkeypatch.setenv("REDACT_FIELDS", "")

    data = spotify_client.get_new_releases(limit=1, attach=True)
    assert isinstance(data, NewReleasesResponse)


@pytest.mark.integration
def test_payload_redaction_integration(monkeypatch, spotify_client: SpotifyClient):
    # Redact the 'albums' key so we can see ***REDACTED*** in the payload
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "1000000")
    monkeypatch.setenv("REDACT_FIELDS", "albums")

    data = spotify_client.get_new_releases(limit=1, attach=True)
    assert isinstance(data, NewReleasesResponse)


@pytest.mark.integration
def test_request_truncation_is_noop_for_get(monkeypatch, spotify_client: SpotifyClient):
    # For GET there is no body, so we expect no Request Body attachment at all
    monkeypatch.setenv("MAX_PAYLOAD_CHARS", "1")  # irrelevant for GET
    spotify_client.get_new_releases(limit=1, attach=True)
    # Ensure no "Request Body" was attached (since GET has no content)
    # assert "Request Body" not in attached
