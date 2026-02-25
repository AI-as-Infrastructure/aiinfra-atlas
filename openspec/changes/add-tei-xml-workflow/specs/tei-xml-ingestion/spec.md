# TEI-XML Ingestion Capability

## ADDED Requirements

### Requirement: TEI-XML Document Parsing

The system SHALL parse TEI-XML documents using namespace-aware XML parsing, extracting structured metadata from the `teiHeader` and text content from the `body`.

#### Scenario: Parse TEI-XML document with correspDesc
- **GIVEN** a TEI-XML file containing `<correspDesc>` with sender, recipient, date, and place
- **WHEN** the TEI parser processes the file
- **THEN** the parser extracts sender name, recipient name, date (ISO 8601), and place as structured metadata
- **AND** the body text is extracted with XML tags stripped

#### Scenario: Parse TEI-XML document with textClass keywords
- **GIVEN** a TEI-XML file containing `<textClass>` with `<keywords>` elements
- **WHEN** the TEI parser processes the file
- **THEN** all keyword terms are extracted as a list
- **AND** term types (if present via `@type` attribute) are preserved

#### Scenario: Parse TEI-XML document with abstract
- **GIVEN** a TEI-XML file containing `<abstract>` in the `profileDesc`
- **WHEN** the TEI parser processes the file
- **THEN** the abstract text is extracted as metadata
- **AND** the abstract is available for prepending to chunks

#### Scenario: Handle TEI namespace variations
- **GIVEN** a TEI-XML file using either default namespace (`xmlns="http://www.tei-c.org/ns/1.0"`) or no namespace
- **WHEN** the TEI parser processes the file
- **THEN** metadata extraction succeeds regardless of namespace declaration

#### Scenario: Handle missing metadata fields gracefully
- **GIVEN** a TEI-XML file where some expected metadata elements are absent
- **WHEN** the TEI parser processes the file
- **THEN** available fields are extracted
- **AND** missing fields are omitted from the metadata dictionary (no null values or empty strings)

### Requirement: TEI Schema Discovery

The system SHALL discover available TEI metadata elements by analysing a sample of TEI-XML files from the corpus, reporting which elements are present and their frequency.

#### Scenario: Discover metadata elements in corpus
- **GIVEN** a directory of TEI-XML files
- **WHEN** the schema discovery runs on a sample of files
- **THEN** it reports which teiHeader elements are present (e.g., correspDesc, textClass, abstract, titleStmt)
- **AND** it reports the frequency of each element across the sample

#### Scenario: Discovery handles heterogeneous corpus
- **GIVEN** a corpus where some files have correspDesc and others do not
- **WHEN** the schema discovery analyses the sample
- **THEN** it reports each element with its coverage percentage
- **AND** the user can decide which elements to extract based on coverage

### Requirement: XML-Aware Chunking

The system SHALL provide two chunking strategies for TEI-XML documents: structural chunking that splits on TEI elements, and whole-document chunking that keeps each document as a single chunk.

#### Scenario: Structural chunking splits on TEI elements
- **GIVEN** a TEI-XML document with multiple `<div>` or `<p>` elements in the body
- **WHEN** structural chunking is applied
- **THEN** the document is split at structural element boundaries
- **AND** each chunk inherits the document-level metadata from the teiHeader
- **AND** small adjacent chunks are merged up to the configured chunk size

#### Scenario: Whole-document chunking preserves document unity
- **GIVEN** a TEI-XML document (e.g., a short letter)
- **WHEN** whole-document chunking is applied
- **THEN** the entire body text forms a single chunk
- **AND** the document-level metadata from the teiHeader is attached

#### Scenario: Metadata prepended to chunk text
- **GIVEN** a chunk produced by either chunking strategy
- **WHEN** the chunk is prepared for embedding
- **THEN** extracted metadata (sender, date, place, abstract, keywords) is prepended to the chunk text in a structured format
- **AND** the prepended metadata is separated from content by clear delimiters

### Requirement: TEI Metadata to ChromaDB Fields

The system SHALL store extracted TEI metadata as ChromaDB chunk metadata fields with a `tei_` prefix, enabling filtering at query time.

#### Scenario: Metadata fields stored in ChromaDB
- **GIVEN** a TEI-XML document with sender, recipient, date, place, and keywords
- **WHEN** the document is chunked and stored in ChromaDB
- **THEN** each chunk's metadata includes `tei_sender`, `tei_recipient`, `tei_date`, `tei_place`, and `tei_keywords`
- **AND** `filter_1` and `filter_2` are populated for backward compatibility

#### Scenario: Date stored as ISO 8601 string
- **GIVEN** a TEI-XML document with `<date when="1859-03-15">`
- **WHEN** the date is stored in ChromaDB metadata
- **THEN** the value is stored as the string `"1859-03-15"`
- **AND** the format enables string comparison for range queries

