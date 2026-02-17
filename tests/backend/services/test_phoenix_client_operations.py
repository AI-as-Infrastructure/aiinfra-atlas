import pytest
from unittest.mock import AsyncMock, Mock, patch

from backend.services.phoenix_client import PhoenixAPIClient


@pytest.mark.asyncio
async def test_query_spans_with_feedback_returns_sessions(monkeypatch):
    client = PhoenixAPIClient()
    client.has_phoenix_client = True

    sessions = [{"session_id": "s1", "qa_id": "q1"}]
    client._query_phoenix_with_client = AsyncMock(return_value=sessions)

    result = await client.query_spans_with_feedback(limit=5)

    assert result == sessions
    client._query_phoenix_with_client.assert_awaited_once()


@pytest.mark.asyncio
async def test_query_spans_with_feedback_returns_empty_when_no_sessions(monkeypatch):
    client = PhoenixAPIClient()
    client.has_phoenix_client = True
    client._query_phoenix_with_client = AsyncMock(return_value=[])

    result = await client.query_spans_with_feedback(limit=5)

    assert result == []


@pytest.mark.asyncio
async def test_get_span_feedback_annotations_extracts_user_feedback(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/s/aiinfra")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "name": "Relevance Rating",
                "result": {"score": 4, "label": "relevance"},
                "metadata": {"qa_id": "qa-1", "feedback_type": "user", "user_id": "anon-1"},
            },
            {
                "name": "Additional Comments",
                "result": {"explanation": "helpful answer", "label": "additional_feedback"},
                "metadata": {"qa_id": "qa-1", "feedback_type": "user", "user_id": "anon-1"},
            },
            {
                "name": "Relevance Rating",
                "result": {"score": 2},
                "metadata": {"is_inter_rater": True, "rater_id": "inter-1"},
            },
        ]
    }

    with patch("httpx.get", return_value=mock_response):
        client = PhoenixAPIClient()
        feedback = await client._get_span_feedback_annotations("span_123")

    assert feedback["relevance"] == 4
    assert feedback["feedback_text"] == "helpful answer"
    assert feedback["qa_id"] == "qa-1"
    assert feedback["feedback_type"] == "user"
    assert feedback["user_id"] == "anon-1"


@pytest.mark.asyncio
async def test_check_user_already_rated_uses_space_endpoint(monkeypatch):
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com/s/aiinfra")

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "metadata": {
                    "is_inter_rater": True,
                    "rater_id": "user-123",
                }
            }
        ]
    }

    with patch("httpx.get", return_value=mock_response) as mock_get:
        client = PhoenixAPIClient()
        client.has_phoenix_client = True
        rated = await client.check_user_already_rated("span_999", "user-123")

    assert rated is True
    called_url = mock_get.call_args.args[0]
    assert called_url.startswith("https://app.phoenix.arize.com/s/aiinfra/v1/projects/")
