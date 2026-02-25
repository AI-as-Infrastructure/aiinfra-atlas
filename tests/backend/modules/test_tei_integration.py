"""
Integration tests for TEI-XML pipeline (Phase 2).

Tests the full TEI pipeline: corpus_analyzer TEI discovery, corpus_builder
TEI routing, corpus_config TEI models, and end-to-end build through
the TEI path (parser → chunking → Documents with metadata).
"""

import pytest
from pathlib import Path
from datetime import datetime

from backend.modules.tei_xml_parser import is_tei_xml, parse_tei_document, discover_tei_schema
from backend.modules.tei_chunking import chunk_tei_document, chunk_tei_corpus
from backend.modules.corpus_analyzer import CorpusAnalyzer
from backend.modules.corpus_config import (
    CorpusConfig,
    CorpusMetadata,
    SourceConfig,
    FilterConfig,
    FilterDefinition,
    CitationConfig,
    EmbeddingConfig,
    ProcessingConfig,
    TeiWorkflowConfig,
    TeiMetadataMapping,
    TeiFacetConfig,
)


# ---------------------------------------------------------------------------
# Shared TEI fixtures
# ---------------------------------------------------------------------------

TEI_LETTER_1 = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="INT-LETT-1">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>From Darwin to Hooker 15 March 1859</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc>
                <msDesc><msIdentifier>
                    <repository>Cambridge UL</repository>
                    <idno>MS DAR 115</idno>
                </msIdentifier></msDesc>
            </sourceDesc>
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
            <abstract><p>Discussion of species theory.</p></abstract>
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
                    and have made considerable progress.</p>
                    <p>The evidence from geographical distribution is particularly
                    compelling. The Galapagos finches continue to provide excellent
                    examples of variation.</p>
                    <p>I hope to have a draft ready for your review by the summer.</p>
                </div>
            </div>
        </div>
    </body>
    </text>
</TEI>
"""

TEI_LETTER_2 = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="INT-LETT-2">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>From Lyell to Darwin 20 April 1859</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
        <profileDesc>
            <correspDesc>
                <correspAction type="sent">
                    <persName>Lyell, Charles</persName>
                    <placeName>London</placeName>
                    <date when="1859-04-20">20 Apr 1859</date>
                </correspAction>
                <correspAction type="received">
                    <persName>Darwin, Charles Robert</persName>
                </correspAction>
            </correspDesc>
            <abstract><p>Remarks on geological strata.</p></abstract>
        </profileDesc>
    </teiHeader>
    <text>
    <body>
        <div type="letter">
            <div type="text">
                <div type="transcription">
                    <p>My dear Darwin, Your geological observations on volcanic
                    islands are most interesting and align with my own work.</p>
                </div>
            </div>
        </div>
    </body>
    </text>
</TEI>
"""

TEI_LETTER_3_MINIMAL = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="INT-LETT-3">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>Fragment</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
    </teiHeader>
    <text>
    <body>
        <p>A fragmentary note with no correspondence metadata.</p>
    </body>
    </text>
</TEI>
"""

NON_TEI_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<document>
    <header><title>Not a TEI file</title></header>
    <body><p>Generic XML content.</p></body>
</document>
"""


@pytest.fixture
def tei_corpus_dir(tmp_path):
    """Create a directory with mixed TEI and non-TEI files."""
    corpus = tmp_path / "tei_corpus"
    corpus.mkdir()
    (corpus / "letter_001.xml").write_text(TEI_LETTER_1, encoding="utf-8")
    (corpus / "letter_002.xml").write_text(TEI_LETTER_2, encoding="utf-8")
    (corpus / "fragment_003.xml").write_text(TEI_LETTER_3_MINIMAL, encoding="utf-8")
    (corpus / "generic.xml").write_text(NON_TEI_XML, encoding="utf-8")
    (corpus / "readme.txt").write_text("Not processed", encoding="utf-8")
    return corpus


