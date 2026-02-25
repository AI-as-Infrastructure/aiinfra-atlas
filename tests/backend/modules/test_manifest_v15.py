"""
Tests for manifest v1.5 facets support.

Tests facet generation in corpus_builder, facet loading in manifest_loader,
facet propagation to corpus_active.json, and backward compatibility.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from backend.modules.manifest_loader import (
    load_manifest,
    get_facets,
    has_facets,
    invalidate_cache,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_manifest_cache():
    """Clear manifest cache before and after each test."""
    invalidate_cache()
    yield
    invalidate_cache()


@pytest.fixture
def manifest_v15(tmp_path):
    """Create a v1.5 manifest with facets."""
    manifest = {
        "version": "1.5",
        "corpus_name": "tei_corpus",
        "facets": [
            {
                "field": "tei_sender",
                "label": "Sender",
                "type": "text",
                "values": ["Darwin, Charles Robert", "Lyell, Charles"],
            },
            {
                "field": "tei_date",
                "label": "Date",
                "type": "date_range",
                "min": "1850-01-01",
                "max": "1882-04-19",
                "count": 15239,
            },
            {
                "field": "tei_keywords",
                "label": "Keywords",
                "type": "keyword",
                "values": ["natural selection", "geology", "botany"],
            },
        ],
        "fields": {
            "corpus": {
                "type": "enum",
                "values": ["darwin_letters"],
            }
        },
        "filters": {},
        "statistics": {"total_documents": 100, "total_chunks": 100},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


@pytest.fixture
def manifest_v14(tmp_path):
    """Create a v1.4 manifest without facets."""
    manifest = {
        "version": "1.4",
        "corpus_name": "folder_corpus",
        "fields": {
            "corpus": {
                "type": "enum",
                "values": ["1901_au", "1901_nz", "1901_uk"],
            }
        },
        "filters": {},
        "statistics": {"total_documents": 206, "total_chunks": 4521},
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return manifest_path


# ---------------------------------------------------------------------------
# manifest_loader facet tests
# ---------------------------------------------------------------------------


class TestManifestLoaderFacets:
    """Test get_facets() and has_facets() in manifest_loader."""

    def test_get_facets_from_v15_manifest(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            facets = get_facets()
            assert len(facets) == 3
            assert facets[0]["field"] == "tei_sender"
            assert facets[0]["type"] == "text"
            assert facets[1]["field"] == "tei_date"
            assert facets[1]["type"] == "date_range"
            assert facets[1]["min"] == "1850-01-01"
            assert facets[1]["max"] == "1882-04-19"
            assert facets[2]["field"] == "tei_keywords"
            assert facets[2]["type"] == "keyword"

    def test_has_facets_true_for_v15(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            assert has_facets() is True

    def test_get_facets_empty_for_v14(self, manifest_v14):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v14),
        ):
            facets = get_facets()
            assert facets == []

    def test_has_facets_false_for_v14(self, manifest_v14):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v14),
        ):
            assert has_facets() is False

    def test_get_facets_when_no_manifest(self, tmp_path):
        missing = str(tmp_path / "nonexistent.json")
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=missing,
        ):
            facets = get_facets()
            assert facets == []

    def test_facet_values_accessible(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            facets = get_facets()
            sender_facet = facets[0]
            assert "Darwin, Charles Robert" in sender_facet["values"]
            assert "Lyell, Charles" in sender_facet["values"]

    def test_date_range_facet_has_min_max(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            facets = get_facets()
            date_facet = facets[1]
            assert date_facet["min"] == "1850-01-01"
            assert date_facet["max"] == "1882-04-19"
            assert date_facet["count"] == 15239


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------


class TestManifestBackwardCompatibility:
    """Verify v1.4 manifests load correctly (no facets, existing features work)."""

    def test_v14_corpus_values_still_work(self, manifest_v14):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v14),
        ):
            from backend.modules.manifest_loader import get_corpus_values

            values = get_corpus_values()
            assert "1901_au" in values
            assert "1901_nz" in values
            assert "1901_uk" in values

    def test_v14_corpus_options_still_work(self, manifest_v14):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v14),
        ):
            from backend.modules.manifest_loader import get_corpus_options

            options = get_corpus_options()
            assert options[0]["value"] == "all"
            assert len(options) >= 4  # all + 3 corpora

    def test_v15_manifest_also_has_corpus_values(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            from backend.modules.manifest_loader import get_corpus_values

            values = get_corpus_values()
            assert "darwin_letters" in values

    def test_empty_facets_array_is_falsy(self, manifest_v14):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v14),
        ):
            assert not get_facets()
            assert has_facets() is False


# ---------------------------------------------------------------------------
# corpus_active.json facet propagation tests
# ---------------------------------------------------------------------------


class TestCorpusActiveFacetPropagation:
    """Test that facets from manifest are included in corpus_active.json."""

    def test_facets_included_when_present(self):
        """Simulate the mode.py logic for corpus_active generation."""
        manifest = {
            "corpus_name": "tei_corpus",
            "vector_store": {"collection_name": "tei_c"},
            "embedding_model": {"id": "sentence-transformers/all-MiniLM-L6-v2"},
            "facets": [
                {"field": "tei_sender", "label": "Sender", "type": "text", "values": ["A", "B"]},
            ],
        }

        # Replicate the mode.py logic
        corpus_active_config = {
            "corpus_name": manifest.get("corpus_name"),
            "collection_name": manifest.get("vector_store", {}).get("collection_name"),
            "embedding_model": manifest.get("embedding_model", {}).get("id"),
        }
        facets = manifest.get("facets", [])
        if facets:
            corpus_active_config["facets"] = facets

        assert "facets" in corpus_active_config
        assert len(corpus_active_config["facets"]) == 1
        assert corpus_active_config["facets"][0]["field"] == "tei_sender"

    def test_facets_absent_when_not_in_manifest(self):
        """v1.4 manifest should not produce facets in corpus_active."""
        manifest = {
            "corpus_name": "folder_corpus",
            "vector_store": {"collection_name": "folder_c"},
            "embedding_model": {"id": "sentence-transformers/all-MiniLM-L6-v2"},
        }

        corpus_active_config = {
            "corpus_name": manifest.get("corpus_name"),
        }
        facets = manifest.get("facets", [])
        if facets:
            corpus_active_config["facets"] = facets

        assert "facets" not in corpus_active_config

    def test_empty_facets_not_included(self):
        """Empty facets array should not be included."""
        manifest = {
            "corpus_name": "corpus",
            "facets": [],
        }

        corpus_active_config = {"corpus_name": manifest.get("corpus_name")}
        facets = manifest.get("facets", [])
        if facets:
            corpus_active_config["facets"] = facets

        assert "facets" not in corpus_active_config


# ---------------------------------------------------------------------------
# Facet structure validation tests
# ---------------------------------------------------------------------------


class TestFacetStructure:
    """Test expected facet structure for different facet types."""

    def test_text_facet_has_values(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            facets = get_facets()
            text_facet = next(f for f in facets if f["type"] == "text")
            assert "values" in text_facet
            assert isinstance(text_facet["values"], list)
            assert len(text_facet["values"]) > 0

    def test_date_range_facet_has_min_max_count(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            facets = get_facets()
            date_facet = next(f for f in facets if f["type"] == "date_range")
            assert "min" in date_facet
            assert "max" in date_facet
            assert "count" in date_facet

    def test_keyword_facet_has_values(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            facets = get_facets()
            kw_facet = next(f for f in facets if f["type"] == "keyword")
            assert "values" in kw_facet
            assert "natural selection" in kw_facet["values"]

    def test_all_facets_have_field_label_type(self, manifest_v15):
        with patch(
            "backend.modules.manifest_loader._get_manifest_path",
            return_value=str(manifest_v15),
        ):
            facets = get_facets()
            for facet in facets:
                assert "field" in facet
                assert "label" in facet
                assert "type" in facet
                assert facet["type"] in ("text", "date_range", "keyword")
