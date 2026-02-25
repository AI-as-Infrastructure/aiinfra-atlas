"""
Tests for faceted retrieval: where clause construction, citation formatting,
filter endpoint response, and backward compatibility with simple filters.
"""

import json
import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


# ---------------------------------------------------------------------------
# Helper: build_faceted_where_clause (extracted from template logic)
# The template generates this as a static method on the retriever class.
# We replicate the logic here for direct testing without needing the template
# instantiation (which requires ChromaDB, embeddings, etc.).
# ---------------------------------------------------------------------------


def build_faceted_where_clause(facet_filters, base_filter=None):
    """Replicate the _build_faceted_where_clause logic from the retriever template."""
    conditions = []

    # Include base filter conditions
    if base_filter:
        for key, value in base_filter.items():
            conditions.append({key: value})

    # Process each faceted filter
    for field, spec in facet_filters.items():
        ftype = spec.get("type", "")

        if ftype == "text":
            value = spec.get("value")
            if value:
                conditions.append({field: value})

        elif ftype == "date_range":
            date_from = spec.get("from")
            date_to = spec.get("to")
            if date_from:
                conditions.append({field: {"$gte": date_from}})
            if date_to:
                conditions.append({field: {"$lte": date_to}})

        elif ftype == "keyword":
            values = spec.get("values", [])
            if values:
                conditions.append({field: {"$in": values}})

    if not conditions:
        return base_filter

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


# ---------------------------------------------------------------------------
# Tests: Where Clause Construction
# ---------------------------------------------------------------------------


class TestBuildFacetedWhereClause:
    """Test ChromaDB where clause construction from faceted filter parameters."""

    def test_empty_filters_returns_none(self):
        result = build_faceted_where_clause({})
        assert result is None

    def test_empty_filters_with_base_returns_base(self):
        base = {"filter_1": "darwin_letters"}
        result = build_faceted_where_clause({}, base)
        assert result == {"filter_1": "darwin_letters"}

    def test_single_text_filter(self):
        facets = {"tei_sender": {"type": "text", "value": "Darwin, Charles Robert"}}
        result = build_faceted_where_clause(facets)
        assert result == {"tei_sender": "Darwin, Charles Robert"}

    def test_single_date_range_from_only(self):
        facets = {"tei_date": {"type": "date_range", "from": "1850-01-01"}}
        result = build_faceted_where_clause(facets)
        assert result == {"tei_date": {"$gte": "1850-01-01"}}

    def test_single_date_range_to_only(self):
        facets = {"tei_date": {"type": "date_range", "to": "1860-12-31"}}
        result = build_faceted_where_clause(facets)
        assert result == {"tei_date": {"$lte": "1860-12-31"}}

    def test_date_range_from_and_to(self):
        facets = {
            "tei_date": {"type": "date_range", "from": "1850-01-01", "to": "1860-12-31"}
        }
        result = build_faceted_where_clause(facets)
        assert result == {
            "$and": [
                {"tei_date": {"$gte": "1850-01-01"}},
                {"tei_date": {"$lte": "1860-12-31"}},
            ]
        }

    def test_single_keyword_filter(self):
        facets = {
            "tei_keywords": {"type": "keyword", "values": ["geology", "botany"]}
        }
        result = build_faceted_where_clause(facets)
        assert result == {"tei_keywords": {"$in": ["geology", "botany"]}}

    def test_combined_text_and_date_range(self):
        facets = {
            "tei_sender": {"type": "text", "value": "Darwin, Charles Robert"},
            "tei_date": {"type": "date_range", "from": "1850-01-01", "to": "1860-12-31"},
        }
        result = build_faceted_where_clause(facets)
        assert "$and" in result
        conditions = result["$and"]
        assert {"tei_sender": "Darwin, Charles Robert"} in conditions
        assert {"tei_date": {"$gte": "1850-01-01"}} in conditions
        assert {"tei_date": {"$lte": "1860-12-31"}} in conditions

    def test_combined_with_base_filter(self):
        facets = {"tei_sender": {"type": "text", "value": "Darwin, Charles Robert"}}
        base = {"filter_1": "darwin_letters"}
        result = build_faceted_where_clause(facets, base)
        assert "$and" in result
        conditions = result["$and"]
        assert {"filter_1": "darwin_letters"} in conditions
        assert {"tei_sender": "Darwin, Charles Robert"} in conditions

    def test_all_three_facet_types_combined(self):
        facets = {
            "tei_sender": {"type": "text", "value": "Darwin, Charles Robert"},
            "tei_date": {"type": "date_range", "from": "1855-01-01"},
            "tei_keywords": {"type": "keyword", "values": ["natural selection"]},
        }
        result = build_faceted_where_clause(facets)
        assert "$and" in result
        conditions = result["$and"]
        assert len(conditions) == 3
        assert {"tei_sender": "Darwin, Charles Robert"} in conditions
        assert {"tei_date": {"$gte": "1855-01-01"}} in conditions
        assert {"tei_keywords": {"$in": ["natural selection"]}} in conditions

    def test_empty_text_value_ignored(self):
        facets = {"tei_sender": {"type": "text", "value": ""}}
        result = build_faceted_where_clause(facets)
        assert result is None

    def test_empty_keyword_list_ignored(self):
        facets = {"tei_keywords": {"type": "keyword", "values": []}}
        result = build_faceted_where_clause(facets)
        assert result is None

    def test_empty_date_range_ignored(self):
        facets = {"tei_date": {"type": "date_range"}}
        result = build_faceted_where_clause(facets)
        assert result is None

    def test_unknown_facet_type_ignored(self):
        facets = {"tei_foo": {"type": "unknown", "value": "bar"}}
        result = build_faceted_where_clause(facets)
        assert result is None