@pytest.fixture
def tei_workflow_config(tei_corpus_dir):
    """Build a CorpusConfig with TEI workflow enabled."""
    return CorpusConfig(
        metadata=CorpusMetadata(
            name="test_tei",
            display_name="Test TEI Corpus",
            description="Integration test corpus",
        ),
        source=SourceConfig(
            type="local",
            location=str(tei_corpus_dir),
            file_extensions=".xml",
        ),
        filters=FilterConfig(
            method="tei",
            directory_depth=1,
            filters=[
                FilterDefinition(
                    id="darwin_letters",
                    label="Darwin Letters",
                    pattern="**/*.xml",
                ),
            ],
        ),
        citation=CitationConfig(),
        embedding=EmbeddingConfig(chunk_size=500, chunk_overlap=50),
        processing=ProcessingConfig(),
        tei_workflow=TeiWorkflowConfig(
            enabled=True,
            chunking_strategy="whole_document",
            selected_fields=[
                "tei_sender",
                "tei_recipient",
                "tei_date",
                "tei_place",
                "tei_keywords",
                "tei_abstract",
                "tei_title",
            ],
        ),
    )


# ---------------------------------------------------------------------------
# CorpusConfig TEI model tests
# ---------------------------------------------------------------------------


class TestCorpusConfigTeiModels:
    """Test TEI-related Pydantic models in corpus_config."""

    def test_tei_workflow_config_defaults(self):
        cfg = TeiWorkflowConfig()
        assert cfg.enabled is False
        assert cfg.chunking_strategy == "whole_document"
        assert cfg.selected_fields == []
        assert cfg.metadata_mappings == []
        assert cfg.facets == []

    def test_tei_workflow_config_enabled(self):
        cfg = TeiWorkflowConfig(
            enabled=True,
            chunking_strategy="structural",
            selected_fields=["tei_sender", "tei_date"],
        )
        assert cfg.enabled is True
        assert cfg.chunking_strategy == "structural"
        assert len(cfg.selected_fields) == 2

    def test_tei_workflow_invalid_strategy_rejected(self):
        with pytest.raises(Exception):
            TeiWorkflowConfig(chunking_strategy="invalid")

    def test_tei_metadata_mapping(self):
        m = TeiMetadataMapping(tei_field="tei_sender", role="author")
        assert m.tei_field == "tei_sender"
        assert m.role == "author"

    def test_tei_facet_config(self):
        f = TeiFacetConfig(field="tei_date", label="Date", type="date_range")
        assert f.field == "tei_date"
        assert f.type == "date_range"

    def test_tei_facet_invalid_type_rejected(self):
        with pytest.raises(Exception):
            TeiFacetConfig(field="f", label="l", type="invalid")

    def test_corpus_config_with_tei_workflow(self, tei_workflow_config):
        assert tei_workflow_config.tei_workflow.enabled is True
        assert tei_workflow_config.filters.method == "tei"

    def test_corpus_config_without_tei_workflow(self):
        cfg = CorpusConfig(
            metadata=CorpusMetadata(
                name="plain", display_name="Plain", description="No TEI"
            ),
            source=SourceConfig(type="local", location="/tmp"),
            filters=FilterConfig(method="directory"),
            citation=CitationConfig(),
            embedding=EmbeddingConfig(),
            processing=ProcessingConfig(),
        )
        assert cfg.tei_workflow is None

    def test_tei_workflow_with_mappings_and_facets(self):
        cfg = TeiWorkflowConfig(
            enabled=True,
            metadata_mappings=[
                TeiMetadataMapping(tei_field="tei_sender", role="author"),
                TeiMetadataMapping(tei_field="tei_place", role="location"),
            ],
            facets=[
                TeiFacetConfig(field="tei_sender", label="Sender", type="text"),
                TeiFacetConfig(field="tei_date", label="Date", type="date_range"),
                TeiFacetConfig(field="tei_keywords", label="Keywords", type="keyword"),
            ],
        )
        assert len(cfg.metadata_mappings) == 2
        assert len(cfg.facets) == 3
        assert cfg.facets[1].type == "date_range"


# ---------------------------------------------------------------------------
# CorpusAnalyzer TEI discovery tests
# ---------------------------------------------------------------------------


