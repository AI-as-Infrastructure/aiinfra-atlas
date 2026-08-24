"""Study-scoped quota tests for the local Phoenix annotations cache."""

from backend.services.annotations_cache import AnnotationsCache


def _rating(user_id: str) -> dict:
    return {
        "name": "[inter-rating] Relevance Rating",
        "metadata": {"is_inter_rater": True, "rater_id": user_id},
        "result": {"score": 4},
    }


def test_user_count_can_be_scoped_to_the_active_study(monkeypatch):
    monkeypatch.setenv("INTER_RATER_PROJECT", "test-project")
    cache = AnnotationsCache()
    cache._by_span["old-pool-span"] = [_rating("reviewer")]
    cache._by_span["new-pool-span"] = [_rating("reviewer")]

    assert cache.get_user_inter_rater_count("reviewer") == 2
    assert cache.get_user_inter_rater_count(
        "reviewer", {"new-pool-span"}
    ) == 1


def test_scoped_count_includes_local_writes(monkeypatch):
    monkeypatch.setenv("INTER_RATER_PROJECT", "test-project")
    cache = AnnotationsCache()
    cache.record_user_rating("new-pool-span", "reviewer")
    cache.record_user_rating("old-pool-span", "reviewer")

    assert cache.get_user_inter_rater_count(
        "reviewer", {"new-pool-span"}
    ) == 1