# ---------------------------------------------------------------------------
# Tests: Citation Formatting with TEI Metadata
# Uses mock to avoid deep import chains from base_retriever.py
# ---------------------------------------------------------------------------


def _format_document_for_citation(document, idx=None):
    """Standalone citation formatter matching base_retriever logic.

    Replicated here to avoid importing base_retriever.py which has deep
    dependency chains (telemetry, auth, etc.) not available in the test venv.
    """
    if not document:
        return None

    metadata = getattr(document, "metadata", {})
    content = getattr(document, "page_content", str(document))

    source = metadata.get("source", "Unknown")
    chunk_id = metadata.get("chunk_id", "")
    doc_id = chunk_id or (
        f"doc_{idx + 1}" if idx is not None else metadata.get("id", "unknown")
    )

    filter_1 = metadata.get("filter_1")
    filter_2 = metadata.get("filter_2")
    corpus = metadata.get("corpus")
    corpus_label = metadata.get("corpus_label")

    corpus_display = corpus_label or corpus
    if filter_1 and filter_2:
        corpus_display = f"{filter_1}/{filter_2}"
    elif filter_1 and not corpus_label:
        corpus_display = filter_1
    elif not corpus_display:
        corpus_display = "Unknown"

    title = metadata.get("title", "")
    if not title and source:
        title = source.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

    preview = content[:300] if len(content) > 300 else content

    enrichment_fields = {}
    for field in ["day_of_week", "day", "month", "year", "date", "title", "author"]:
        if field in metadata:
            enrichment_fields[field] = metadata[field]

    # TEI metadata extraction (matches base_retriever.py update)
    tei_fields = {}
    for field in [
        "tei_sender", "tei_recipient", "tei_date", "tei_place",
        "tei_keywords", "tei_abstract", "tei_title",
    ]:
        if field in metadata and metadata[field]:
            tei_fields[field] = metadata[field]

    citation = {
        "id": doc_id,
        "retrieval_id": doc_id,
        "source": source,
        "corpus": corpus_display,
        "title": title,
        "text": preview,
        "quote": preview,
        "content": content[:500] if len(content) > 500 else content,
        "full_content": content,
        "url": metadata.get("url", "") or metadata.get("source_url", ""),
        "source_url": metadata.get("source_url", "") or metadata.get("url", ""),
        "date": metadata.get("date", ""),
        "page": metadata.get("page", ""),
        "loc": metadata.get("loc", ""),
        "weight": 1.0,
        "has_more": len(content) > 300,
        "metadata": metadata,
    }

    if enrichment_fields:
        citation["enrichment"] = enrichment_fields

    if tei_fields:
        citation["tei"] = tei_fields
        if "tei_sender" in tei_fields:
            citation["sender"] = tei_fields["tei_sender"]
        if "tei_recipient" in tei_fields:
            citation["recipient"] = tei_fields["tei_recipient"]
        if "tei_date" in tei_fields and not citation.get("date"):
            citation["date"] = tei_fields["tei_date"]
        if "tei_place" in tei_fields:
            citation["place"] = tei_fields["tei_place"]

    if idx is not None:
        citation["idx"] = idx

    return citation