class TestCorpusAnalyzerTeiDiscovery:
    """Test the analyze_tei_corpus method on CorpusAnalyzer."""

    def test_detects_tei_corpus(self, tei_corpus_dir):
        analyzer = CorpusAnalyzer()
        result = analyzer.analyze_tei_corpus(str(tei_corpus_dir))
        assert result["is_tei_corpus"] is True
        # 3 TEI files (letters + fragment), 1 non-TEI XML
        assert result["tei_file_count"] == 3
        assert result["non_tei_xml_count"] == 1
        assert result["total_xml_files"] == 4

    def test_schema_discovery_returns_elements(self, tei_corpus_dir):
        analyzer = CorpusAnalyzer()
        result = analyzer.analyze_tei_corpus(str(tei_corpus_dir), sample_size=10)
        schema = result["schema_discovery"]
        assert schema is not None
        assert schema["tei_files"] == 3
        # sender is present in 2 of 3 TEI files
        assert schema["elements"]["correspDesc/sender"]["count"] == 2
        # title is present in all 3
        assert schema["elements"]["title"]["count"] == 3

    def test_coverage_percentages(self, tei_corpus_dir):
        analyzer = CorpusAnalyzer()
        result = analyzer.analyze_tei_corpus(str(tei_corpus_dir))
        schema = result["schema_discovery"]
        # 3 files sampled, title in 3 → 100%
        assert schema["elements"]["title"]["percentage"] == 100.0
        # sender in 2 of 3 → 66.7%
        assert schema["elements"]["correspDesc/sender"]["percentage"] == pytest.approx(
            66.7, abs=0.1
        )

    def test_no_tei_files_returns_false(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        (d / "plain.xml").write_text(NON_TEI_XML, encoding="utf-8")
        analyzer = CorpusAnalyzer()
        result = analyzer.analyze_tei_corpus(str(d))
        assert result["is_tei_corpus"] is False
        assert result["schema_discovery"] is None

    def test_empty_directory(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        analyzer = CorpusAnalyzer()
        result = analyzer.analyze_tei_corpus(str(d))
        assert result["is_tei_corpus"] is False
        assert result["tei_file_count"] == 0

    def test_nonexistent_path_raises(self):
        analyzer = CorpusAnalyzer()
        with pytest.raises(ValueError, match="Path does not exist"):
            analyzer.analyze_tei_corpus("/nonexistent/path")

    def test_sample_values_populated(self, tei_corpus_dir):
        analyzer = CorpusAnalyzer()
        result = analyzer.analyze_tei_corpus(str(tei_corpus_dir))
        schema = result["schema_discovery"]
        sender_values = schema["elements"]["correspDesc/sender"]["sample_values"]
        assert len(sender_values) >= 1
        # Check known senders appear in sample values
        found_senders = set(sender_values)
        assert any("Darwin" in v for v in found_senders)


# ---------------------------------------------------------------------------
# End-to-end TEI build pipeline tests
# ---------------------------------------------------------------------------


class TestTeiPipelineEndToEnd:
    """Test the full TEI pipeline: files → parser → chunking → Documents."""

    def test_whole_document_pipeline(self, tei_corpus_dir):
        """Build TEI corpus with whole-document strategy, verify output."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
            corpus_name="test_tei",
            filter_id="darwin_letters",
            filter_label="Darwin Letters",
        )
        # 3 TEI files → 3 documents (non-TEI and txt are skipped)
        assert len(docs) == 3

    def test_metadata_fields_on_chunks(self, tei_corpus_dir):
        """Verify TEI metadata fields appear on generated Documents."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
            corpus_name="test_tei",
            filter_id="darwin_letters",
            filter_label="Darwin Letters",
        )
        # Find the Darwin→Hooker letter
        darwin_doc = next(
            d for d in docs if d.metadata.get("tei_sender") == "Darwin, Charles Robert"
        )
        meta = darwin_doc.metadata

        # TEI fields
        assert meta["tei_sender"] == "Darwin, Charles Robert"
        assert meta["tei_recipient"] == "Hooker, Joseph Dalton"
        assert meta["tei_date"] == "1859-03-15"
        assert meta["tei_place"] == "Down"
        assert "natural selection" in meta["tei_keywords"]
        assert "species theory" in meta.get("tei_abstract", "")

        # Backward compatibility fields
        assert meta["filter_1"] == "darwin_letters"
        assert meta["corpus"] == "darwin_letters"
        assert meta["corpus_label"] == "Darwin Letters"
        assert meta["date"] == "1859-03-15"

    def test_chunk_text_contains_metadata_prefix(self, tei_corpus_dir):
        """Verify chunk text has [Metadata]/[Content] delimiters."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
            corpus_name="test_tei",
        )
        darwin_doc = next(
            d for d in docs if d.metadata.get("tei_sender") == "Darwin, Charles Robert"
        )
        content = darwin_doc.page_content

        assert "[Metadata]" in content
        assert "[/Metadata]" in content
        assert "[Content]" in content
        assert "[/Content]" in content
        assert "Sender: Darwin, Charles Robert" in content
        assert "Recipient: Hooker, Joseph Dalton" in content
        assert "Date: 1859-03-15" in content

    def test_chunk_text_contains_body(self, tei_corpus_dir):
        """Verify body text appears after [Content] delimiter."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
            corpus_name="test_tei",
        )
        darwin_doc = next(
            d for d in docs if d.metadata.get("tei_sender") == "Darwin, Charles Robert"
        )
        content = darwin_doc.page_content
        assert "species question" in content
        assert "Galapagos finches" in content

    def test_structural_chunking_pipeline(self, tei_corpus_dir):
        """Build TEI corpus with structural strategy, verify splitting."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="structural",
            chunk_size=200,
            chunk_overlap=0,
            corpus_name="test_tei",
        )
        # With small chunk_size, multi-paragraph letters should produce
        # more chunks than the 3 source files
        assert len(docs) >= 3

    def test_structural_chunks_all_have_metadata(self, tei_corpus_dir):
        """Each structural chunk should carry the document metadata."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="structural",
            chunk_size=200,
            chunk_overlap=0,
            corpus_name="test_tei",
            filter_id="darwin",
            filter_label="Darwin",
        )
        for doc in docs:
            # Every chunk should have corpus metadata
            assert "chunk_id" in doc.metadata
            assert doc.metadata.get("corpus") == "darwin"

    def test_selected_fields_filtering(self, tei_corpus_dir):
        """selected_fields should limit which TEI fields appear."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
            selected_fields=["tei_sender", "tei_date"],
        )
        for doc in docs:
            meta = doc.metadata
            # Excluded fields should not be present
            assert "tei_keywords" not in meta
            assert "tei_abstract" not in meta
            assert "tei_place" not in meta
            # Included fields should be present (if the file has them)
            if "Darwin" in doc.page_content:
                assert "tei_sender" in meta
                assert "tei_date" in meta

    def test_custom_metadata_mappings(self, tei_corpus_dir):
        """Custom mappings should add aliased fields."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
            metadata_mappings={"tei_sender": "author", "tei_place": "location"},
        )
        darwin_doc = next(
            d for d in docs if d.metadata.get("tei_sender") == "Darwin, Charles Robert"
        )
        assert darwin_doc.metadata["author"] == "Darwin, Charles Robert"
        assert darwin_doc.metadata["location"] == "Down"
        # Original fields still present
        assert darwin_doc.metadata["tei_sender"] == "Darwin, Charles Robert"

    def test_non_tei_files_excluded(self, tei_corpus_dir):
        """Non-TEI XML and .txt files should be skipped."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
        )
        filenames = [d.metadata["source_filename"] for d in docs]
        assert "generic.xml" not in filenames
        assert "readme.txt" not in filenames

    def test_chunk_ids_unique_across_corpus(self, tei_corpus_dir):
        """All chunk IDs should be unique across the corpus."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
            corpus_name="test_tei",
        )
        ids = [d.metadata["chunk_id"] for d in docs]
        assert len(ids) == len(set(ids))

    def test_minimal_tei_produces_chunks(self, tei_corpus_dir):
        """TEI files with minimal metadata should still produce chunks."""
        docs = chunk_tei_corpus(
            directory=tei_corpus_dir,
            strategy="whole_document",
        )
        fragment_doc = next(
            d for d in docs if d.metadata["source_filename"] == "fragment_003.xml"
        )
        # Should have title but not sender/recipient
        assert fragment_doc.metadata.get("tei_title") == "Fragment"
        assert "tei_sender" not in fragment_doc.metadata
        assert "fragmentary note" in fragment_doc.page_content


