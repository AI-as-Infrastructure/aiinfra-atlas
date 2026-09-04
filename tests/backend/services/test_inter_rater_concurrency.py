"""
Concurrency test for the inter-rater submission path, at study scale.

The existing allocation coverage test drives `_balanced_assignment` in-process,
which proves the *design* saturates. It never touches the coordination that
actually broke during this change: the Redis span lock, the shared pool
snapshot, and the split refusal statuses. Those only misbehave under real
concurrent access, which is precisely what a single manual tester cannot
produce — 20 reviewers, 4 ratings per prompt, everyone racing for the same
spans.

So this runs against **real Redis** with Phoenix stubbed out. Redis is where
the coordination lives; Phoenix is only the eventual store, and writing to it
would put hundreds of junk annotations into a real project. Nothing here
writes to Phoenix, and no project name is required.

Skipped unless REDIS_URL points at a reachable Redis.

    REDIS_URL=redis://localhost:6379/15 \\
      .venv/bin/python -m pytest tests/backend/services/test_inter_rater_concurrency.py -v
"""

import asyncio
import os
import socket
from urllib.parse import urlparse

import pytest

from backend.services.inter_rater_submission_gate import (
    InterRaterSubmissionGate,
    SubmissionStatus,
)

pytestmark = pytest.mark.integration

POOL_SIZE = 100
N_RATERS = 20
RATINGS_PER_RATER = 20
MAX_RATINGS = 4

assert N_RATERS * RATINGS_PER_RATER == POOL_SIZE * MAX_RATINGS


def _redis_reachable() -> bool:
    """Plain socket probe, so the skip decision needs no event loop."""
    url = os.getenv("REDIS_URL", "")
    if not url:
        return False
    parsed = urlparse(url)
    try:
        with socket.create_connection(
            (parsed.hostname or "localhost", parsed.port or 6379), timeout=1
        ):
            return True
    except OSError:
        return False


class _FakeAnnotationsCache:
    """
    Stands in for Phoenix. Records ratings in memory with the same semantics
    the gate relies on, so the test exercises coordination rather than storage.
    """

    project_name = "concurrency-test"

    def __init__(self):
        self._ratings: dict[str, set[str]] = {}
        self._lock = asyncio.Lock()

    async def refresh_span(self, _span_id: str) -> bool:
        return True

    def check_user_already_rated(self, span_id: str, user_id: str) -> bool:
        return user_id in self._ratings.get(span_id, set())

    def get_inter_rater_count(self, span_id: str) -> int:
        return len(self._ratings.get(span_id, set()))

    def record_user_rating(self, span_id: str, user_id: str) -> None:
        self._ratings.setdefault(span_id, set()).add(user_id)


@pytest.fixture
def study(monkeypatch):
    """A gate wired to real Redis, a fake Phoenix, and a fixed 100-span pool."""
    if not _redis_reachable():
        pytest.skip("REDIS_URL is not set or Redis is unreachable")

    span_ids = [f"span-{index:03d}" for index in range(POOL_SIZE)]
    cache = _FakeAnnotationsCache()

    import backend.services.annotations_cache as cache_module

    monkeypatch.setattr(cache_module, "annotations_cache", cache)

    from backend.services import inter_rater_service as service_module

    async def _pool(*_args, **_kwargs):
        return set(span_ids)

    monkeypatch.setattr(
        service_module.inter_rater_service, "span_ids_in_current_pool", _pool
    )

    gate = InterRaterSubmissionGate()

    # The Phoenix write is stubbed: this test is about the coordination that
    # decides *whether* to write, not about storage. The gate still records the
    # rating in the fake cache afterwards, exactly as it does in production.
    async def _write(*_args, **_kwargs):
        return True

    monkeypatch.setattr(gate, "_submit_annotation", _write)

    return gate, cache, span_ids


async def _submit(gate, span_id, user_id):
    return await gate.submit(span_id, user_id, {}, f"qa-{span_id}", MAX_RATINGS)


@pytest.mark.asyncio
async def test_study_scale_submissions_never_exceed_the_cap(study):
    """
    Every reviewer works their whole queue at once. The cap must hold across
    all of them, and the pool must saturate exactly — no prompt over-rated,
    none left short.
    """
    gate, cache, span_ids = study

    # Each reviewer gets a rotated view of the pool, so all 20 contend for the
    # same spans in different orders — the worst realistic case for the lock.
    async def reviewer(index: int):
        offset = (index * 5) % POOL_SIZE
        queue = span_ids[offset:] + span_ids[:offset]
        results = []
        for span_id in queue:
            status = await _submit(gate, span_id, f"reviewer-{index:02d}")
            results.append(status)
            if sum(1 for s in results if s is SubmissionStatus.SUCCESS) >= RATINGS_PER_RATER:
                break
        return results

    all_results = await asyncio.gather(*[reviewer(i) for i in range(N_RATERS)])
    flat = [status for results in all_results for status in results]

    successes = sum(1 for status in flat if status is SubmissionStatus.SUCCESS)
    assert successes == POOL_SIZE * MAX_RATINGS == 400
    assert SubmissionStatus.ERROR not in flat

    counts = [cache.get_inter_rater_count(span_id) for span_id in span_ids]
    assert max(counts) == MAX_RATINGS, "a prompt exceeded its rating cap"
    assert min(counts) == MAX_RATINGS, "a prompt was left under-rated"

    # Every reviewer completed their quota — payment depends on it.
    for index, results in enumerate(all_results):
        completed = sum(1 for s in results if s is SubmissionStatus.SUCCESS)
        assert completed == RATINGS_PER_RATER, f"reviewer-{index:02d} finished short"


@pytest.mark.asyncio
async def test_full_prompt_reports_capacity_not_duplication(study):
    """
    The two refusals a reviewer can hit are different facts and must stay
    distinguishable — collapsing them is what reported a reviewer's own
    re-rating as a concurrency loss (#72).
    """
    gate, _, span_ids = study
    span_id = span_ids[0]

    for index in range(MAX_RATINGS):
        assert await _submit(gate, span_id, f"filler-{index}") is SubmissionStatus.SUCCESS

    # A fresh reviewer meets a full prompt.
    assert await _submit(gate, span_id, "latecomer") is SubmissionStatus.AT_CAPACITY

    # One of the original raters tries again: their own duplicate, not capacity.
    assert await _submit(gate, span_id, "filler-0") is SubmissionStatus.ALREADY_RATED


@pytest.mark.asyncio
async def test_concurrent_duplicates_from_one_reviewer_record_once(study):
    """A double-submit (fast clicks, a retry) must not consume two slots."""
    gate, cache, span_ids = study
    span_id = span_ids[1]

    results = await asyncio.gather(
        *[_submit(gate, span_id, "eager-reviewer") for _ in range(6)]
    )

    assert sum(1 for s in results if s is SubmissionStatus.SUCCESS) == 1
    assert all(
        s in (SubmissionStatus.SUCCESS, SubmissionStatus.ALREADY_RATED) for s in results
    )
    assert cache.get_inter_rater_count(span_id) == 1


@pytest.mark.asyncio
async def test_span_outside_the_pool_is_refused_under_load(study):
    """Stale client state must not slip a foreign span through while busy."""
    gate, cache, span_ids = study

    results = await asyncio.gather(
        _submit(gate, "not-in-pool", "reviewer-00"),
        *[_submit(gate, span_ids[2], f"reviewer-{i:02d}") for i in range(4)],
    )

    assert results[0] is SubmissionStatus.OUT_OF_POOL
    assert cache.get_inter_rater_count("not-in-pool") == 0
