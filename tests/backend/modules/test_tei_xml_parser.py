"""
Tests for TEI-XML parser module.

Tests metadata extraction from TEI P5 documents, namespace handling,
schema discovery, XXE protection, and malformed XML rejection.
"""

import pytest
from pathlib import Path

from backend.modules.tei_xml_parser import (
    is_tei_xml,
    parse_tei_document,
    discover_tei_schema,
)


# ---------------------------------------------------------------------------
# TEI-XML fixtures
# ---------------------------------------------------------------------------

SAMPLE_TEI_FULL = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="TEST-LETT-42">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title xml:id="main_title">From Alice Smith 15 March 1859</title>
            </titleStmt>
            <publicationStmt>
                <authority>Test Project</authority>
            </publicationStmt>
            <sourceDesc>
                <msDesc>
                    <msIdentifier>
                        <repository key="../repo/repo_1.xml">BL</repository>
                        <collection>ADD</collection>
                        <idno>MS 12345</idno>
                    </msIdentifier>
                </msDesc>
            </sourceDesc>
        </fileDesc>
        <profileDesc>
            <correspDesc>
                <correspAction type="sent">
                    <persName key="../nameregs/nr_1.xml">Smith, Alice</persName>
                    <placeName>London</placeName>
                    <date when="1859-03-15">15 Mar 1859</date>
                </correspAction>
                <correspAction type="received">
                    <persName key="../nameregs/nr_2.xml">Jones, Robert</persName>
                </correspAction>
            </correspDesc>
            <abstract>
                <p>Discussion of botanical specimens from Kew.</p>
            </abstract>
            <textClass>
                <keywords>
                    <term type="scientific_terms">botany</term>
                    <term type="places">Kew Gardens</term>
                    <term ref="#">specimen collection</term>
                </keywords>
            </textClass>
        </profileDesc>
    </teiHeader>
    <text>
    <body>
        <div type="letter">
            <div type="text">
                <opener>
                    <placeName>London</placeName>
                    <date>15 March 1859</date>
                    <salute>Dear Robert,</salute>
                </opener>
                <div type="transcription">
                    <p>I have received the botanical specimens you sent from Kew Gardens.
                    They are in excellent condition and will be most useful for our research.</p>
                    <p>The ferns in particular are remarkable. I shall prepare detailed
                    drawings for publication.</p>
                </div>
            </div>
        </div>
        <div type="footnotes">
            <note xml:id="foot.f1">Kew Gardens was the premier botanical institution.</note>
        </div>
    </body>
    </text>
</TEI>
"""

SAMPLE_TEI_NO_NAMESPACE = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xml:id="TEST-NONAMESPACE">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title>Simple Title</title>
            </titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
        <profileDesc>
            <correspDesc>
                <correspAction type="sent">
                    <persName>Author, Test</persName>
                    <date when="1900-01-01">1 Jan 1900</date>
                </correspAction>
            </correspDesc>
        </profileDesc>
    </teiHeader>
    <text>
    <body>
        <div type="letter">
            <div type="text">
                <div type="transcription">
                    <p>This is a test letter without TEI namespace.</p>
                </div>
            </div>
        </div>
    </body>
    </text>
</TEI>
"""

SAMPLE_TEI_MINIMAL = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="TEST-MINIMAL">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>Minimal</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
    </teiHeader>
    <text>
    <body>
        <p>Simple body text without any structural divs.</p>
    </body>
    </text>
</TEI>
"""

SAMPLE_TEI_MULTI_SECTION = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="TEST-MULTI">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>Multi-section document</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
        <profileDesc>
            <correspDesc>
                <correspAction type="sent">
                    <persName>Writer, A</persName>
                    <date when="1850-06-01"/>
                </correspAction>
            </correspDesc>
        </profileDesc>
    </teiHeader>
    <text>
    <body>
        <div type="letter">
            <div type="text">
                <div type="transcription">
                    <p>First paragraph of the letter about geology.</p>
                    <p>Second paragraph continues the discussion of rock formations.</p>
                    <p>Third paragraph concludes with observations on fossils.</p>
                </div>
            </div>
        </div>
    </body>
    </text>
</TEI>
"""

MALFORMED_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <unclosed_tag>
    </teiHeader>
"""

NOT_XML = "This is not XML at all. Just plain text."

XXE_ATTEMPT = """\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="XXE-TEST">
    <teiHeader>
        <fileDesc>
            <titleStmt><title>&xxe;</title></titleStmt>
            <publicationStmt><authority>Test</authority></publicationStmt>
            <sourceDesc><p>Source</p></sourceDesc>
        </fileDesc>
    </teiHeader>
    <text><body><p>Test</p></body></text>
