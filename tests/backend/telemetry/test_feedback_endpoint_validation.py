import pytest
from unittest.mock import AsyncMock, Mock, patch
import sys
import types

from backend.telemetry.feedback import submit_span_annotation


@pytest.mark.asyncio
async def test_submit_span_annotation_fails_without_endpoint(monkeypatch):
    monkeypatch.delenv("PHOENIX_COLLECTOR_ENDPOINT", raising=False)
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")

    result = await submit_span_annotation("123", {"feedback_text": "hello"}, "qa-1")

    assert result is False


@pytest.mark.asyncio
async def test_submit_span_annotation_fails_without_space_path(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com")
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")

    result = await submit_span_annotation("123", {"feedback_text": "hello"}, "qa-1")

    assert result is False


@pytest.mark.asyncio
async def test_submit_span_annotation_uses_space_endpoint(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/s/aiinfra")
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")

    mock_response = Mock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client
    mock_context.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_context):
        result = await submit_span_annotation("123", {"feedback_text": "hello"}, "qa-1")

    assert result is True
    post_call = mock_client.post.call_args
    assert post_call is not None
    called_url = post_call.args[0]
    assert called_url.startswith("https://app.phoenix.arize.com/s/aiinfra/")


@pytest.mark.asyncio
async def test_submit_span_annotation_submits_user_feedback_payload(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/s/aiinfra")
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")

    mock_response = Mock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client
    mock_context.__aexit__.return_value = None

    feedback_payload = {
        "feedback_text": "useful response",
        "relevance": 4,
        "clarity": 5,
    }

    with patch("httpx.AsyncClient", return_value=mock_context):
        result = await submit_span_annotation("123", feedback_payload, "qa-42")

    assert result is True
    post_call = mock_client.post.call_args
    assert post_call is not None
    sent_json = post_call.kwargs["json"]
    assert "data" in sent_json
    labels = {item["result"]["label"] for item in sent_json["data"]}
    assert "user_feedback" in labels
    assert "relevance" in labels
    assert "clarity" in labels


@pytest.mark.asyncio
async def test_submit_span_annotation_inter_rater_submission(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/s/aiinfra")
    monkeypatch.setenv("PHOENIX_API_KEY", "test-key")

    fake_phoenix_client_module = types.SimpleNamespace(
        phoenix_client=types.SimpleNamespace(get_inter_rater_count=AsyncMock(return_value=2))
    )
    monkeypatch.setitem(sys.modules, "backend.services.phoenix_client", fake_phoenix_client_module)

    mock_response = Mock()
    mock_response.status_code = 200

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_client
    mock_context.__aexit__.return_value = None

    feedback_payload = {
        "is_inter_rater": True,
        "original_span_id": "999",
        "rater_id": "anon_rater_123",
        "relevance": 3,
    }

    with patch("httpx.AsyncClient", return_value=mock_context):
        result = await submit_span_annotation("123", feedback_payload, "qa-99")

    assert result is True
    sent_json = mock_client.post.call_args.kwargs["json"]
    relevance_annotations = [
        item for item in sent_json["data"] if item["result"].get("label") == "relevance"
    ]
    assert len(relevance_annotations) == 1
    annotation = relevance_annotations[0]
    assert annotation["name"].startswith("[inter-rating-3]")
    assert annotation["metadata"]["is_inter_rater"] is True
    assert annotation["metadata"]["feedback_type"] == "inter_rater"
    assert annotation["metadata"]["inter_rater_number"] == 3
