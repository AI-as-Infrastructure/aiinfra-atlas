"""
Attribution tests for the inter-rater rating history extractor.

Scores and the fault rationale carry `rater_id`. Fault tags, Additional
Comments and the per-scale comments do not (backend/telemetry/feedback.py:657,
672, 690-715), so the only link to their author is the shared
`[inter-rating-N]` name prefix. That join is the disclosure risk for the
"own ratings only" requirement, so these tests pin the rule: attribute a group
only when exactly one rater owns it, and omit rather than guess.
"""

from backend.services.annotations_cache import AnnotationsCache


def _score(group: str, rater: str, name: str = "Corpus Fidelity", score: int = 4) -> dict:
    return {
        "name": f"[inter-rating-{group}] {name}",
        "metadata": {"is_inter_rater": True, "rater_id": rater},
        "result": {"score": score},
    }


def _fault(group: str, fault: str = "Hallucination") -> dict:
    """Metadata-poor: no rater_id, no is_inter_rater."""
    return {
        "name": f"[inter-rating-{group}] Fault: {fault}",
        "metadata": {"qa_id": "qa-1", "fault_type": fault.lower()},
        "result": {"label": "fault", "score": 1},
    }


def _scale_comment(group: str, label: str = "Corpus Fidelity Comment") -> dict:
    """Metadata-poor: no rater_id, no is_inter_rater."""
    return {
        "name": f"[inter-rating-{group}] {label}",
        "metadata": {"qa_id": "qa-1"},
        "result": {"explanation": "rationale text"},
    }


def _additional_comments(group: str, text: str = "overall note") -> dict:
    """Metadata-poor: no rater_id, no is_inter_rater."""
    return {
        "name": f"[inter-rating-{group}] Additional Comments",
        "metadata": {"qa_id": "qa-1", "feedback_type": "extended"},
        "result": {"explanation": text},
    }


def _cache(monkeypatch) -> AnnotationsCache:
    monkeypatch.setenv("INTER_RATER_PROJECT", "test-project")
    return AnnotationsCache()


def test_returns_own_scores_rationales_and_faults(monkeypatch):
    cache = _cache(monkeypatch)
    cache._by_span["span-1"] = [
        _score("1", "reviewer-a"),
        _score("1", "reviewer-a", name="Coherence", score=2),
        _scale_comment("1"),
        _fault("1"),
        _additional_comments("1"),
    ]

    rating = cache.get_user_inter_rater_rating("span-1", "reviewer-a")

    assert rating is not None
    assert rating["scores"] == {"corpus_fidelity": 4, "coherence": 2}
    assert rating["rationales"] == {"corpus_fidelity": "rationale text"}
    assert rating["faults"] == ["Hallucination"]
    assert rating["additional_comments"] == "overall note"
    assert rating["inter_rater_number"] == 1


def test_another_reviewers_rating_is_never_returned(monkeypatch):
    cache = _cache(monkeypatch)
    cache._by_span["span-1"] = [
        _score("1", "reviewer-a"),
        _fault("1"),
        _additional_comments("1", "a-note"),
        _score("2", "reviewer-b"),
        _fault("2", "Harmful Handling"),
        _additional_comments("2", "b-note"),
    ]

    own = cache.get_user_inter_rater_rating("span-1", "reviewer-a")
    assert own["faults"] == ["Hallucination"]
    assert own["additional_comments"] == "a-note"

    other = cache.get_user_inter_rater_rating("span-1", "reviewer-b")
    assert other["faults"] == ["Harmful Handling"]
    assert other["additional_comments"] == "b-note"

    assert cache.get_user_inter_rater_rating("span-1", "reviewer-c") is None


def test_group_with_no_rater_identity_is_omitted(monkeypatch):
    """A group of only metadata-poor annotations cannot be attributed."""
    cache = _cache(monkeypatch)
    cache._by_span["span-1"] = [
        _fault("1"),
        _scale_comment("1"),
        _additional_comments("1"),
    ]

    assert cache.get_user_inter_rater_rating("span-1", "reviewer-a") is None


def test_colliding_group_number_is_omitted_not_guessed(monkeypatch):
    """
    Two raters sharing a group number make the join ambiguous. Neither may
    claim the group's metadata-poor annotations.
    """
    cache = _cache(monkeypatch)
    cache._by_span["span-1"] = [
        _score("1", "reviewer-a"),
        _score("1", "reviewer-b"),
        _fault("1"),
        _scale_comment("1"),
        _additional_comments("1"),
    ]

    assert cache.get_user_inter_rater_rating("span-1", "reviewer-a") is None
    assert cache.get_user_inter_rater_rating("span-1", "reviewer-b") is None


def test_malformed_prefix_is_not_treated_as_inter_rater(monkeypatch):
    cache = _cache(monkeypatch)
    cache._by_span["span-1"] = [
        {
            "name": "Corpus Fidelity",
            "metadata": {"rater_id": "reviewer-a"},
            "result": {"score": 5},
        },
        {
            "name": "[inter-rating-] Corpus Fidelity",
            "metadata": {"is_inter_rater": True, "rater_id": "reviewer-a"},
            "result": {"score": 5},
        },
    ]

    assert cache.get_user_inter_rater_rating("span-1", "reviewer-a") is None


def test_unnumbered_fallback_prefix_is_attributed(monkeypatch):
    """feedback.get_annotation_name falls back to "[Inter-rater] " with no number."""
    cache = _cache(monkeypatch)
    cache._by_span["span-1"] = [
        {
            "name": "[Inter-rater] Corpus Fidelity",
            "metadata": {"is_inter_rater": True, "rater_id": "reviewer-a"},
            "result": {"score": 3},
        },
        {
            "name": "[Inter-rater] Fault: Hallucination",
            "metadata": {"qa_id": "qa-1", "fault_type": "hallucination"},
            "result": {"label": "fault", "score": 1},
        },
    ]

    rating = cache.get_user_inter_rater_rating("span-1", "reviewer-a")

    assert rating["scores"] == {"corpus_fidelity": 3}
    assert rating["faults"] == ["Hallucination"]
    assert rating["inter_rater_number"] is None


def test_baseline_feedback_is_not_returned_as_a_rating(monkeypatch):
    cache = _cache(monkeypatch)
    cache._by_span["span-1"] = [
        {
            "name": "Relevance Rating",
            "metadata": {"feedback_type": "original", "user_id": "reviewer-a"},
            "result": {"score": 4},
        }
    ]

    assert cache.get_user_inter_rater_rating("span-1", "reviewer-a") is None