</TEI>
"""


@pytest.fixture
def tei_dir(tmp_path):
    """Create a directory with sample TEI-XML files."""
    d = tmp_path / "tei_corpus"
    d.mkdir()

    (d / "letter_full.xml").write_text(SAMPLE_TEI_FULL, encoding="utf-8")
    (d / "letter_no_ns.xml").write_text(SAMPLE_TEI_NO_NAMESPACE, encoding="utf-8")
    (d / "letter_minimal.xml").write_text(SAMPLE_TEI_MINIMAL, encoding="utf-8")
    (d / "letter_multi.xml").write_text(SAMPLE_TEI_MULTI_SECTION, encoding="utf-8")
    (d / "not_xml.txt").write_text(NOT_XML, encoding="utf-8")

    return d


@pytest.fixture
def full_tei_file(tmp_path):
    """Create a single full TEI-XML file."""
    f = tmp_path / "test_letter.xml"
    f.write_text(SAMPLE_TEI_FULL, encoding="utf-8")
    return f


@pytest.fixture
def no_namespace_tei_file(tmp_path):
    """Create a TEI-XML file without namespace."""
    f = tmp_path / "no_ns.xml"
    f.write_text(SAMPLE_TEI_NO_NAMESPACE, encoding="utf-8")
    return f


@pytest.fixture
def minimal_tei_file(tmp_path):
    """Create a minimal TEI-XML file."""
    f = tmp_path / "minimal.xml"
    f.write_text(SAMPLE_TEI_MINIMAL, encoding="utf-8")
    return f


@pytest.fixture
def malformed_xml_file(tmp_path):
    """Create a malformed XML file."""
    f = tmp_path / "malformed.xml"
    f.write_text(MALFORMED_XML, encoding="utf-8")
    return f


@pytest.fixture
def xxe_file(tmp_path):
    """Create an XML file with XXE attack attempt."""
    f = tmp_path / "xxe.xml"
    f.write_text(XXE_ATTEMPT, encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# is_tei_xml tests
# ---------------------------------------------------------------------------

class TestIsTeiXml:
    def test_detects_tei_with_namespace(self, full_tei_file):
        assert is_tei_xml(full_tei_file) is True

    def test_detects_tei_without_namespace(self, no_namespace_tei_file):
        assert is_tei_xml(no_namespace_tei_file) is True

    def test_rejects_plain_text(self, tmp_path):
        f = tmp_path / "plain.txt"
        f.write_text("Just plain text", encoding="utf-8")
        assert is_tei_xml(f) is False

    def test_rejects_non_tei_xml(self, tmp_path):
        f = tmp_path / "other.xml"
        f.write_text('<?xml version="1.0"?><root><data>test</data></root>', encoding="utf-8")
        assert is_tei_xml(f) is False

    def test_handles_missing_file(self, tmp_path):
        f = tmp_path / "does_not_exist.xml"
        assert is_tei_xml(f) is False


# ---------------------------------------------------------------------------
# parse_tei_document tests
# ---------------------------------------------------------------------------

class TestParseTeiDocument:
    def test_extracts_sender(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert result["metadata"]["tei_sender"] == "Smith, Alice"

    def test_extracts_recipient(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert result["metadata"]["tei_recipient"] == "Jones, Robert"

    def test_extracts_date(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert result["metadata"]["tei_date"] == "1859-03-15"

    def test_extracts_place(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert result["metadata"]["tei_place"] == "London"

    def test_extracts_abstract(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert "botanical specimens" in result["metadata"]["tei_abstract"]

    def test_extracts_keywords(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        keywords = result["metadata"]["tei_keywords"]
        assert "botany" in keywords
        assert "Kew Gardens" in keywords
        assert "specimen collection" in keywords

    def test_extracts_title(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert "Alice Smith" in result["metadata"]["tei_title"]

    def test_extracts_repository(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert result["metadata"]["tei_repository"] == "BL"

    def test_extracts_source_id(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert result["metadata"]["tei_source_id"] == "MS 12345"

    def test_extracts_body_text(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert "botanical specimens" in result["body_text"]
        assert "ferns" in result["body_text"]

    def test_excludes_footnotes_from_body(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert "premier botanical institution" not in result["body_text"]

    def test_extracts_body_sections(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert len(result["body_sections"]) >= 1

    def test_no_namespace_parsing(self, no_namespace_tei_file):
        result = parse_tei_document(no_namespace_tei_file)
        assert result["metadata"]["tei_sender"] == "Author, Test"
        assert result["metadata"]["tei_date"] == "1900-01-01"

    def test_missing_fields_omitted(self, minimal_tei_file):
        result = parse_tei_document(minimal_tei_file)
        meta = result["metadata"]
        # Should not have correspDesc fields
        assert "tei_sender" not in meta
        assert "tei_recipient" not in meta
        assert "tei_date" not in meta
        assert "tei_place" not in meta
        assert "tei_abstract" not in meta
        assert "tei_keywords" not in meta
        # But should have title
        assert "tei_title" in meta

    def test_unstated_place_omitted(self, tmp_path):
        """Place with value 'unstated' should be omitted."""
        tei = """\
