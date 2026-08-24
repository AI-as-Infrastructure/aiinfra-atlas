"""Regression tests for side-effect-free study manifest guards."""

import json
import sys

import pytest

from utils.scripts import seed_questions, seed_reset


def _questions_file(tmp_path):
    path = tmp_path / "questions.json"
    path.write_text(json.dumps({
        "questions": [
            {"question": "A sufficiently useful test question?", "corpus_filter": "all"}
        ]
    }))
    return path


def test_existing_manifest_is_rejected_before_submission(monkeypatch, tmp_path):
    manifest = tmp_path / "seed_pool.json"
    manifest.write_text(json.dumps({
        "project": "test-project",
        "qa_ids": ["existing-prompt"],
    }))
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(manifest))
    monkeypatch.setenv("INTER_RATER_PROJECT", "test-project")
    monkeypatch.setenv("INTER_RATER_MAX_RATINGS", "1")
    monkeypatch.delenv("INTER_RATER_REVIEWERS", raising=False)
    monkeypatch.delenv("INTER_RATER_SESSIONS_PER_USER", raising=False)
    monkeypatch.setattr(
        seed_questions,
        "_submit_with_retry",
        lambda *args, **kwargs: pytest.fail("submission ran before manifest preflight"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["seed_questions.py", "--file", str(_questions_file(tmp_path))],
    )

    with pytest.raises(SystemExit, match="No prompts were submitted"):
        seed_questions.main()


def test_seed_requires_manifest_path_from_environment(monkeypatch, tmp_path):
    monkeypatch.delenv("INTER_RATER_POOL_MANIFEST", raising=False)
    monkeypatch.setenv("INTER_RATER_PROJECT", "test-project")

    with pytest.raises(SystemExit, match="INTER_RATER_POOL_MANIFEST"):
        seed_questions.prepare_manifest_target(force=False)


def test_reset_requires_manifest_path_before_project_deletion(monkeypatch):
    monkeypatch.delenv("INTER_RATER_POOL_MANIFEST", raising=False)
    monkeypatch.setattr(sys, "argv", ["seed_reset.py", "--yes"])

    with pytest.raises(SystemExit, match="INTER_RATER_POOL_MANIFEST"):
        seed_reset.main()


def test_manifest_write_is_complete_and_replaceable(monkeypatch, tmp_path):
    """Forced replacement produces a complete JSON snapshot at the target."""
    monkeypatch.setenv("INTER_RATER_PROJECT", "test-project")
    path = tmp_path / "pool" / "seed_pool.json"
    path.parent.mkdir()
    path.write_text("old snapshot")
    seeded = [
        seed_questions.SeedResult(
            index=1,
            question="Question",
            corpus_filter="all",
            qa_id="qa-new",
            session_id="session-new",
        )
    ]

    assert seed_questions.write_pool_manifest(
        seeded, total=1, force=True, path=str(path)
    )
    manifest = json.loads(path.read_text())
    assert manifest["project"] == "test-project"
    assert manifest["created"]
    assert manifest["count"] == 1
    assert manifest["qa_ids"] == ["qa-new"]
    assert list(path.parent.glob(".seed_pool.*.tmp")) == []
