"""Safety checks for deriving the Redis database used by rater-load."""

from utils.scripts import scratch_redis_url


def test_rejects_query_selected_application_database(monkeypatch, capsys):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0?db=15")
    monkeypatch.setenv("RATER_TEST_REDIS_DB", "15")

    assert scratch_redis_url.main() == 1
    assert "already using Redis DB 15" in capsys.readouterr().err


def test_rejects_equivalent_zero_padded_database(monkeypatch, capsys):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/015")
    monkeypatch.setenv("RATER_TEST_REDIS_DB", "15")

    assert scratch_redis_url.main() == 1
    assert "already using Redis DB 15" in capsys.readouterr().err


def test_rewrites_database_and_removes_query_override(monkeypatch, capsys):
    monkeypatch.setenv(
        "REDIS_URL",
        "rediss://:secret@redis.example:6380/1?db=1&ssl_cert_reqs=required",
    )
    monkeypatch.setenv("RATER_TEST_REDIS_DB", "15")

    assert scratch_redis_url.main() == 0
    output = capsys.readouterr().out.strip()
    assert output == (
        "rediss://:secret@redis.example:6380/15?ssl_cert_reqs=required"
    )


def test_rejects_invalid_scratch_database(monkeypatch, capsys):
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("RATER_TEST_REDIS_DB", "not-a-number")

    assert scratch_redis_url.main() == 1
    assert "must be a non-negative integer" in capsys.readouterr().err
