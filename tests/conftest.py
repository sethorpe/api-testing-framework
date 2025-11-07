import os
import uuid

import allure
import pytest

from api_testing_framework.client import APIClient
from tests.utils_allure import find_attachment_path, wait_for_result_with_label


@pytest.fixture
def api_client(request):
    """
    Provide a SpotifyClient (or a generic APIClient subclass). If ATTACH_ON_FAILURE is set,
    APIClient will record each exchane. We attach this instance to the test node so
    a pytest hook can retrieve and attach exchanges only on failure.
    """

    client = APIClient(base_url="https://api.example.com", token=None)

    request.node._api_client = client
    return client


def pytest_runtest_makereport(item, call):
    """
    After each test's 'call' phase, if the test failed and the client recorded an exchange,
    attach it to Allure.
    """
    if call.when != "call":
        return

    if call.excinfo is None:
        return

    api_client = getattr(item, "_api_client", None)
    if isinstance(api_client, APIClient):
        api_client._attach_last_exchange_to_allure()


@pytest.fixture
def require_alluredir(pytestconfig):
    allure_dir = pytestconfig.getoption("--alluredir", default=None)
    if not allure_dir:
        pytest.skip(
            "This test requires --alluredir=<dir> (no Allure artifacts otherwise)"
        )
    return allure_dir


@pytest.fixture
def assert_truncated_response_after_test(require_alluredir, request):
    """
    After the test finishes, locate THIS test's result by a label the test sets,
    then verify the 'Response Body' attachment ends with '<truncated>'.
    """
    # The test will set this label on itself (see test code below)
    LABEL_NAME = "nodeid"
    LABEL_VALUE = request.node.nodeid

    yield  # --- test body runs here ---

    res = wait_for_result_with_label(
        require_alluredir, LABEL_NAME, LABEL_VALUE, timeout=12.0
    )
    assert res, f"No Allure result found for label {LABEL_NAME}={LABEL_VALUE}."

    body_path = find_attachment_path(res, require_alluredir, "Response Body")
    assert body_path, "No 'Response Body' attachment found in this test's result."

    with open(body_path, "r", encoding="utf-8", errors="ignore") as f:
        body = f.read()
    assert body.endswith("<truncated>"), "Response body was not truncated."


# @pytest.fixture
# def assert_truncated_after_test(require_alluredir, request):
#     """
#     Attach a unique marker at the start (so we can find THIS test's result),
#     let the test run, then (after teardown) assert the 'Response Body' was truncated.
#     """
#     marker = f"ATTACHMENT_MARKER:{uuid.uuid4()}"
#     allure.attach("marker", name=marker, attachment_type=allure.attachment_type.TEXT)

#     yield  # <-- test body runs here

#     res = wait_for_result_with_marker(require_alluredir, marker, timeout=12.0)
#     assert res, "No Allure result found for this test (race or mssing --alluredir)."

#     body_path = find_attachment_by_name_in_result(
#         res, require_alluredir, "Response Body"
#     )
#     assert body_path, "No 'Response Body' attachment found in this test's result."

#     with open(body_path, "r", encoding="utf-8", errors="ignore") as f:
#         body = f.read()
#     assert body.endswith("<truncated>"), "Response Body was not truncated."
