# Dynamic Corpus Filters

## ADDED Requirements

### Requirement: Manifest-Based Corpus Discovery
The system MUST read available corpus options from `manifest.json` instead of hardcoded values.

#### Scenario: Load Corpus Values from Manifest
Given a valid `manifest.json` exists at `backend/targets/manifest.json`
When the system loads corpus options
Then the corpus values are read from `fields.corpus.values`
And an "all" option is prepended to the list

#### Scenario: Generate Labels from Corpus IDs
Given a corpus ID follows the pattern `{year}_{country_code}`
When a label is generated for the corpus
Then the label follows the format "{Country Name} ({Year})"
And the country name is derived from a known country code mapping

#### Scenario: Handle Unknown Country Codes
Given a corpus ID with an unrecognized country code
When a label is generated
Then the corpus ID is used as the label (fallback behavior)

### Requirement: Graceful Degradation
The system MUST handle missing or invalid manifests gracefully.

#### Scenario: Missing Manifest File
Given `manifest.json` does not exist
When corpus options are requested
Then an empty list is returned for corpus-specific options
And only the "all" option is available
And a warning is logged

#### Scenario: Invalid Manifest Format
Given `manifest.json` exists but has invalid JSON
When corpus options are requested
Then an empty list is returned for corpus-specific options
And an error is logged

#### Scenario: Missing Corpus Field in Manifest
Given `manifest.json` exists but lacks `fields.corpus.values`
When corpus options are requested
Then corpus IDs are derived from `stats.corpora` keys as fallback
And a warning is logged

## MODIFIED Requirements

### Requirement: Corpus Filter Validation
Corpus filter validation MUST use dynamically loaded options instead of hardcoded values.

#### Scenario: Valid Corpus Filter
Given a query request with corpus_filter set to a valid corpus ID
When the filter is validated
Then the filter is accepted if it exists in the manifest's corpus values

#### Scenario: Invalid Corpus Filter
Given a query request with an unrecognized corpus_filter value
When the filter is validated
Then the filter defaults to "all"
And a warning is logged

## REMOVED Requirements

### Requirement: Hardcoded Corpus Lists
Hardcoded corpus option lists MUST be removed from:
- `backend/retrievers/hansard_retriever.py` (CORPUS_OPTIONS constant)
- `backend/modules/config.py` (default corpus_options)
- `backend/app.py` (validation list)

#### Scenario: No Hardcoded Corpus Values in Code
Given the refactoring is complete
When searching for hardcoded corpus lists
Then no hardcoded lists of corpus IDs exist in Python files
And all corpus-related configuration comes from manifest.json
