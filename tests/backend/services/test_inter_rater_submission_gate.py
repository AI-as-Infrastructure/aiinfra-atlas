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
    monkeypatch.setattr(
        gate, "_get_shared_raters", AsyncMock(return_value=set())
    )
    monkeypatch.setattr(
        gate, "_record_shared_rating", AsyncMock(return_value=None)
    )

    # The gate now checks pool membership before capacity. These tests are
    # about capacity, so default every span into the pool; the membership
    # cases override this explicitly.
    from backend.services import inter_rater_service as service_module

    class _AnyPool:
        def __contains__(self, _span_id):
            return True

    monkeypatch.setattr(
        service_module.inter_rater_service,
        "span_ids_in_current_pool",
        AsyncMock(return_value=_AnyPool()),
    )
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

    assert result == SubmissionStatus.AT_CAPACITY
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
    assert results.count(SubmissionStatus.AT_CAPACITY) == 4
    assert cache.get_inter_rater_count(span_id) == 4


@pytest.mark.asyncio
async def test_rejects_span_outside_the_current_pool(gate_and_cache, monkeypatch):
    """
    A span rehydrated from stale client state must not be rated just because it
    still has capacity. Membership is checked server-side, never from a
    client-supplied qa_id or snapshot id.
    """
    gate, cache = gate_and_cache
    from backend.services import inter_rater_service as service_module

    monkeypatch.setattr(
        service_module.inter_rater_service,
        "span_ids_in_current_pool",
        AsyncMock(return_value={"some-other-span"}),
    )
    refresh = AsyncMock(return_value=True)
    monkeypatch.setattr(cache, "refresh_span", refresh)
    submit = AsyncMock(return_value=True)
    monkeypatch.setattr(gate, "_submit_annotation", submit)

    result = await gate.submit("stale-span", "rater-1", {}, "qa-1", max_ratings=4)

    assert result == SubmissionStatus.OUT_OF_POOL
    submit.assert_not_awaited()
    refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_fails_closed_when_pool_cannot_be_established(gate_and_cache, monkeypatch):
    """An unverifiable pool must refuse, not fall through to accepting."""
    gate, cache = gate_and_cache
    from backend.services import inter_rater_service as service_module

    monkeypatch.setattr(
        service_module.inter_rater_service,
        "span_ids_in_current_pool",
        AsyncMock(side_effect=RuntimeError("phoenix unreachable")),
    )
    submit = AsyncMock(return_value=True)
    monkeypatch.setattr(gate, "_submit_annotation", submit)

    result = await gate.submit("span-1", "rater-1", {}, "qa-1", max_ratings=4)

    assert result == SubmissionStatus.ERROR
    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_is_distinct_from_capacity(gate_and_cache, monkeypatch):
    """
    The reviewer's own duplicate and a prompt filled by others are different
    facts. Collapsing them reported a re-rating as a concurrency loss (#72).
    """
    gate, cache = gate_and_cache
    span_id = "span-dup"
    cache._by_span[span_id] = [_annotation(span_id, "rater-1")]
    monkeypatch.setattr(cache, "refresh_span", AsyncMock(return_value=True))
    submit = AsyncMock(return_value=True)
    monkeypatch.setattr(gate, "_submit_annotation", submit)

    result = await gate.submit(span_id, "rater-1", {}, "qa-1", max_ratings=4)

    assert result == SubmissionStatus.ALREADY_RATED
    assert result != SubmissionStatus.AT_CAPACITY
    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_shared_ledger_blocks_capacity_when_phoenix_is_stale(
    gate_and_cache, monkeypatch
):
    gate, cache = gate_and_cache
    monkeypatch.setattr(cache, "refresh_span", AsyncMock(return_value=True))
    monkeypatch.setattr(
        gate,
        "_get_shared_raters",
        AsyncMock(return_value={f"rater-{index}" for index in range(4)}),
    )
    submit = AsyncMock(return_value=True)
    monkeypatch.setattr(gate, "_submit_annotation", submit)

    result = await gate.submit("span-1", "late-rater", {}, "qa-1", max_ratings=4)

    assert result == SubmissionStatus.AT_CAPACITY
    submit.assert_not_awaited()


@pytest.mark.asyncio
async def test_shared_ledger_bridges_separate_stale_worker_caches(monkeypatch):
    from backend.services import annotations_cache as cache_module
    from backend.services import inter_rater_service as service_module

    shared_raters = set()

    async def get_shared(_project_name, _span_id):
        return set(shared_raters)

    async def record_shared(_project_name, _span_id, user_id):
        shared_raters.add(user_id)

    @asynccontextmanager
    async def unlocked(_project_name, _span_id):
        yield

    async def in_pool(*_args, **_kwargs):
        return {"span-1"}

    monkeypatch.setattr(
        service_module.inter_rater_service,
        "span_ids_in_current_pool",
        in_pool,
    )

    for index in range(4):
        cache = AnnotationsCache()
        cache.project_name = "test-project"
        monkeypatch.setattr(cache, "refresh_span", AsyncMock(return_value=True))
        monkeypatch.setattr(cache_module, "annotations_cache", cache)

        gate = InterRaterSubmissionGate()
        monkeypatch.setattr(gate, "_span_lock", unlocked)
        monkeypatch.setattr(gate, "_get_shared_raters", get_shared)
        monkeypatch.setattr(gate, "_record_shared_rating", record_shared)
        monkeypatch.setattr(gate, "_submit_annotation", AsyncMock(return_value=True))

        assert await gate.submit(
            "span-1", f"rater-{index}", {}, "qa-1", max_ratings=4
        ) is SubmissionStatus.SUCCESS

    stale_cache = AnnotationsCache()
    stale_cache.project_name = "test-project"
    monkeypatch.setattr(
        stale_cache, "refresh_span", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(cache_module, "annotations_cache", stale_cache)
    late_gate = InterRaterSubmissionGate()
    monkeypatch.setattr(late_gate, "_span_lock", unlocked)
    monkeypatch.setattr(late_gate, "_get_shared_raters", get_shared)
    monkeypatch.setattr(late_gate, "_record_shared_rating", record_shared)
    submit = AsyncMock(return_value=True)
    monkeypatch.setattr(late_gate, "_submit_annotation", submit)

    assert await late_gate.submit(
        "span-1", "late-rater", {}, "qa-1", max_ratings=4
    ) is SubmissionStatus.AT_CAPACITY
    submit.assert_not_awaited()
