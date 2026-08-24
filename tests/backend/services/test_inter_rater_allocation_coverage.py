"""
Allocation coverage simulation for the inter-rater focus group.

Drives the real InterRaterService._allocate_sessions_to_user against a
simulated focus group, so rating coverage can be verified before the live
session (which cannot be re-run).

Study design: 20 raters x 20 ratings = 400 ratings, over a pool of 100
seeded prompts at INTER_RATER_MAX_RATINGS=4 — a saturated 1:1 design where
every prompt receives exactly 4 independent ratings.

Coverage depends on two behaviours of the shipped system:

1. InterRaterDashboard.vue fetches a rater's session list once and works
   through that snapshot without re-fetching (its submitFeedback handler
   removes the rated item locally: "re-fetching risks returning it again").
   So count-aware ranking only re-applies when a rater exhausts their batch,
   and with SESSIONS_PER_USER=20 that is once per rater.

2. INTER_RATER_MAX_RATINGS is enforced both at allocation
   (inter_rater_service.py) and at submission (telemetry/api.py). The
   submission-time check is what keeps concurrent raters from pushing one
   span past the cap while others starve; test_without_submit_cap_coverage_degrades
   documents what happens without it.

The allocator is deterministic (SHA-256 of span_id:user_id), so results are
reproducible without seeding.
"""

from collections import Counter

import pytest

POOL_SIZE = 100
N_RATERS = 20
RATINGS_PER_RATER = 20
MAX_RATINGS = 4
FLOOR = 2  # minimum ratings per prompt for usable IRR

# 20 x 20 = 400 = 100 x 4 — demand exactly matches capacity
assert N_RATERS * RATINGS_PER_RATER == POOL_SIZE * MAX_RATINGS


@pytest.fixture
def service(monkeypatch):
    monkeypatch.setenv("INTER_RATER_ENABLED", "true")
    monkeypatch.setenv("INTER_RATER_MAX_RATINGS", str(MAX_RATINGS))
    monkeypatch.setenv("INTER_RATER_SESSIONS_PER_USER", str(RATINGS_PER_RATER))
    from backend.services.inter_rater_service import InterRaterService

    return InterRaterService()


def _simulate(service, batch_size, interleaved, enforce_cap_on_submit=True, pool_size=POOL_SIZE):
    """
    Run a focus group. Returns ({span_id: rating_count}, {rater: ratings_done}).

    batch_size: sessions per allocation call (INTER_RATER_SESSIONS_PER_USER)
    interleaved: True  -> raters work concurrently, submissions interleave
                 False -> each rater finishes their batch before the next starts
    enforce_cap_on_submit: the submission-time max_ratings check in telemetry/api.py
    """
    service.sessions_per_user = batch_size
    max_ratings = service.max_ratings

    spans = [f"span_{i:03d}" for i in range(pool_size)]
    raters = [f"anon_{i:016x}" for i in range(N_RATERS)]

    counts = {s: 0 for s in spans}
    rated_by = {s: set() for s in spans}
    queue = {u: [] for u in raters}
    done = {u: 0 for u in raters}

    def allocate(user):
        available = [
            {"span_id": s, "inter_rater_count": counts[s]}
            for s in spans
            if counts[s] < max_ratings and user not in rated_by[s]
        ]
        return [s["span_id"] for s in service._allocate_sessions_to_user(available, user)]

    def submit(user):
        """One rating. Returns False when this rater can make no further progress."""
        if not queue[user]:
            queue[user] = allocate(user)
            if not queue[user]:
                return False
        span = queue[user].pop(0)
        if user in rated_by[span]:
            return True  # duplicate prevention (check_user_already_rated)
        if enforce_cap_on_submit and counts[span] >= max_ratings:
            return True  # session_unavailable; rater moves to the next item
        counts[span] += 1
        rated_by[span].add(user)
        done[user] += 1
        return True

    if interleaved:
        active = list(raters)
        while active:
            for user in list(active):
                if done[user] >= RATINGS_PER_RATER or not submit(user):
                    active.remove(user)
    else:
        for user in raters:
            while done[user] < RATINGS_PER_RATER and submit(user):
                pass

    return counts, done


