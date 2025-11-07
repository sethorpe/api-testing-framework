import pytest

from api_testing_framework.client import APIClient


@pytest.mark.unit
def test_manual_attach_using_swapi():
    client = APIClient(base_url="https://www.swapi.tech/api", token=None)
    data = client.get("/people", attach=True)
    assert "total_records" in data
