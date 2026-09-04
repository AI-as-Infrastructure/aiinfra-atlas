"""
Startup guard for focus-group mode.

INTER_RATER_DEFAULT_UI=true means a study is running. Without a study pool the
allocator silently reverts to project-wide ad-hoc rating: no pool purity, no
capacity check, and a cohort key that moves when spans do. That combination has
no legitimate reading: an unset focus-group setting fails at startup, and any
configured-but-unreadable pool fails during allocation.
"""

import json

import pytest

# Imported once at module scope. The module-level InterRaterService() global
# would otherwise run the guard during whichever test imported first, making
# the outcome depend on collection order rather than on the test's own env.
from backend.services.inter_rater_service import InterRaterService


def _env(monkeypatch, **overrides):
    base = {
        "INTER_RATER_ENABLED": "true",
        "INTER_RATER_PROJECT": "Hansard-Interrating",
        "PHOENIX_PROJECT_NAME": "Hansard-Interrating",
        "REDIS_URL": "redis://localhost:6379/1",
        "INTER_RATER_MAX_RATINGS": "4",
        "INTER_RATER_REVIEWERS": "20",
        "INTER_RATER_SESSIONS_PER_USER": "20",
        "INTER_RATER_DEFAULT_UI": "false",
        "INTER_RATER_POOL_MANIFEST": "data/seed_pool.json",
    }
    base.update(overrides)
    for key, value in base.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return InterRaterService


def test_focus_group_mode_requires_a_study_pool(monkeypatch):
    service_cls = _env(monkeypatch, INTER_RATER_DEFAULT_UI="true", INTER_RATER_POOL_MANIFEST=None)

    with pytest.raises(ValueError, match="INTER_RATER_POOL_MANIFEST"):
        service_cls()


def test_focus_group_mode_with_a_study_pool_starts(monkeypatch, tmp_path):
    manifest = tmp_path / "seed_pool.json"
    manifest.write_text(json.dumps({"project": "Hansard-Interrating", "qa_ids": ["q1"]}))
    service_cls = _env(
        monkeypatch,
        INTER_RATER_DEFAULT_UI="true",
        INTER_RATER_POOL_MANIFEST=str(manifest),
    )

    assert service_cls().default_ui is True


def test_blank_manifest_setting_counts_as_unset(monkeypatch):
    """An empty or whitespace value must not satisfy the requirement."""
    service_cls = _env(monkeypatch, INTER_RATER_DEFAULT_UI="true", INTER_RATER_POOL_MANIFEST="   ")

    with pytest.raises(ValueError, match="INTER_RATER_POOL_MANIFEST"):
        service_cls()


def test_ad_hoc_mode_does_not_require_a_study_pool(monkeypatch):
    """Project-wide inter-rating alongside chat is a supported configuration."""
    service_cls = _env(monkeypatch, INTER_RATER_DEFAULT_UI="false", INTER_RATER_POOL_MANIFEST=None)

    assert service_cls().default_ui is False


def test_guard_does_not_apply_when_feature_is_disabled(monkeypatch):
    service_cls = _env(
        monkeypatch,
        INTER_RATER_ENABLED="false",
        INTER_RATER_DEFAULT_UI="true",
        INTER_RATER_POOL_MANIFEST=None,
    )

    assert service_cls().is_enabled() is False


def test_invalid_pool_refresh_wait_fails_at_startup(monkeypatch):
    service_cls = _env(
        monkeypatch,
        INTER_RATER_POOL_REFRESH_LOCK_WAIT_SECONDS="not-a-number",
    )

    with pytest.raises(
        ValueError,
        match="INTER_RATER_POOL_REFRESH_LOCK_WAIT_SECONDS must be a positive number",
    ):
        service_cls()


def test_pool_refresh_wait_is_ignored_when_feature_is_disabled(monkeypatch):
    service_cls = _env(
        monkeypatch,
        INTER_RATER_ENABLED="false",
        INTER_RATER_POOL_REFRESH_LOCK_WAIT_SECONDS="not-a-number",
    )

    assert service_cls().is_enabled() is False


# --------------------------------------------------------------------------
# The startup guard only proves the setting is present. A configured path with
# no readable file behind it yields no fingerprint, which would skip every
# study invariant — so the pool refresh has to reject it too.
#
# Deliberately not enforced at startup: `make seed` writes the manifest by
# POSTing to the running backend, so refusing to boot without one would
# deadlock a first-time study.
# --------------------------------------------------------------------------


def _capacity_check(service, sessions, fingerprint):
    return service._validate_study_capacity(sessions, fingerprint)


def test_missing_manifest_is_rejected_at_pool_refresh(monkeypatch, tmp_path):
    service_cls = _env(
        monkeypatch,
        INTER_RATER_DEFAULT_UI="true",
        INTER_RATER_POOL_MANIFEST=str(tmp_path / "never_created.json"),
    )
    service = service_cls()

    with pytest.raises(ValueError, match="to be readable"):
        _capacity_check(service, [{"span_id": "s1"}] * 37, None)


def test_ad_hoc_mode_requires_manifest_setting_to_be_unset(monkeypatch):
    service_cls = _env(
        monkeypatch,
        INTER_RATER_DEFAULT_UI="false",
        INTER_RATER_POOL_MANIFEST=None,
    )
    service = service_cls()

    assert _capacity_check(service, [{"span_id": "s1"}] * 37, None) is None


def test_configured_pool_is_required_even_with_normal_chat_ui(monkeypatch, tmp_path):
    """A seeded study's integrity must not depend on which page is the default."""
    service_cls = _env(
        monkeypatch,
        INTER_RATER_DEFAULT_UI="false",
        INTER_RATER_POOL_MANIFEST=str(tmp_path / "never_created.json"),
    )
    service = service_cls()

    with pytest.raises(ValueError, match="to be readable"):
        _capacity_check(service, [{"span_id": "s1"}] * 37, None)


def test_manifest_removed_mid_study_is_rejected(monkeypatch, tmp_path):
    """seed-reset during a live study must not silently degrade to ad-hoc."""
    manifest = tmp_path / "seed_pool.json"
    manifest.write_text(json.dumps({"project": "Hansard-Interrating", "qa_ids": ["q1"]}))
    service_cls = _env(
        monkeypatch,
        INTER_RATER_DEFAULT_UI="true",
        INTER_RATER_POOL_MANIFEST=str(manifest),
    )
    service = service_cls()
    manifest.unlink()

    with pytest.raises(ValueError, match="to be readable"):
        _capacity_check(service, [{"span_id": "s1"}] * 37, None)