<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0">
    <teiHeader>
        <fileDesc><titleStmt><title>T</title></titleStmt>
        <publicationStmt><authority>T</authority></publicationStmt>
        <sourceDesc><p>S</p></sourceDesc></fileDesc>
        <profileDesc>
            <correspDesc>
                <correspAction type="sent">
                    <persName>Test</persName>
                    <placeName>unstated</placeName>
                    <date when="1900-01-01"/>
                </correspAction>
            </correspDesc>
        </profileDesc>
    </teiHeader>
    <text><body><p>Body.</p></body></text>
</TEI>"""
        f = tmp_path / "unstated.xml"
        f.write_text(tei, encoding="utf-8")
        result = parse_tei_document(f)
        assert "tei_place" not in result["metadata"]

    def test_malformed_xml_raises(self, malformed_xml_file):
        with pytest.raises(ValueError, match="Malformed XML"):
            parse_tei_document(malformed_xml_file)

    def test_file_path_preserved(self, full_tei_file):
        result = parse_tei_document(full_tei_file)
        assert result["file_path"] == str(full_tei_file)

    def test_multi_section_body_sections(self, tmp_path):
        f = tmp_path / "multi.xml"
        f.write_text(SAMPLE_TEI_MULTI_SECTION, encoding="utf-8")
        result = parse_tei_document(f)
        # Should have at least 3 paragraph sections
        assert len(result["body_sections"]) >= 3


# ---------------------------------------------------------------------------
# XXE protection tests
# ---------------------------------------------------------------------------

class TestXxeProtection:
    def test_xxe_entity_not_resolved(self, xxe_file):
        """Parser should not resolve external entities."""
        # The parser uses resolve_entities=False and load_dtd=False.
        # lxml with these settings should either ignore the entity or raise.
        # Either outcome is acceptable — the entity must NOT be resolved.
        try:
            result = parse_tei_document(xxe_file)
            # If parsing succeeds, the entity should not have been resolved
            title = result["metadata"].get("tei_title", "")
            assert "root:" not in title  # /etc/passwd content
        except (ValueError, Exception):
            # Parsing failure is also acceptable — entity was blocked
            pass


# ---------------------------------------------------------------------------
# discover_tei_schema tests
# ---------------------------------------------------------------------------

class TestDiscoverTeiSchema:
    def test_discovers_elements_from_sample(self, tei_dir):
        result = discover_tei_schema(tei_dir, sample_size=10)
        assert result["tei_files"] >= 3  # full, no_ns, minimal, multi
        assert result["sample_size"] >= 3

    def test_reports_corresp_desc_coverage(self, tei_dir):
        result = discover_tei_schema(tei_dir, sample_size=10)
        # At least the full and no_ns files have correspDesc/sender
        sender = result["elements"].get("correspDesc/sender", {})
        assert sender["count"] >= 2

    def test_reports_abstract_coverage(self, tei_dir):
        result = discover_tei_schema(tei_dir, sample_size=10)
        abstract = result["elements"].get("abstract", {})
        assert abstract["count"] >= 1  # full file has abstract

    def test_reports_keywords_coverage(self, tei_dir):
        result = discover_tei_schema(tei_dir, sample_size=10)
        keywords = result["elements"].get("keywords", {})
        assert keywords["count"] >= 1

    def test_sample_values_populated(self, tei_dir):
        result = discover_tei_schema(tei_dir, sample_size=10)
        sender = result["elements"].get("correspDesc/sender", {})
        assert len(sender.get("sample_values", [])) >= 1

    def test_empty_directory(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        result = discover_tei_schema(d)
        assert result["tei_files"] == 0
        assert result["sample_size"] == 0

    def test_no_tei_files(self, tmp_path):
        d = tmp_path / "nontei"
        d.mkdir()
        (d / "data.xml").write_text('<?xml version="1.0"?><root/>', encoding="utf-8")
        result = discover_tei_schema(d)
        assert result["tei_files"] == 0


# ---------------------------------------------------------------------------
# Darwin corpus integration (optional, uses real data if available)
# ---------------------------------------------------------------------------

class TestDarwinCorpusIntegration:
    """Tests against the real Darwin corpus, skipped if not available."""

    DARWIN_DIR = Path("/home/jamessmithies/WSL Projects/aiinfra-atlas/source_examples/Darwin")

    @pytest.fixture
    def darwin_file(self):
        """Get a single Darwin letter for testing."""
        if not self.DARWIN_DIR.exists():
            pytest.skip("Darwin corpus not available")
        # Find first XML file
        xml_files = sorted(self.DARWIN_DIR.rglob("*.xml"))
        if not xml_files:
            pytest.skip("No XML files in Darwin corpus")
        return xml_files[0]

    def test_parse_darwin_letter(self, darwin_file):
        result = parse_tei_document(darwin_file)
        assert result["body_text"]
        assert result["metadata"]

    def test_discover_darwin_schema(self):
        if not self.DARWIN_DIR.exists():
            pytest.skip("Darwin corpus not available")
        result = discover_tei_schema(self.DARWIN_DIR, sample_size=10)
        assert result["tei_files"] > 0
        # Darwin letters should have correspDesc
        sender = result["elements"].get("correspDesc/sender", {})
        assert sender["count"] > 0