### Requirement: XML Parsing Security

The system SHALL parse XML with external entity resolution disabled and network access blocked to prevent XXE attacks.

#### Scenario: XXE protection enabled
- **GIVEN** a TEI-XML file containing an external entity declaration
- **WHEN** the parser processes the file
- **THEN** external entities are not resolved
- **AND** no network requests are made during parsing

#### Scenario: Malformed XML rejected
- **GIVEN** a file that is not well-formed XML
- **WHEN** the parser attempts to process the file
- **THEN** the file is rejected with a clear error message
- **AND** processing continues with remaining files

### Requirement: TEI Wizard Workflow Steps

The system SHALL provide dedicated wizard steps for TEI-XML corpora: schema discovery, metadata mapping, chunking strategy selection, and filter configuration.

#### Scenario: Wizard enables XML workflow
- **GIVEN** a user starts the corpus wizard
- **WHEN** they select "XML Workflow" in Step 1
- **THEN** TEI-specific steps are added to the wizard flow
- **AND** the source selection step accepts XML file directories

#### Scenario: Schema discovery step presents available fields
- **GIVEN** a user has selected a directory of TEI-XML files
- **WHEN** the schema discovery step runs
- **THEN** discovered metadata elements are displayed with their coverage percentages
- **AND** the user can select which fields to extract

#### Scenario: Metadata mapping step with defaults
- **GIVEN** the schema discovery has identified TEI elements
- **WHEN** the metadata mapping step is displayed
- **THEN** common TEI patterns are pre-mapped to metadata roles (e.g., correspAction/persName to sender)
- **AND** the user can adjust or override the default mappings

#### Scenario: Chunking strategy selection with preview
- **GIVEN** a user is on the chunking strategy step
- **WHEN** they select structural or whole-document chunking
- **THEN** a preview shows example chunk boundaries from sample documents
- **AND** the prepended metadata is visible in the preview

#### Scenario: Filter configuration step
- **GIVEN** extracted metadata fields are available
- **WHEN** the user reaches the filter configuration step
- **THEN** they can select which fields become searchable facets
- **AND** the system suggests appropriate facet types (text, date_range, keyword) based on field content

## MODIFIED Requirements

### Requirement: Corpus Builder XML Handling

The corpus builder SHALL route TEI-XML corpora through the TEI-specific parsing and chunking pipeline instead of the generic `UnstructuredXMLLoader`.

#### Scenario: TEI-XML corpus uses TEI pipeline
- **GIVEN** a corpus configured with XML workflow type
- **WHEN** the corpus builder processes the files
- **THEN** TEI-XML files are parsed by `tei_xml_parser.py`
- **AND** chunking uses `tei_chunking.py` with the user's chosen strategy
- **AND** `UnstructuredXMLLoader` is not invoked

#### Scenario: Non-TEI XML falls back to existing loader
- **GIVEN** a corpus containing XML files that are not TEI-XML
- **WHEN** the corpus builder processes the files using the folder workflow
- **THEN** the existing `UnstructuredXMLLoader` pipeline is used
- **AND** no TEI-specific processing is attempted

### Requirement: Corpus Analyser XML Detection

The corpus analyser SHALL detect TEI-XML files and report available metadata elements during analysis.

#### Scenario: Analyser identifies TEI-XML corpus
- **GIVEN** a directory containing files with `.xml` extension
- **WHEN** the analyser examines the files
- **THEN** it detects TEI-XML structure (presence of `<TEI>` root element or TEI namespace)
- **AND** it reports discovered teiHeader elements and their frequency

#### Scenario: Analyser distinguishes TEI from generic XML
- **GIVEN** a directory with mixed XML files (some TEI, some not)
- **WHEN** the analyser processes the directory
- **THEN** it reports the count of TEI-XML vs non-TEI XML files
- **AND** it recommends the appropriate workflow based on the majority

### Requirement: Manifest Schema Extension

The manifest SHALL support version 1.5 with a `facets` array declaring filterable metadata fields, their types, and available values.

#### Scenario: Manifest v1.5 includes facets
- **GIVEN** a TEI-XML corpus has been built with filter configuration
- **WHEN** the manifest is generated
- **THEN** it includes a `facets` array with field name, label, type, and values for each configured facet
- **AND** the manifest version is set to `"1.5"`

#### Scenario: Manifest v1.5 backward compatible
- **GIVEN** a corpus built without TEI-XML workflow (folder workflow)
- **WHEN** the manifest is generated
- **THEN** the `facets` array is empty or absent
- **AND** existing manifest consumers continue to work without modification
