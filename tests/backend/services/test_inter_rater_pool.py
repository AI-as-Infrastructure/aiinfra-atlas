"""
Tests for the seeded study pool manifest.

The manifest is what makes the study pool pure: only prompts written by
`make seed` are eligible, the pool is identical for every reviewer, and the
cohort fingerprint stays stable for the whole run.
"""

import json

import pytest

from backend.services.inter_rater_pool import InterRaterPool


def _write(tmp_path, qa_ids, project="test-project"):
    path = tmp_path / "seed_pool.json"
    path.write_text(json.dumps({"project": project, "count": len(qa_ids), "qa_ids": qa_ids}))
    return path


@pytest.fixture
def pool(monkeypatch, tmp_path):
    def _configure(qa_ids=None):
        if qa_ids is not None:
            monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(_write(tmp_path, qa_ids)))
        else:
            monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(tmp_path / "absent.json"))
        return InterRaterPool()

    return _configure


def test_no_manifest_leaves_sessions_untouched(pool):
    """Ad-hoc inter-rating outside a study must still see every session."""
    p = pool(None)
    sessions = [{"qa_id": "a"}, {"qa_id": "b"}]

    assert p.load() is None
    assert p.qa_ids() is None
    assert p.fingerprint() is None
    assert p.restrict(sessions) == sessions


def test_restrict_excludes_organic_sessions(pool):
    p = pool(["seed-1", "seed-2"])
    sessions = [{"qa_id": "seed-1"}, {"qa_id": "organic-9"}, {"qa_id": "seed-2"}]

    assert [s["qa_id"] for s in p.restrict(sessions)] == ["seed-1", "seed-2"]


def test_restrict_is_user_independent(pool):
    """
    Two reviewers seeing different raw sessions must still get the same pool —
    otherwise they land in different cohorts and receive the same queue.
    """
    p = pool(["seed-1", "seed-2"])
    reviewer_a = [{"qa_id": "seed-1"}, {"qa_id": "seed-2"}, {"qa_id": "organic-a"}]
    reviewer_b = [{"qa_id": "seed-1"}, {"qa_id": "seed-2"}]

    assert p.restrict(reviewer_a) == p.restrict(reviewer_b)


def test_fingerprint_is_stable_against_span_churn(pool):
    """
    The cohort key must not move when Phoenix returns a different set — that
    would re-slot every reviewer mid-study.
    """
    p = pool(["seed-1", "seed-2", "seed-3"])
    before = p.fingerprint()
    p.restrict([{"qa_id": "seed-1"}])  # two prompts missing from Phoenix

    assert p.fingerprint() == before


def test_fingerprint_changes_when_pool_is_reseeded(pool):
    assert pool(["seed-1", "seed-2"]).fingerprint() != pool(["seed-1", "seed-3"]).fingerprint()


def test_fingerprint_ignores_qa_id_ordering(pool):
    assert pool(["a", "b", "c"]).fingerprint() == pool(["c", "a", "b"]).fingerprint()


def test_malformed_manifest_fails_loudly(pool, tmp_path, monkeypatch):
    for payload in ({"qa_ids": []}, {"qa_ids": "not-a-list"}, {}):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps(payload))
        monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(path))
        with pytest.raises(ValueError):
            InterRaterPool().load()


def test_duplicate_qa_ids_rejected(pool, tmp_path, monkeypatch):
    """A duplicate would inflate apparent capacity and skew the assignment."""
    path = tmp_path / "dupe.json"
    path.write_text(json.dumps({"qa_ids": ["seed-1", "seed-1"]}))
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(path))

    with pytest.raises(ValueError):
        InterRaterPool().load()


# --------------------------------------------------------------------------
# Failure paths. A wrong manifest changes the study design silently, so each
# of these must fail loudly rather than degrade.
# --------------------------------------------------------------------------


def test_manifest_from_another_project_is_rejected(tmp_path, monkeypatch):
    """A cross-environment manifest names qa_ids absent here, emptying the pool."""
    path = tmp_path / "seed_pool.json"
    path.write_text(json.dumps({"project": "Hansard-Staging", "qa_ids": ["seed-1"]}))
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(path))
    monkeypatch.setenv("INTER_RATER_PROJECT", "Hansard-Interrating")

    with pytest.raises(ValueError, match="Hansard-Staging"):
        InterRaterPool().load()


def test_manifest_matching_active_project_is_accepted(tmp_path, monkeypatch):
    path = tmp_path / "seed_pool.json"
    path.write_text(json.dumps({"project": "Hansard-Interrating", "qa_ids": ["seed-1"]}))
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(path))
    monkeypatch.setenv("INTER_RATER_PROJECT", "Hansard-Interrating")

    assert InterRaterPool().load()["qa_ids"] == ["seed-1"]


def test_manifest_falls_back_to_phoenix_project_name(tmp_path, monkeypatch):
    path = tmp_path / "seed_pool.json"
    path.write_text(json.dumps({"project": "Hansard-Dev", "qa_ids": ["seed-1"]}))
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(path))
    monkeypatch.delenv("INTER_RATER_PROJECT", raising=False)
    monkeypatch.setenv("PHOENIX_PROJECT_NAME", "Hansard-Dev")

    assert InterRaterPool().load() is not None


def test_manifest_path_is_resolved_from_one_place(monkeypatch, tmp_path):
    """
    The seeder, the reset script and the reader must never disagree about which
    file is the study pool.
    """
    from backend.services.inter_rater_pool import manifest_path

    target = str(tmp_path / "elsewhere.json")
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", target)

    assert manifest_path() == target
    assert InterRaterPool().manifest_path == target
