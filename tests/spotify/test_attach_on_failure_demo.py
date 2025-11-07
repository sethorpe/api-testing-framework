"""
Demo test that intentionally fails to show ATTACH_ON_FAILURE in action.
This test should be run manually to see attachments in Allure report.
"""
import os

import pytest


@pytest.fixture(autouse=True)
def enable_attach_on_failure(monkeypatch):
    """Enable ATTACH_ON_FAILURE for this test module."""
    monkeypatch.setenv("ATTACH_ON_FAILURE", "true")
    yield
    monkeypatch.delenv("ATTACH_ON_FAILURE", raising=False)


@pytest.mark.integration
@pytest.mark.skip(reason="Demo test - unskip to see ATTACH_ON_FAILURE in action")
def test_intentional_failure_to_demo_attach_on_failure(api_client):
    """
    This test intentionally fails to demonstrate ATTACH_ON_FAILURE.

    When this test fails:
    1. The pytest hook detects the failure
    2. It finds the api_client attached to the test node
    3. It calls _attach_last_exchange_to_allure()
    4. The HTTP request/response appear in the Allure report

    To see it in action:
    1. Remove the @pytest.mark.skip decorator
    2. Run: poetry run pytest tests/spotify/test_attach_on_failure_demo.py --alluredir=allure-results
    3. Run: make serve-report
    4. Check the Allure report for this failing test - it will have HTTP attachments
    """
    # Make a real API call
    result = api_client.get("/search", params={"q": "test", "type": "track", "limit": 1})

    # Verify the exchange was recorded
    assert api_client._last_request is not None
    assert api_client._last_response is not None

    # This assertion intentionally fails to trigger the pytest hook
    assert False, "Intentional failure to demonstrate ATTACH_ON_FAILURE - check Allure report for HTTP attachments!"
