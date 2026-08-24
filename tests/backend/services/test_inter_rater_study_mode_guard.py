"""
Startup guard for focus-group mode.

INTER_RATER_DEFAULT_UI=true means a study is running. Without a study pool the
allocator silently reverts to project-wide ad-hoc rating: no pool purity, no
capacity check, and a cohort key that moves when spans do. That combination has
no legitimate reading, so it must fail at startup rather than at analysis.
"""

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


def test_focus_group_mode_with_a_study_pool_starts(monkeypatch):
    service_cls = _env(monkeypatch, INTER_RATER_DEFAULT_UI="true")

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
