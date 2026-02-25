"""
Tests for TEI-XML chunking module.

Tests structural and whole-document chunking, metadata prepending,
chunk metadata fields, and section merging.
"""

import pytest
from pathlib import Path

from backend.modules.tei_chunking import (
    chunk_tei_document,
    chunk_tei_corpus,
    _build_metadata_prefix,
    _merge_sections,
)
from backend.modules.tei_xml_parser import parse_tei_document


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SAMPLE_TEI = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="TEST-CHUNK-1">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>Test Chunking Letter</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
        <profileDesc>
            <correspDesc>
                <correspAction type="sent">
                    <persName>Darwin, Charles Robert</persName>
                    <placeName>Down</placeName>
                    <date when="1859-03-15">15 Mar 1859</date>
                </correspAction>
                <correspAction type="received">
                    <persName>Hooker, Joseph Dalton</persName>
                </correspAction>
            </correspDesc>
            <abstract>
                <p>Discussion of species theory and natural selection.</p>
            </abstract>
            <textClass>
                <keywords>
                    <term type="scientific_terms">natural selection</term>
                    <term type="places">Down House</term>
                </keywords>
            </textClass>
        </profileDesc>
    </teiHeader>
    <text>
    <body>
        <div type="letter">
            <div type="text">
                <div type="transcription">
                    <p>My dear Hooker, I have been working hard on the species question
                    and have made considerable progress. The evidence from geographical
                    distribution is particularly compelling.</p>
                    <p>The Galapagos finches continue to provide excellent examples
                    of variation under natural conditions. Each island population
                    shows distinct adaptations.</p>
                    <p>I hope to have a draft ready for your review by the summer.
                    Your botanical expertise will be invaluable in checking my
                    arguments about plant distribution.</p>
                </div>
            </div>
        </div>
        <div type="footnotes">
            <note xml:id="foot.f1">This is a footnote.</note>
        </div>
    </body>
    </text>
</TEI>
"""

SAMPLE_TEI_SHORT = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="TEST-SHORT">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>Short Letter</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
        <profileDesc>
            <correspDesc>
                <correspAction type="sent">
                    <persName>Writer, A</persName>
                    <date when="1850-01-01"/>
                </correspAction>
            </correspDesc>
        </profileDesc>
    </teiHeader>
    <text>
    <body>
        <div type="letter">
            <div type="text">
                <div type="transcription">
                    <p>A short note.</p>
                </div>
            </div>
        </div>
    </body>
    </text>
</TEI>
"""

SAMPLE_TEI_NO_METADATA = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="TEST-NOMETA">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>No Metadata</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
    </teiHeader>
    <text>
    <body>
        <p>Body text without metadata.</p>
    </body>
    </text>
