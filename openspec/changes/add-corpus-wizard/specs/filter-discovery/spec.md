# Capability: Intelligent Filter Discovery

## ADDED Requirements

### Requirement: Metadata-driven filter discovery
The system SHALL use user-provided metadata to guide filter discovery, combining domain knowledge with structural analysis.

#### Scenario: Discover person-based filters
GIVEN a user indicates the corpus contains correspondence from "Charles Darwin, Thomas Huxley, Alfred Wallace"
WHEN the system analyzes the corpus
THEN it specifically searches for these names in:
  - Directory names
  - File names
  - XML metadata tags (if applicable)
  - Document content samples
AND creates filters for each person found with confidence scores
AND prioritizes these filters in the suggestion list

#### Scenario: Discover temporal filters
GIVEN a user indicates the corpus spans 1825-1882
WHEN the system analyzes the corpus
THEN it automatically suggests temporal groupings:
  - By decade if span > 50 years
  - By year if span 10-50 years
  - By month if span < 10 years
AND validates these against actual dates found in the corpus
AND adjusts groupings based on document distribution

### Requirement: Structural pattern recognition
The system SHALL analyze directory structure to identify organizational patterns for filter creation.

#### Scenario: Detect hierarchical organization
GIVEN a corpus organized as /Year/Author/document.txt
WHEN the system analyzes the structure
THEN it identifies the hierarchical pattern
AND suggests multi-level filters:
  - Primary: by year
  - Secondary: by author
  - Combined: year + author
AND shows document distribution for each level

#### Scenario: Detect flat organization with naming patterns
GIVEN a corpus with flat structure but consistent naming like "YYYY-MM-DD_author_title.txt"
WHEN the system analyzes file names
THEN it extracts patterns using regex
AND suggests filters based on name components:
  - Date-based filters from YYYY-MM-DD
  - Author filters from the author field
  - Topic filters from title keywords
AND validates patterns across all files

### Requirement: Content-based filter extraction
The system SHALL sample document content to discover metadata for filter creation.

#### Scenario: Extract XML metadata for filters
GIVEN a corpus contains XML documents with metadata tags
WHEN the system samples documents
THEN it identifies common XML elements like:
  - <author>, <recipient>, <subject>
  - <date>, <location>, <category>
  - Custom domain-specific tags
AND creates filter suggestions based on element values
AND shows value distribution across the corpus

#### Scenario: Extract headers from text documents
GIVEN a corpus contains structured text documents
WHEN the system samples documents
THEN it identifies consistent header patterns like:
  - "Date:", "From:", "To:", "Subject:"
  - Chapter headings or section markers
  - Standardized metadata blocks
AND extracts values for filter creation
AND validates patterns across multiple samples

### Requirement: Filter validation and refinement
The system SHALL allow users to validate and refine discovered filters before committing to them.

#### Scenario: Test filter effectiveness
GIVEN a set of suggested filters
WHEN the user wants to validate them
THEN the system provides:
  - Document count for each filter
  - Sample documents matching each filter
  - Overlap analysis between filters
  - Coverage report (documents matching no filters)
  - Performance impact estimate
AND allows iterative refinement based on results

## REMOVED Requirements

### Requirement: Hardcoded corpus patterns
The system SHALL NO LONGER rely on hardcoded patterns like "AU/NZ/UK" for corpus organization.

#### Scenario: Support arbitrary corpus structure
GIVEN a corpus with non-parliamentary structure
WHEN the system processes it
THEN it does not require specific directory names
AND does not assume three-letter country codes
AND discovers organization from actual structure
AND generates appropriate corpus IDs dynamically