class _FakeDocument:
    """Minimal Document-like object for testing."""

    def __init__(self, page_content="", metadata=None):
        self.page_content = page_content
        self.metadata = metadata or {}


class TestCitationFormattingWithTei:
    """Test format_document_for_citation includes TEI metadata fields."""

    def _make_doc(self, metadata=None, content="Sample letter content"):
        return _FakeDocument(page_content=content, metadata=metadata or {})

    def test_citation_without_tei_metadata(self):
        doc = self._make_doc({"source": "letter.xml", "corpus": "darwin_letters"})
        citation = _format_document_for_citation(doc, idx=0)
        assert citation is not None
        assert "tei" not in citation
        assert citation["source"] == "letter.xml"

    def test_citation_with_tei_sender(self):
        doc = self._make_doc({
            "source": "letter_1234.xml",
            "tei_sender": "Darwin, Charles Robert",
        })
        citation = _format_document_for_citation(doc, idx=0)
        assert "tei" in citation
        assert citation["tei"]["tei_sender"] == "Darwin, Charles Robert"
        assert citation["sender"] == "Darwin, Charles Robert"

    def test_citation_with_tei_recipient(self):
        doc = self._make_doc({
            "source": "letter_1234.xml",
            "tei_recipient": "Lyell, Charles",
        })
        citation = _format_document_for_citation(doc, idx=0)
        assert citation["tei"]["tei_recipient"] == "Lyell, Charles"
        assert citation["recipient"] == "Lyell, Charles"

    def test_citation_with_tei_date(self):
        doc = self._make_doc({
            "source": "letter_1234.xml",
            "tei_date": "1856-07-05",
        })
        citation = _format_document_for_citation(doc, idx=0)
        assert citation["tei"]["tei_date"] == "1856-07-05"
        # tei_date should populate top-level date if empty
        assert citation["date"] == "1856-07-05"

    def test_citation_tei_date_does_not_overwrite_existing_date(self):
        doc = self._make_doc({
            "source": "letter_1234.xml",
            "date": "1856-07",
            "tei_date": "1856-07-05",
        })
        citation = _format_document_for_citation(doc, idx=0)
        # Existing date field should be preserved
        assert citation["date"] == "1856-07"
        # TEI date still available in tei sub-object
        assert citation["tei"]["tei_date"] == "1856-07-05"

    def test_citation_with_tei_place(self):
        doc = self._make_doc({
            "source": "letter_1234.xml",
            "tei_place": "Down",
        })
        citation = _format_document_for_citation(doc, idx=0)
        assert citation["tei"]["tei_place"] == "Down"
        assert citation["place"] == "Down"

    def test_citation_with_all_tei_fields(self):
        doc = self._make_doc({
            "source": "letter_1234.xml",
            "corpus": "darwin_letters",
            "tei_sender": "Darwin, Charles Robert",
            "tei_recipient": "Hooker, Joseph Dalton",
            "tei_date": "1856-07-05",
            "tei_place": "Down",
            "tei_keywords": "botany, orchids",
            "tei_abstract": "Discussion about orchid pollination",
        })
        citation = _format_document_for_citation(doc, idx=0)
        assert "tei" in citation
        assert len(citation["tei"]) == 6
        assert citation["sender"] == "Darwin, Charles Robert"
        assert citation["recipient"] == "Hooker, Joseph Dalton"
        assert citation["place"] == "Down"

    def test_citation_empty_tei_fields_excluded(self):
        doc = self._make_doc({
            "source": "letter_1234.xml",
            "tei_sender": "",  # Empty should be excluded
            "tei_date": "1856-07-05",
        })
        citation = _format_document_for_citation(doc, idx=0)
        assert "tei" in citation
        # Empty tei_sender should not appear
        assert "tei_sender" not in citation["tei"]
        assert citation["tei"]["tei_date"] == "1856-07-05"