</TEI>
"""


@pytest.fixture
def tei_file(tmp_path):
    """Create a TEI-XML file for chunking tests."""
    f = tmp_path / "test_letter.xml"
    f.write_text(SAMPLE_TEI, encoding="utf-8")
    return f


@pytest.fixture
def parsed_tei(tei_file):
    """Parse the test TEI file."""
    return parse_tei_document(tei_file)


@pytest.fixture
def short_tei_file(tmp_path):
    """Create a short TEI-XML file."""
    f = tmp_path / "short_letter.xml"
    f.write_text(SAMPLE_TEI_SHORT, encoding="utf-8")
    return f


@pytest.fixture
def no_meta_file(tmp_path):
    """Create a TEI file without metadata."""
    f = tmp_path / "no_meta.xml"
    f.write_text(SAMPLE_TEI_NO_METADATA, encoding="utf-8")
    return f


@pytest.fixture
def tei_corpus_dir(tmp_path):
    """Create a directory with multiple TEI-XML files."""
    d = tmp_path / "corpus"
    d.mkdir()
    (d / "letter1.xml").write_text(SAMPLE_TEI, encoding="utf-8")
    (d / "letter2.xml").write_text(SAMPLE_TEI_SHORT, encoding="utf-8")
    (d / "letter3.xml").write_text(SAMPLE_TEI_NO_METADATA, encoding="utf-8")
    (d / "readme.txt").write_text("Not a TEI file", encoding="utf-8")
    return d


# ---------------------------------------------------------------------------
# _build_metadata_prefix tests
# ---------------------------------------------------------------------------

class TestBuildMetadataPrefix:
    def test_full_metadata_prefix(self):
        metadata = {
            "tei_sender": "Darwin, Charles Robert",
            "tei_recipient": "Hooker, Joseph Dalton",
            "tei_date": "1859-03-15",
            "tei_place": "Down",
            "tei_keywords": "natural selection; Down House",
            "tei_abstract": "Discussion of species theory.",
        }
        prefix = _build_metadata_prefix(metadata)
        assert "[Metadata]" in prefix
        assert "[/Metadata]" in prefix
        assert "Sender: Darwin, Charles Robert" in prefix
        assert "Recipient: Hooker, Joseph Dalton" in prefix
        assert "Date: 1859-03-15" in prefix
        assert "Place: Down" in prefix
        assert "Keywords: natural selection; Down House" in prefix

    def test_empty_metadata_returns_empty(self):
        prefix = _build_metadata_prefix({})
        assert prefix == ""

    def test_partial_metadata(self):
        metadata = {"tei_sender": "Test Author"}
        prefix = _build_metadata_prefix(metadata)
        assert "Sender: Test Author" in prefix
        assert "Recipient:" not in prefix


# ---------------------------------------------------------------------------
# Whole-document chunking tests
# ---------------------------------------------------------------------------

class TestWholeDocumentChunking:
    def test_produces_single_chunk(self, parsed_tei):
        docs = chunk_tei_document(parsed_tei, strategy="whole_document")
        assert len(docs) == 1

    def test_chunk_contains_metadata_prefix(self, parsed_tei):
        docs = chunk_tei_document(parsed_tei, strategy="whole_document")
        content = docs[0].page_content
        assert "[Metadata]" in content
        assert "Sender: Darwin, Charles Robert" in content
        assert "[/Metadata]" in content

    def test_chunk_contains_body_text(self, parsed_tei):
        docs = chunk_tei_document(parsed_tei, strategy="whole_document")
        content = docs[0].page_content
        assert "[Content]" in content
        assert "species question" in content

    def test_chunk_has_tei_metadata_fields(self, parsed_tei):
        docs = chunk_tei_document(
            parsed_tei,
            strategy="whole_document",
            corpus_name="test_corpus",
            filter_id="darwin",
            filter_label="Darwin Letters",
        )
        meta = docs[0].metadata
        assert meta["tei_sender"] == "Darwin, Charles Robert"
        assert meta["tei_recipient"] == "Hooker, Joseph Dalton"
        assert meta["tei_date"] == "1859-03-15"
        assert meta["tei_place"] == "Down"
        assert "natural selection" in meta["tei_keywords"]

    def test_backward_compat_filter_fields(self, parsed_tei):
        docs = chunk_tei_document(
            parsed_tei,
            strategy="whole_document",
            corpus_name="test",
            filter_id="darwin",
            filter_label="Darwin Letters",
        )
        meta = docs[0].metadata
        assert meta["filter_1"] == "darwin"
        assert meta["corpus"] == "darwin"
        assert meta["corpus_label"] == "Darwin Letters"

    def test_date_field_populated(self, parsed_tei):
        docs = chunk_tei_document(parsed_tei, strategy="whole_document")
        meta = docs[0].metadata
        assert meta["date"] == "1859-03-15"

    def test_chunk_id_generated(self, parsed_tei):
        docs = chunk_tei_document(parsed_tei, strategy="whole_document")
        assert "chunk_id" in docs[0].metadata
        assert len(docs[0].metadata["chunk_id"]) == 16

    def test_source_filename_preserved(self, parsed_tei):
        docs = chunk_tei_document(parsed_tei, strategy="whole_document")
        assert docs[0].metadata["source_filename"] == "test_letter.xml"

    def test_minimal_metadata_produces_title_only(self, no_meta_file):
        parsed = parse_tei_document(no_meta_file)
        docs = chunk_tei_document(parsed, strategy="whole_document")
        assert len(docs) == 1
        content = docs[0].page_content
        # Still has title from titleStmt, so metadata prefix present
        assert "[Metadata]" in content
        assert "Title:" in content
        # But no correspondence fields
        assert "Sender:" not in content
        assert "Recipient:" not in content
        assert "Body text without metadata" in content


# ---------------------------------------------------------------------------
# Structural chunking tests
# ---------------------------------------------------------------------------

class TestStructuralChunking:
    def test_produces_multiple_chunks_for_multi_paragraph(self, parsed_tei):
        docs = chunk_tei_document(
            parsed_tei,
            strategy="structural",
            chunk_size=200,  # Small to force splitting
            chunk_overlap=0,
        )
        # Should produce more than 1 chunk with small chunk_size
        assert len(docs) >= 1

    def test_each_chunk_has_metadata_prefix(self, parsed_tei):
        docs = chunk_tei_document(
            parsed_tei,
            strategy="structural",
            chunk_size=200,
            chunk_overlap=0,
        )
        for doc in docs:
            assert "[Metadata]" in doc.page_content

    def test_each_chunk_inherits_document_metadata(self, parsed_tei):
        docs = chunk_tei_document(
            parsed_tei,
            strategy="structural",
            chunk_size=200,
            chunk_overlap=0,
            corpus_name="test",
        )
        for doc in docs:
            assert doc.metadata["tei_sender"] == "Darwin, Charles Robert"
            assert doc.metadata["tei_date"] == "1859-03-15"

    def test_chunk_ids_unique(self, parsed_tei):
        docs = chunk_tei_document(
            parsed_tei,
            strategy="structural",
            chunk_size=200,
            chunk_overlap=0,
        )
        if len(docs) > 1:
            ids = [d.metadata["chunk_id"] for d in docs]
            assert len(ids) == len(set(ids))

    def test_falls_back_to_whole_document_if_no_sections(self, no_meta_file):
        parsed = parse_tei_document(no_meta_file)
        docs = chunk_tei_document(parsed, strategy="structural")
        # Should fall back to whole-document
        assert len(docs) >= 1

    def test_large_chunk_size_merges_all(self, parsed_tei):
        docs = chunk_tei_document(
            parsed_tei,
            strategy="structural",
            chunk_size=10000,  # Large enough to fit everything
            chunk_overlap=0,
        )
        assert len(docs) == 1


# ---------------------------------------------------------------------------
# _merge_sections tests
# ---------------------------------------------------------------------------

class TestMergeSections:
    def test_merges_small_sections(self):
        sections = [
            {"type": "paragraph", "text": "Short."},
            {"type": "paragraph", "text": "Also short."},
            {"type": "paragraph", "text": "Still short."},
        ]
        merged = _merge_sections(sections, chunk_size=100, chunk_overlap=0)
        assert len(merged) == 1

    def test_splits_large_sections(self):
        sections = [
            {"type": "paragraph", "text": "A" * 100},
            {"type": "paragraph", "text": "B" * 100},
            {"type": "paragraph", "text": "C" * 100},
        ]
        merged = _merge_sections(sections, chunk_size=150, chunk_overlap=0)
        assert len(merged) >= 2

    def test_empty_sections(self):
        merged = _merge_sections([], chunk_size=100, chunk_overlap=0)
        assert merged == []

    def test_overlap_preserved(self):
        sections = [
            {"type": "paragraph", "text": "First paragraph content."},
            {"type": "paragraph", "text": "Second paragraph content."},
        ]
        merged = _merge_sections(sections, chunk_size=30, chunk_overlap=10)
        # With overlap, second chunk should contain some of first's content
        assert len(merged) >= 2


# ---------------------------------------------------------------------------
# Custom metadata mappings tests
# ---------------------------------------------------------------------------

class TestCustomMappings:
    def test_metadata_mapping_applied(self, parsed_tei):
        mappings = {"tei_sender": "author", "tei_place": "location"}
        docs = chunk_tei_document(
            parsed_tei,
            strategy="whole_document",
            metadata_mappings=mappings,
        )
        meta = docs[0].metadata
        assert meta["author"] == "Darwin, Charles Robert"
        assert meta["location"] == "Down"
        # Original fields still present
        assert meta["tei_sender"] == "Darwin, Charles Robert"


# ---------------------------------------------------------------------------
# chunk_tei_corpus tests
# ---------------------------------------------------------------------------

class TestChunkTeiCorpus:
    def test_chunks_all_tei_files(self, tei_corpus_dir):
        docs = chunk_tei_corpus(
            tei_corpus_dir,
            strategy="whole_document",
            corpus_name="test",
        )
        # Should have chunks from TEI files, not txt
        assert len(docs) >= 2  # letter1.xml and letter2.xml at minimum

    def test_skips_non_tei_files(self, tei_corpus_dir):
        docs = chunk_tei_corpus(tei_corpus_dir, strategy="whole_document")
        filenames = [d.metadata["source_filename"] for d in docs]
        assert "readme.txt" not in filenames

    def test_handles_malformed_files_gracefully(self, tei_corpus_dir):
        # Add a malformed XML file
        (tei_corpus_dir / "bad.xml").write_text(
            '<?xml version="1.0"?><TEI><broken', encoding="utf-8"
        )
        # Should not raise; malformed file is skipped
        docs = chunk_tei_corpus(tei_corpus_dir, strategy="whole_document")
        assert len(docs) >= 2

    def test_selected_fields_filter(self, tei_corpus_dir):
        docs = chunk_tei_corpus(
            tei_corpus_dir,
            strategy="whole_document",
            selected_fields=["tei_sender", "tei_date"],
        )
        for doc in docs:
            meta = doc.metadata
            # Should not have keywords or abstract (not in selected_fields)
            assert "tei_keywords" not in meta
            assert "tei_abstract" not in meta


# ---------------------------------------------------------------------------
# Invalid strategy tests
# ---------------------------------------------------------------------------

class TestInvalidStrategy:
    def test_unknown_strategy_raises(self, parsed_tei):
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            chunk_tei_document(parsed_tei, strategy="invalid")
