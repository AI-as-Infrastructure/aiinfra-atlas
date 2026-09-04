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
import contextvars
import os
import socket
import uuid
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
WORKER_COUNT = 8

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


_worker = contextvars.ContextVar("inter_rater_test_worker", default=0)


class _FakePhoenix:
    def __init__(self):
        self.recorded: dict[str, set[str]] = {}

    async def write(self, span_id: str, user_id: str) -> bool:
        self.recorded.setdefault(span_id, set()).add(user_id)
        return True

    def visible_raters(self, _span_id: str) -> set[str]:
        return set()

    def count(self, span_id: str) -> int:
        return len(self.recorded.get(span_id, set()))


class _WorkerAnnotationsCache:
    """Route cache reads to separate worker-local views of delayed Phoenix."""

    def __init__(self, project_name: str, phoenix: _FakePhoenix):
        self.project_name = project_name
        self._phoenix = phoenix
        self._local: list[dict[str, set[str]]] = [
            {} for _ in range(WORKER_COUNT)
        ]

    def _ratings(self) -> dict[str, set[str]]:
        return self._local[_worker.get()]

    async def refresh_span(self, span_id: str) -> bool:
        self._ratings()[span_id] = self._phoenix.visible_raters(span_id)
        return True

    def get_inter_rater_raters(self, span_id: str) -> set[str]:
        return set(self._ratings().get(span_id, set()))

    def record_user_rating(self, span_id: str, user_id: str) -> None:
        self._ratings().setdefault(span_id, set()).add(user_id)


@pytest.fixture
async def study(monkeypatch):
    """Eight worker caches coordinated by real Redis over delayed Phoenix."""
    if not os.getenv("REDIS_URL"):
        pytest.skip("REDIS_URL is not set")
    if not _redis_reachable():
        pytest.fail("REDIS_URL is set but Redis is unreachable")

    project_name = f"concurrency-test-{uuid.uuid4().hex}"
    span_ids = [f"span-{index:03d}" for index in range(POOL_SIZE)]
    phoenix = _FakePhoenix()
    cache = _WorkerAnnotationsCache(project_name, phoenix)

    import backend.services.annotations_cache as cache_module

    monkeypatch.setattr(cache_module, "annotations_cache", cache)

    from backend.services import inter_rater_service as service_module
    from backend.services.inter_rater_pool_snapshot import (
        inter_rater_pool_snapshot_registry,
    )

    monkeypatch.setattr(
        service_module.inter_rater_service, "project_name", project_name
    )
    await inter_rater_pool_snapshot_registry.publish(
        project_name, "concurrency-snapshot", span_ids
    )

    gates = [InterRaterSubmissionGate() for _ in range(WORKER_COUNT)]

    async def _write(span_id, feedback_data, _qa_id):
        return await phoenix.write(span_id, feedback_data["rater_id"])

    for gate in gates:
        monkeypatch.setattr(gate, "_submit_annotation", _write)

    yield gates, phoenix, span_ids

    import redis.asyncio as redis

    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        keys = [
            inter_rater_pool_snapshot_registry._key(project_name),
            inter_rater_pool_snapshot_registry._lock_key(project_name),
        ]
        for gate in gates:
            keys.extend(
                gate._raters_key(project_name, span_id)
                for span_id in span_ids
            )
            keys.extend(
                gate._lock_key(project_name, span_id)
                for span_id in span_ids
            )
            break
        await client.delete(*keys)
    finally:
        await client.aclose()


async def _submit(gates, worker_index, span_id, user_id):
    token = _worker.set(worker_index % WORKER_COUNT)
    try:
        return await gates[worker_index % WORKER_COUNT].submit(
            span_id,
            user_id,
            {"rater_id": user_id},
            f"qa-{span_id}",
            MAX_RATINGS,
        )
    finally:
        _worker.reset(token)


@pytest.mark.asyncio
async def test_study_scale_submissions_never_exceed_the_cap(study):
    """
    Every reviewer works their whole queue at once. The cap must hold across
    all of them, and the pool must saturate exactly — no prompt over-rated,
    none left short.
    """
    gates, phoenix, span_ids = study

    # Each reviewer gets a rotated view of the pool, so all 20 contend for the
    # same spans in different orders — the worst realistic case for the lock.
    async def reviewer(index: int):
        offset = (index * 5) % POOL_SIZE
        queue = span_ids[offset:] + span_ids[:offset]
        results = []
        for span_id in queue:
            status = await _submit(
                gates, index, span_id, f"reviewer-{index:02d}"
            )
            results.append(status)
            if sum(1 for s in results if s is SubmissionStatus.SUCCESS) >= RATINGS_PER_RATER:
                break
        return results

    all_results = await asyncio.gather(*[reviewer(i) for i in range(N_RATERS)])
    flat = [status for results in all_results for status in results]

    successes = sum(1 for status in flat if status is SubmissionStatus.SUCCESS)
    assert successes == POOL_SIZE * MAX_RATINGS == 400
    assert SubmissionStatus.ERROR not in flat

    counts = [phoenix.count(span_id) for span_id in span_ids]
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
    gates, _, span_ids = study
    span_id = span_ids[0]

    for index in range(MAX_RATINGS):
        assert await _submit(
            gates, index, span_id, f"filler-{index}"
        ) is SubmissionStatus.SUCCESS

    # A fresh reviewer meets a full prompt.
    assert await _submit(
        gates, 4, span_id, "latecomer"
    ) is SubmissionStatus.AT_CAPACITY

    # One of the original raters tries again: their own duplicate, not capacity.
    assert await _submit(
        gates, 5, span_id, "filler-0"
    ) is SubmissionStatus.ALREADY_RATED


@pytest.mark.asyncio
async def test_concurrent_duplicates_from_one_reviewer_record_once(study):
    """A double-submit (fast clicks, a retry) must not consume two slots."""
    gates, phoenix, span_ids = study
    span_id = span_ids[1]

    results = await asyncio.gather(
        *[
            _submit(gates, index, span_id, "eager-reviewer")
            for index in range(6)
        ]
    )

    assert sum(1 for s in results if s is SubmissionStatus.SUCCESS) == 1
    assert all(
        s in (SubmissionStatus.SUCCESS, SubmissionStatus.ALREADY_RATED) for s in results
    )
    assert phoenix.count(span_id) == 1


@pytest.mark.asyncio
async def test_span_outside_the_pool_is_refused_under_load(study):
    """Stale client state must not slip a foreign span through while busy."""
    gates, phoenix, span_ids = study

    results = await asyncio.gather(
        _submit(gates, 0, "not-in-pool", "reviewer-00"),
        *[
            _submit(gates, index, span_ids[2], f"reviewer-{index:02d}")
            for index in range(4)
        ],
    )

    assert results[0] is SubmissionStatus.OUT_OF_POOL
    assert phoenix.count("not-in-pool") == 0
