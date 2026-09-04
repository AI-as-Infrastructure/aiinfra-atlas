"""Configuration tests for the shared inter-rater pool snapshot."""

import pytest

from backend.services.inter_rater_pool_snapshot import (
    InterRaterPoolSnapshotRegistry,
)


def test_refresh_lock_wait_defaults_to_thirty_seconds(monkeypatch):
    monkeypatch.delenv(
        InterRaterPoolSnapshotRegistry.LOCK_WAIT_SECONDS_ENV,
        raising=False,
    )

    assert InterRaterPoolSnapshotRegistry.lock_wait_seconds() == 30


def test_refresh_lock_wait_is_configurable(monkeypatch):
    monkeypatch.setenv(
        InterRaterPoolSnapshotRegistry.LOCK_WAIT_SECONDS_ENV,
        "12.5",
    )

    assert InterRaterPoolSnapshotRegistry.lock_wait_seconds() == 12.5


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_refresh_lock_wait_must_be_positive(monkeypatch, value):
    monkeypatch.setenv(
        InterRaterPoolSnapshotRegistry.LOCK_WAIT_SECONDS_ENV,
        value,
    )

    with pytest.raises(ValueError, match="must be a positive number"):
        InterRaterPoolSnapshotRegistry.lock_wait_seconds()
