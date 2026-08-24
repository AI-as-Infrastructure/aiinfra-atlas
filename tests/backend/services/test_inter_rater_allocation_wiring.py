"""
Wiring tests for get_sessions_for_inter_rating.

Covers the seams between the study pool, the shared pool cache, per-user
filtering and cohort assignment — the parts simulating the allocator alone
cannot check.

Phoenix, the annotations cache and Redis are replaced with stub modules, so
these run without the Phoenix package installed.
"""

import json
import sys
import types
from unittest.mock import AsyncMock

import pytest

POOL_SIZE = 8
N_RATERS = 4
PER_USER = 4
MAX_RATINGS = 2  # 8 x 2 = 16 = 4 x 4, an exactly saturated design


def _pool(author=None, extra=None):
    sessions = [
        {
            "span_id": f"span_{i:03d}",
            "qa_id": f"seed-{i}",
            "session_id": f"s{i}",
            "original_user_id": author if i == 0 else None,
        }
        for i in range(POOL_SIZE)
    ]
    return sessions + (extra or [])


def _stub(monkeypatch, name, **attrs):
    module = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(module, key, value)
    monkeypatch.setitem(sys.modules, name, module)
    return module


@pytest.fixture
def wired(monkeypatch, tmp_path):
    monkeypatch.setenv("INTER_RATER_ENABLED", "true")
    monkeypatch.setenv("INTER_RATER_PROJECT", "test-project")
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "test-project")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("INTER_RATER_MAX_RATINGS", str(MAX_RATINGS))
    monkeypatch.setenv("INTER_RATER_REVIEWERS", str(N_RATERS))
    monkeypatch.setenv("INTER_RATER_SESSIONS_PER_USER", str(PER_USER))

    manifest = tmp_path / "seed_pool.json"
    manifest.write_text(json.dumps({"qa_ids": [f"seed-{i}" for i in range(POOL_SIZE)]}))
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(manifest))

    query = AsyncMock(return_value=_pool(author="anon_0"))
    _stub(
        monkeypatch,
        "backend.services.phoenix_client",
        phoenix_client=types.SimpleNamespace(query_spans_for_inter_rating=query),
    )
    _stub(
        monkeypatch,
        "backend.services.annotations_cache",
        annotations_cache=types.SimpleNamespace(
            check_user_already_rated=lambda span_id, user_id: False,
            get_inter_rater_count=lambda span_id: 0,
            get_user_inter_rater_count=lambda user_id: 0,
        ),
    )
    slots: dict = {}
    _stub(
        monkeypatch,
        "backend.services.inter_rater_cohort",
        inter_rater_cohort_registry=types.SimpleNamespace(
            get_slot=AsyncMock(
                side_effect=lambda project, key, user, count: slots.setdefault(user, len(slots))
            )
        ),
    )

    from backend.services import inter_rater_pool as pool_module
    from backend.services.inter_rater_service import InterRaterService

    monkeypatch.setattr(pool_module, "inter_rater_pool", pool_module.InterRaterPool())

    return InterRaterService(), query


async def test_pool_is_fetched_once_and_shared(wired):
    """The Phoenix query is the expensive step; it must not repeat per reviewer."""
    service, query = wired

    for slot in range(N_RATERS):
        await service.get_sessions_for_inter_rating(f"anon_{slot}")

    assert query.await_count == 1


async def test_author_id_never_reaches_the_caller(wired):
    service, _ = wired

    sessions = await service.get_sessions_for_inter_rating("anon_1")

    assert sessions
    assert all("original_user_id" not in s for s in sessions)


async def test_shared_pool_is_not_corrupted_by_per_user_filtering(wired):
    """
    anon_0 authored span_000 and must not be offered it, but the cached pool
    is shared — the exclusion must not remove it for everyone else.
    """
    service, _ = wired

    own = {s["span_id"] for s in await service.get_sessions_for_inter_rating("anon_0")}
    others = set()
    for slot in range(1, N_RATERS):
        others |= {s["span_id"] for s in await service.get_sessions_for_inter_rating(f"anon_{slot}")}

    assert "span_000" not in own
    assert "span_000" in others


async def test_organic_sessions_are_kept_out_of_the_study(wired):
    service, query = wired
    query.return_value = _pool(
        extra=[{"span_id": "span_organic", "qa_id": "organic-1",
                "session_id": "so", "original_user_id": None}]
    )

    sessions = await service.get_sessions_for_inter_rating("anon_1")

    assert "span_organic" not in {s["span_id"] for s in sessions}


async def test_quota_respected_and_counts_annotated(wired):
    service, _ = wired

    sessions = await service.get_sessions_for_inter_rating("anon_1")

    assert 0 < len(sessions) <= PER_USER
    assert all(s["inter_rater_count"] == 0 for s in sessions)


async def test_saturated_design_covers_every_prompt_exactly(wired):
    """End-to-end: the wired path must reproduce the saturated assignment."""
    from collections import Counter

    service, query = wired
    query.return_value = _pool()  # nobody authored anything, as with a seeded pool

    covered = Counter()
    for slot in range(N_RATERS):
        for session in await service.get_sessions_for_inter_rating(f"anon_{slot}"):
            covered[session["span_id"]] += 1

    assert len(covered) == POOL_SIZE
    assert set(covered.values()) == {MAX_RATINGS}


# --------------------------------------------------------------------------
# Failure paths for the cached pool.
# --------------------------------------------------------------------------


async def test_cached_pool_and_fingerprint_stay_paired_across_a_reseed(wired, tmp_path, monkeypatch):
    """
    A re-seed must not hand reviewers a new cohort's slot over the old cohort's
    prompts. The fingerprint is read with the pool, so while the cached pool is
    the old one the cohort key must be the old one too.
    """
    service, query = wired
    from backend.services import inter_rater_pool as pool_module

    before_sessions, before_fp = await service._get_pool(True)

    # Re-seed: same path, new qa_ids, new mtime.
    manifest = tmp_path / "seed_pool.json"
    manifest.write_text(json.dumps({"qa_ids": [f"reseeded-{i}" for i in range(POOL_SIZE)]}))

    cached_sessions, cached_fp = await service._get_pool(True)

    assert cached_sessions is before_sessions
    assert cached_fp == before_fp, "fingerprint advanced while the pool was still cached"
    # The manifest itself has moved on, proving the pairing is what protects us.
    assert pool_module.inter_rater_pool.fingerprint() != before_fp


async def test_shrunken_pool_fails_instead_of_silently_unbalancing(wired):
    """
    A pool that no longer satisfies the capacity equation must raise. Falling
    back to unbalanced ranking would under-rate part of the pool invisibly.
    """
    service, query = wired
    query.return_value = _pool()[:-1]  # one prompt failed to seed

    with pytest.raises(ValueError, match="does not match the configured design"):
        await service.get_sessions_for_inter_rating("anon_1")


async def test_capacity_guard_only_applies_in_study_mode(wired, monkeypatch, tmp_path):
    """Without a manifest, ad-hoc inter-rating uses whatever is in the project."""
    service, query = wired
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(tmp_path / "absent.json"))
    query.return_value = _pool()[:-1]

    sessions = await service.get_sessions_for_inter_rating("anon_1")

    assert isinstance(sessions, list)