def _summary(counts, max_ratings=MAX_RATINGS):
    values = list(counts.values())
    return {
        "total": sum(values),
        "below_floor": sum(1 for c in values if c < FLOOR),
        "at_target": sum(1 for c in values if c == max_ratings),
        "over_cap": sum(1 for c in values if c > max_ratings),
        "max": max(values),
        "histogram": dict(sorted(Counter(values).items())),
    }


def test_sequential_arrival_saturates_pool(service):
    """One rater at a time: perfect 1:1 saturation."""
    counts, done = _simulate(service, RATINGS_PER_RATER, interleaved=False)
    result = _summary(counts)

    assert result["total"] == POOL_SIZE * MAX_RATINGS == 400
    assert result["at_target"] == POOL_SIZE
    assert result["below_floor"] == 0
    assert result["over_cap"] == 0
    assert min(done.values()) == RATINGS_PER_RATER


def test_concurrent_arrival_saturates_pool(service):
    """
    All 20 raters working concurrently — the realistic scheduled-session
    pattern. The submission-time cap keeps the design saturated.
    """
    counts, done = _simulate(service, RATINGS_PER_RATER, interleaved=True)
    result = _summary(counts)

    assert result["below_floor"] == 0
    assert result["over_cap"] == 0
    assert result["max"] <= MAX_RATINGS
    assert result["at_target"] >= POOL_SIZE - 1  # at most one prompt short


def test_every_rater_completes_their_workload(service):
    """
    Capacity matches demand exactly, so no rater should run out of work —
    reviewer payment is contingent on completing all 20 ratings.
    """
    _, done = _simulate(service, RATINGS_PER_RATER, interleaved=True)

    assert min(done.values()) >= RATINGS_PER_RATER - 1


def test_undersized_pool_starves_raters(service):
    """
    Guard on the study arithmetic: at MAX_RATINGS=3 the 100-prompt pool holds
    only 300 ratings against 400 demanded, so raters cannot finish. This is
    why the 20-rater design needs MAX_RATINGS=4.
    """
    service.max_ratings = 3
    counts, done = _simulate(service, RATINGS_PER_RATER, interleaved=True)

    assert sum(counts.values()) < N_RATERS * RATINGS_PER_RATER
    assert min(done.values()) < RATINGS_PER_RATER


def test_without_submit_cap_coverage_degrades(service):
    """
    Documents why the submission-time cap check exists. Without it, raters
    working from stale snapshots overshoot some prompts and starve others.
    """
    counts, _ = _simulate(
        service, RATINGS_PER_RATER, interleaved=True, enforce_cap_on_submit=False
    )
    result = _summary(counts)

    assert result["below_floor"] > 0
    assert result["over_cap"] > 0
    assert result["max"] > MAX_RATINGS


@pytest.mark.parametrize("batch_size", [3, 5, 10, RATINGS_PER_RATER])
def test_saturation_holds_at_any_batch_size(service, batch_size):
    """Coverage must not depend on INTER_RATER_SESSIONS_PER_USER tuning."""
    counts, _ = _simulate(service, batch_size, interleaved=True)
    result = _summary(counts)

    assert result["below_floor"] == 0
    assert result["over_cap"] == 0


def test_coverage_report(service, capsys):
    """Print the coverage table. Run with -s to read it."""
    rows = [
        ("sequential", dict(interleaved=False)),
        ("concurrent", dict(interleaved=True)),
        ("concurrent, no submit cap", dict(interleaved=True, enforce_cap_on_submit=False)),
    ]

    with capsys.disabled():
        print(
            f"\n{POOL_SIZE} prompts x {N_RATERS} raters x {RATINGS_PER_RATER} ratings, "
            f"cap {MAX_RATINGS} (demand {N_RATERS * RATINGS_PER_RATER} = capacity {POOL_SIZE * MAX_RATINGS})"
        )
        print(f"{'scenario':<28} {'total':>6} {'<2':>4} {'==4':>5} {'>4':>4} {'max':>4} {'minRater':>9}")
        for label, kwargs in rows:
            counts, done = _simulate(service, RATINGS_PER_RATER, **kwargs)
            r = _summary(counts)
            print(
                f"{label:<28} {r['total']:>6} {r['below_floor']:>4} {r['at_target']:>5} "
                f"{r['over_cap']:>4} {r['max']:>4} {min(done.values()):>9}"
            )
