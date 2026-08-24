"""Tests for atomic inter-rater submission-time capacity enforcement."""

import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from backend.services.annotations_cache import AnnotationsCache
from backend.services.inter_rater_submission_gate import (
    InterRaterSubmissionGate,
    SubmissionStatus,
)


def _annotation(span_id, rater_id):
    return {
        "span_id": span_id,
        "metadata": {"is_inter_rater": True, "rater_id": rater_id},
    }


@pytest.fixture
def gate_and_cache(monkeypatch):
    gate = InterRaterSubmissionGate()
    cache = AnnotationsCache()

    import backend.services.annotations_cache as cache_module

    monkeypatch.setattr(cache_module, "annotations_cache", cache)

    @asynccontextmanager
    async def unlocked(_project_name, _span_id):
        yield

    monkeypatch.setattr(gate, "_span_lock", unlocked)
    return gate, cache


@pytest.mark.asyncio
async def test_rejects_span_at_capacity(gate_and_cache, monkeypatch):
    gate, cache = gate_and_cache
    span_id = "span-full"
    cache._by_span[span_id] = [_annotation(span_id, f"rater-{i}") for i in range(4)]
    monkeypatch.setattr(cache, "refresh_span", AsyncMock(return_value=True))

    submit = AsyncMock(return_value=True)
    monkeypatch.setattr(gate, "_submit_annotation", submit)

    result = await gate.submit(span_id, "new-rater", {}, "qa-1", max_ratings=4)

    assert result == SubmissionStatus.UNAVAILABLE
    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_fails_closed_when_count_cannot_be_refreshed(gate_and_cache, monkeypatch):
    gate, cache = gate_and_cache
    monkeypatch.setattr(cache, "refresh_span", AsyncMock(return_value=False))

    submit = AsyncMock(return_value=True)
    monkeypatch.setattr(gate, "_submit_annotation", submit)

    result = await gate.submit("span-1", "rater-1", {}, "qa-1", max_ratings=4)

    assert result == SubmissionStatus.ERROR
    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_concurrent_submissions_never_exceed_cap(gate_and_cache, monkeypatch):
    gate, cache = gate_and_cache
    span_id = "span-shared"
    lock = asyncio.Lock()

    @asynccontextmanager
    async def serialized(_project_name, _span_id):
        async with lock:
            yield

    monkeypatch.setattr(gate, "_span_lock", serialized)
    monkeypatch.setattr(cache, "refresh_span", AsyncMock(return_value=True))
    monkeypatch.setattr(gate, "_submit_annotation", AsyncMock(return_value=True))

    results = await asyncio.gather(*[
        gate.submit(span_id, f"rater-{i}", {}, f"qa-{i}", max_ratings=4)
        for i in range(8)
    ])

    assert results.count(SubmissionStatus.SUCCESS) == 4
    assert results.count(SubmissionStatus.UNAVAILABLE) == 4
    assert cache.get_inter_rater_count(span_id) == 4