# ---------------------------------------------------------------------------
# Corpus builder TEI routing tests
# ---------------------------------------------------------------------------


try:
    import torch  # noqa: F401
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
class TestCorpusBuilderTeiRouting:
    """Test _is_tei_workflow and _load_tei_documents on UniversalCorpusBuilder."""

    def test_is_tei_workflow_when_enabled(self, tei_workflow_config):
        from backend.modules.corpus_builder import UniversalCorpusBuilder

        builder = UniversalCorpusBuilder(tei_workflow_config)
        assert builder._is_tei_workflow() is True

    def test_is_tei_workflow_when_disabled(self):
        from backend.modules.corpus_builder import UniversalCorpusBuilder

        config = CorpusConfig(
            metadata=CorpusMetadata(
                name="plain", display_name="Plain", description="No TEI"
            ),
            source=SourceConfig(type="local", location="/tmp"),
            filters=FilterConfig(method="directory"),
            citation=CitationConfig(),
            embedding=EmbeddingConfig(),
            processing=ProcessingConfig(),
        )
        builder = UniversalCorpusBuilder(config)
        assert builder._is_tei_workflow() is False

    def test_is_tei_workflow_when_none(self):
        from backend.modules.corpus_builder import UniversalCorpusBuilder

        config = CorpusConfig(
            metadata=CorpusMetadata(
                name="plain", display_name="Plain", description="No TEI"
            ),
            source=SourceConfig(type="local", location="/tmp"),
            filters=FilterConfig(method="directory"),
            citation=CitationConfig(),
            embedding=EmbeddingConfig(),
            processing=ProcessingConfig(),
            tei_workflow=None,
        )
        builder = UniversalCorpusBuilder(config)
        assert builder._is_tei_workflow() is False

    def test_load_tei_documents(self, tei_workflow_config, tei_corpus_dir):
        from backend.modules.corpus_builder import UniversalCorpusBuilder

        builder = UniversalCorpusBuilder(tei_workflow_config)
        docs = builder._load_tei_documents(tei_corpus_dir)
        # 3 TEI files → 3 whole-document chunks
        assert len(docs) == 3

        # Check metadata from config propagated correctly
        darwin_doc = next(
            d for d in docs if d.metadata.get("tei_sender") == "Darwin, Charles Robert"
        )
        assert darwin_doc.metadata["filter_1"] == "darwin_letters"
        assert darwin_doc.metadata["corpus_label"] == "Darwin Letters"

    def test_load_tei_documents_with_structural_chunking(
        self, tei_corpus_dir
    ):
        from backend.modules.corpus_builder import UniversalCorpusBuilder

        config = CorpusConfig(
            metadata=CorpusMetadata(
                name="test", display_name="Test", description="Test"
            ),
            source=SourceConfig(
                type="local",
                location=str(tei_corpus_dir),
                file_extensions=".xml",
            ),
            filters=FilterConfig(
                method="tei",
                filters=[
                    FilterDefinition(id="letters", label="Letters", pattern="**/*.xml"),
                ],
            ),
            citation=CitationConfig(),
            embedding=EmbeddingConfig(chunk_size=200, chunk_overlap=0),
            processing=ProcessingConfig(),
            tei_workflow=TeiWorkflowConfig(
                enabled=True,
                chunking_strategy="structural",
            ),
        )
        builder = UniversalCorpusBuilder(config)
        docs = builder._load_tei_documents(tei_corpus_dir)
        # With small chunk size, multi-paragraph letter may split
        assert len(docs) >= 3

    def test_load_tei_documents_with_metadata_mappings(
        self, tei_corpus_dir
    ):
        from backend.modules.corpus_builder import UniversalCorpusBuilder

        config = CorpusConfig(
            metadata=CorpusMetadata(
                name="test", display_name="Test", description="Test"
            ),
            source=SourceConfig(
                type="local",
                location=str(tei_corpus_dir),
                file_extensions=".xml",
            ),
            filters=FilterConfig(
                method="tei",
                filters=[
                    FilterDefinition(id="letters", label="Letters", pattern="**/*.xml"),
                ],
            ),
            citation=CitationConfig(),
            embedding=EmbeddingConfig(),
            processing=ProcessingConfig(),
            tei_workflow=TeiWorkflowConfig(
                enabled=True,
                metadata_mappings=[
                    TeiMetadataMapping(tei_field="tei_sender", role="author"),
                ],
            ),
        )
        builder = UniversalCorpusBuilder(config)
        docs = builder._load_tei_documents(tei_corpus_dir)
        darwin_doc = next(
            d for d in docs if d.metadata.get("tei_sender") == "Darwin, Charles Robert"
        )
        assert darwin_doc.metadata["author"] == "Darwin, Charles Robert"
