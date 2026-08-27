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


def _reset_env(monkeypatch, tmp_path, *, environment, project):
    """Configure a seed_reset run far enough to reach the production guard."""
    manifest = tmp_path / "seed_pool.json"
    manifest.write_text(json.dumps({"qa_ids": ["a"], "project": project, "count": 1}))
    monkeypatch.setenv("INTER_RATER_POOL_MANIFEST", str(manifest))
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://phoenix.invalid")
    monkeypatch.setenv("INTER_RATER_PROJECT", project)
    if environment is None:
        monkeypatch.delenv("ENVIRONMENT", raising=False)
    else:
        monkeypatch.setenv("ENVIRONMENT", environment)


def test_reset_refuses_production_environment_whatever_the_project_is_called(
    monkeypatch, tmp_path
):
    """ENVIRONMENT, not the project name, is what identifies a production study."""
    _reset_env(monkeypatch, tmp_path, environment="production", project="Hansard-Interrating")
    monkeypatch.setattr(sys, "argv", ["seed_reset.py", "--yes"])

    assert seed_reset.main() == 2


def test_reset_still_refuses_a_production_looking_project_name(monkeypatch, tmp_path):
    _reset_env(monkeypatch, tmp_path, environment="staging", project="ATLAS-Production")
    monkeypatch.setattr(sys, "argv", ["seed_reset.py", "--yes"])

    assert seed_reset.main() == 2


def test_reset_of_a_protected_project_still_requires_typed_confirmation(
    monkeypatch, tmp_path
):
    """--force lifts the refusal; it must not also skip the confirmation."""
    _reset_env(monkeypatch, tmp_path, environment="production", project="Hansard-Interrating")
    monkeypatch.setattr(sys, "argv", ["seed_reset.py", "--yes", "--force"])
    monkeypatch.setattr("builtins.input", lambda _: "not-the-project-name")

    assert seed_reset.main() == 1


def test_reset_of_an_unprotected_project_is_unattended(monkeypatch, tmp_path):
    """A non-production target keeps honouring --yes without prompting."""
    _reset_env(monkeypatch, tmp_path, environment="development", project="ATLAS-SeedTest")
    monkeypatch.setattr(sys, "argv", ["seed_reset.py", "--yes"])

    def _refuse(_):
        raise AssertionError("unprotected reset must not prompt")

    monkeypatch.setattr("builtins.input", _refuse)
    deleted = {}

    class _Response:
        status_code = 204

    def _delete(url, **kwargs):
        deleted["url"] = url
        return _Response()

    monkeypatch.setattr(seed_reset.httpx, "delete", _delete)

    assert seed_reset.main() == 0
    assert deleted["url"].endswith("/v1/projects/ATLAS-SeedTest")
