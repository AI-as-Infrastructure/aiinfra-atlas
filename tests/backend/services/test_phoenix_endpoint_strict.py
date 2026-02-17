import pytest

from backend.services.phoenix_client import PhoenixAPIClient


def test_get_phoenix_endpoint_requires_env(monkeypatch):
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)

    client = PhoenixAPIClient()

    with pytest.raises(ValueError, match="PHOENIX_COLLECTOR_ENDPOINT is not configured"):
        client._get_phoenix_endpoint()


def test_get_phoenix_endpoint_requires_space_path_for_cloud(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com")

    client = PhoenixAPIClient()

    with pytest.raises(ValueError, match="must include '/s/<space-id>'"):
        client._get_phoenix_endpoint()


def test_get_phoenix_endpoint_accepts_space_url(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/s/aiinfra/")

    client = PhoenixAPIClient()

    endpoint = client._get_phoenix_endpoint()

    assert endpoint == "https://app.phoenix.arize.com/s/aiinfra"


def test_get_phoenix_endpoint_accepts_explicit_override_url(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://phoenix.internal.company")

    client = PhoenixAPIClient()

    endpoint = client._get_phoenix_endpoint()

    assert endpoint == "https://phoenix.internal.company"