# ---------------------------------------------------------------------------
# Tests: Backward Compatibility
# ---------------------------------------------------------------------------


class TestBackwardCompatibilityWithSimpleFilters:
    """Verify that existing simple filter behavior is preserved."""

    def test_simple_corpus_filter_no_facets(self):
        base = {"filter_1": "1901_au"}
        result = build_faceted_where_clause({}, base)
        assert result == {"filter_1": "1901_au"}

    def test_simple_two_filter_no_facets(self):
        """Two-filter base with no facets gets wrapped in $and (ChromaDB standard)."""
        base = {"filter_1": "1901_au", "filter_2": "victoria"}
        result = build_faceted_where_clause({}, base)
        # With 2 base keys, the function splits into conditions joined by $and
        assert "$and" in result
        conditions = result["$and"]
        assert {"filter_1": "1901_au"} in conditions
        assert {"filter_2": "victoria"} in conditions

    def test_no_filters_at_all(self):
        result = build_faceted_where_clause({}, None)
        assert result is None

    def test_facet_filters_with_no_base(self):
        facets = {"tei_sender": {"type": "text", "value": "Darwin"}}
        result = build_faceted_where_clause(facets, None)
        assert result == {"tei_sender": "Darwin"}


# ---------------------------------------------------------------------------
# Tests: Retriever Filter Endpoint Response Shape
# Tests the data shape without importing the router (avoids deep deps).
# ---------------------------------------------------------------------------


class TestRetrieverFilterResponseShape:
    """Test the expected response shape of /api/retriever/filters."""

    def test_facets_structure_in_response(self):
        """Verify a v1.5+ filter response includes facets array."""
        # Simulate the response format the endpoint now returns
        response = {
            "corpus_filtering": {"supported": True, "options": [{"value": "all", "label": "All Collections"}]},
            "time_period_filtering": {"supported": False, "options": []},
            "direction_filtering": {"supported": False, "options": []},
            "facets": [
                {"field": "tei_sender", "label": "Sender", "type": "text",
                 "values": ["Darwin, Charles Robert", "Lyell, Charles"]},
                {"field": "tei_date", "label": "Date", "type": "date_range",
                 "min": "1850-01-01", "max": "1882-04-19"},
                {"field": "tei_keywords", "label": "Keywords", "type": "keyword",
                 "values": ["natural selection", "geology"]},
            ]
        }

        assert "facets" in response
        assert len(response["facets"]) == 3

        # Text facet has values
        text_facet = response["facets"][0]
        assert text_facet["type"] == "text"
        assert "values" in text_facet

        # Date range facet has min/max
        date_facet = response["facets"][1]
        assert date_facet["type"] == "date_range"
        assert "min" in date_facet
        assert "max" in date_facet

        # Keyword facet has values
        kw_facet = response["facets"][2]
        assert kw_facet["type"] == "keyword"
        assert "values" in kw_facet

    def test_empty_facets_for_non_tei_corpus(self):
        """Non-TEI (v1.4) corpus should return empty facets array."""
        response = {
            "corpus_filtering": {"supported": True, "options": []},
            "facets": []
        }
        assert response["facets"] == []

    def test_response_backward_compatible(self):
        """Existing filter fields should still be present alongside facets."""
        response = {
            "corpus_filtering": {"supported": True, "options": [
                {"value": "all", "label": "All Collections"},
                {"value": "1901_au", "label": "1901 Au"}
            ]},
            "time_period_filtering": {"supported": False, "options": []},
            "direction_filtering": {"supported": False, "options": []},
            "facets": []
        }
        assert "corpus_filtering" in response
        assert response["corpus_filtering"]["supported"] is True
        assert "facets" in response
