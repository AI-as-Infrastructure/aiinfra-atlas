# Corpus Wizard Specification

## ADDED Requirements

### Requirement: Simplified Embedding Model Selection

The corpus wizard SHALL provide a simple, transparent embedding model selection without brittle automation.

#### Scenario: Select default embedding model
GIVEN a user is on the embedding model selection step
WHEN they choose "Use Recommended Model"
THEN the system uses sentence-transformers/all-mpnet-base-v2
AND this choice is documented in the manifest

#### Scenario: Select custom embedding model with validation
GIVEN a user is on the embedding model selection step
WHEN they choose "Use Custom Model" and enter a HuggingFace model ID
THEN the system validates the model exists on HuggingFace
AND warns if the model is not sentence-transformers compatible
AND allows proceeding only after successful validation

#### Scenario: Document embedding model in manifest
GIVEN a user has selected an embedding model
WHEN the corpus is built
THEN the manifest.json includes complete model information
AND records whether it was the default or custom selection
AND includes model characteristics (size, dimensions, etc.)

### Requirement: Auto-Generated Corpus-Specific Retriever

The corpus wizard SHALL generate a corpus-specific retriever module for each new corpus.

#### Scenario: Generate retriever during corpus creation
GIVEN a user completes the corpus wizard
WHEN they confirm the corpus build
THEN the system generates a new retriever module in backend/retrievers/{corpus_name}_retriever.py
AND the retriever is based on the template in backend/retrievers/templates/corpus_retriever_template.py
AND the RETRIEVER_MODULE environment variable is set to the new retriever

#### Scenario: Clean default state requires wizard
GIVEN the system is in a clean default state (no pre-existing corpus)
WHEN a user attempts to use the system
THEN they are directed to run the corpus wizard first
AND the system shows a warning that no retriever is configured

### Requirement: Corpus Activation with Selective Overwrite

The corpus activation process SHALL selectively move files to avoid destroying configurations.

#### Scenario: Activate corpus with existing test targets
GIVEN a corpus has been built in create/output/
WHEN the user activates the corpus
THEN the system warns about files that will be overwritten
AND preserves test target .conf files in backend/targets/
AND moves only corpus data files (chroma_db/, bm25_corpus.jsonl, manifest.json)
AND moves the generated retriever to backend/retrievers/

## ADDED Requirements

### Requirement: Two-Filter System

The corpus wizard SHALL support exactly two filters selected from the directory structure.

#### Scenario: Select two folder levels as filters
GIVEN a user has a corpus with hierarchical folder structure
WHEN they reach the "Select Filters" step
THEN they can select up to 2 folder levels to use as filters
AND each selected level becomes filter_1 and filter_2 respectively

#### Scenario: Handle corpora with fewer than 2 levels
GIVEN a user has a corpus with only 1 folder level
WHEN they reach the "Select Filters" step
THEN they can select the single level as filter_1
AND filter_2 remains unset (null)

### Requirement: Optional Metadata Enrichment

The system SHALL provide optional filename metadata extraction for enrichment purposes only.

#### Scenario: Enable filename metadata extraction
GIVEN a user has files with structured filenames like "Friday, 02 August, 1901.txt"
WHEN they enable optional metadata extraction
THEN the system extracts day_of_week="Friday", day=2, month="August", year=1901
AND stores these as enrichment metadata (not for filtering)
AND this metadata appears in search result citations

#### Scenario: Skip metadata extraction
GIVEN a user has files with unstructured filenames
WHEN they skip the optional metadata extraction
THEN the system proceeds with only the 2 selected filters
AND no filename metadata is extracted

### Requirement: Filter Templates

The system SHALL provide pre-defined templates for common filename patterns.

#### Scenario: Select parliamentary date template
GIVEN a user has parliamentary records with date-based filenames
WHEN they select the "Parliamentary Date" template
THEN the system uses the pattern for day_of_week, date, month, year extraction
AND the user does not need to define custom patterns

### Requirement: Backward Compatibility

The system SHALL maintain backward compatibility with existing single-corpus filtering.

#### Scenario: Load existing corpus with single "corpus" field
GIVEN an existing corpus using the "corpus" metadata field
WHEN the corpus is loaded for search
THEN the system treats "corpus" as a legacy filter
AND searches work correctly without modification

### Requirement: Test Target Configuration

The system SHALL create test target configuration files in .conf format.

#### Scenario: Create test target in wizard
GIVEN a user completes the corpus wizard
WHEN they reach the "Create Test Target" step
THEN they can specify LLM provider and model name
AND configure search parameters (search_k, citation_limit)
AND the system generates a .conf file in backend/targets/
AND updates TEST_TARGET in the appropriate .env file

#### Scenario: Load test target from .conf file
GIVEN a test target .conf file exists
WHEN the system loads configuration
THEN it reads the .conf file using INI format parser
AND applies all settings from the file
AND no longer supports legacy .txt format

## MODIFIED Requirements

### Requirement: Document Loading Enhancement

The document loading process SHALL be modified to store filter_1 and filter_2 metadata fields.

#### Scenario: Load documents with 2-filter system
GIVEN a corpus configuration specifies 2 filter levels
WHEN documents are loaded during corpus building
THEN each document has filter_1 and filter_2 extracted from its path
AND these fields are stored in the vector store metadata
AND optional enrichment metadata is added if enabled

### Requirement: Filter Discovery Enhancement

The filter discovery process SHALL limit suggestions to 2 meaningful folder levels.

#### Scenario: Suggest exactly 2 filters
GIVEN documents have been analyzed
WHEN the system suggests filters
THEN it identifies the 2 most meaningful folder levels
AND excludes levels with too many unique values (>20)
AND presents these as filter_1 and filter_2 options

## Retriever Generation

### ADDED: Retriever Template

The corpus wizard uses a template to generate corpus-specific retrievers:

```python
# backend/retrievers/templates/corpus_retriever_template.py
# Template variables:
# - {corpus_name}: Name of the corpus (e.g., "hansard_1901")
# - {CorpusClass}: PascalCase class name (e.g., "Hansard1901")
# - {creation_date}: Date of generation
# - {creation_time}: Time of generation
# - {filter_1_label}: Label for first filter
# - {filter_2_label}: Label for second filter
# - {embedding_model}: Embedding model name

class {CorpusClass}Retriever(BaseRetriever):
    """Auto-generated retriever for {corpus_name}."""

    def __init__(self, config: Dict[str, Any]):
        # Initialize with 2-filter support
        self.filter_1_label = "{filter_1_label}"
        self.filter_2_label = "{filter_2_label}"

    async def _get_relevant_documents(self, query: str, **kwargs):
        # Build filter dict from filter_1 and filter_2
        filter_dict = {}
        config = kwargs.get("config", {})

        if config.get("filter_1") and config["filter_1"] != "all":
            filter_dict["filter_1"] = config["filter_1"]
        if config.get("filter_2") and config["filter_2"] != "all":
            filter_dict["filter_2"] = config["filter_2"]

        # Perform filtered search
        return self.vector_store.similarity_search(
            query=query, k=k, filter=filter_dict
        )
```

## Configuration Schema

### ADDED: Manifest Embedding Model Documentation

The manifest.json SHALL document the selected embedding model:

```json
{
  "corpus_name": "my_corpus",
  "creation_date": "2024-01-22T10:30:00Z",
  "embedding_model": {
    "id": "sentence-transformers/all-mpnet-base-v2",
    "source": "huggingface",
    "is_default": true,
    "validated": true,
    "characteristics": {
      "embedding_dim": 768,
      "max_sequence_length": 512,
      "model_size_mb": 420
    }
  },
  "filters": {
    "filter_1": {
      "label": "Country",
      "values": ["au", "nz", "uk"]
    },
    "filter_2": {
      "label": "Parliament",
      "values": ["house_of_reps", "senate"]
    }
  }
}
```

### MODIFIED: filters section

```yaml
filters:
  # Exactly 2 filters from directory structure
  - id: "filter_1"
    label: "Country"
    source_level: 0
    values: ["au", "nz", "uk"]

  - id: "filter_2"
    label: "Parliament"
    source_level: 1
    values: ["house_of_reps", "senate", "parliament"]
```

### ADDED: metadata_enrichment section (optional)

```yaml
metadata_enrichment:
  enabled: false
  template: "parliamentary_date"  # or "custom"

  # If template is "custom", specify pattern
  custom_pattern: "{day_of_week}, {day:d} {month}, {year:d}"

  # Fields extracted (for display in citations)
  extracted_fields:
    - name: "day_of_week"
      type: "string"
    - name: "day"
      type: "number"
    - name: "month"
      type: "string"
    - name: "year"
      type: "number"
```

### ADDED: Test Target Configuration (.conf format)

```ini
# backend/targets/{corpus_name}_{model}.conf
[metadata]
name = Hansard Claude-4 Configuration
corpus = hansard_1901
created = 2024-01-22
created_by = corpus_wizard
version = 1.0

[llm]
provider = ANTHROPIC
model = claude-sonnet-4-20250514

[retrieval]
search_type = hybrid
search_k = 20
citation_limit = 10
search_score_threshold = 0.0
large_retrieval_single_corpus = 120
large_retrieval_all_corpus = 80

[vector_store]
algorithm = HNSW
chunk_size = 1000
chunk_overlap = 100
pooling = mean+max

[embedding]
model = Livingwithmachines/bert_1890_1900
```

## API Endpoints

### MODIFIED Endpoints

#### POST /api/corpus-wizard/suggest-filters
Modified to return exactly 2 filter suggestions.

Response:
```json
{
  "filter_1": {
    "source_level": 0,
    "label": "Country",
    "values": ["au", "nz", "uk"],
    "count": 3
  },
  "filter_2": {
    "source_level": 1,
    "label": "Parliament",
    "values": ["house_of_reps", "senate"],
    "count": 2
  },
  "enrichment_available": true,
  "detected_pattern": "parliamentary_date"
}
```

### ADDED Endpoints

#### POST /api/corpus-wizard/validate-embedding-model
Validate a HuggingFace embedding model for compatibility.

Request:
```json
{
  "model_id": "sentence-transformers/all-MiniLM-L6-v2"
}
```

Response:
```json
{
  "valid": true,
  "is_sentence_transformer": true,
  "model_info": {
    "id": "sentence-transformers/all-MiniLM-L6-v2",
    "pipeline_tag": "sentence-similarity",
    "downloads": 1000000,
    "likes": 500,
    "warning": null
  }
}
```

Error Response:
```json
{
  "valid": false,
  "error": "Model 'invalid/model-name' not found on HuggingFace"
}
```

#### POST /api/corpus-wizard/test-enrichment
Test enrichment pattern against sample files.

Request:
```json
{
  "template": "parliamentary_date",
  "sample_files": ["Friday, 02 August, 1901.txt"]
}
```

Response:
```json
{
  "success": true,
  "results": [
    {
      "filename": "Friday, 02 August, 1901.txt",
      "extracted": {
        "day_of_week": "Friday",
        "day": 2,
        "month": "August",
        "year": 1901
      }
    }
  ]
}
```

#### POST /api/corpus-wizard/create-test-target
Create a test target configuration file.

Request:
```json
{
  "corpus_name": "hansard_1901",
  "provider": "ANTHROPIC",
  "model": "claude-sonnet-4-20250514",
  "search_k": 20,
  "citation_limit": 10,
  "set_as_default": true
}
```

Response:
```json
{
  "success": true,
  "target_name": "hansard_claude4",
  "file_path": "backend/targets/hansard_claude4.conf",
  "env_updated": true
}
```

## Complete Wizard Workflow

### ADDED: End-to-End Flow

The complete corpus wizard workflow:

1. **Step 1: Upload Documents**
   - User uploads document files
   - System analyzes directory structure

2. **Step 2: Select Embedding Model**
   - User chooses between default model (all-mpnet-base-v2) or custom
   - If custom: User enters HuggingFace model ID
   - System validates model exists and compatibility
   - System configures vector store settings

3. **Step 3: Select Filters**
   - System analyzes folder structure
   - User selects exactly 2 folder levels as filter_1 and filter_2
   - Optional: Enable filename metadata extraction

4. **Step 4: Build Corpus**
   - System creates vector store in create/output/chroma_db/
   - System generates BM25 corpus in create/output/bm25_corpus.jsonl
   - System creates manifest in create/output/manifest.json
   - System generates retriever from template → create/output/{corpus_name}_retriever.py

5. **Step 5: Create Test Target**
   - User selects LLM provider and model
   - User configures search parameters
   - System creates .conf file in create/output/{corpus_name}_{model}.conf

6. **Step 6: Activate Corpus**
   - System shows what files will be moved/overwritten
   - User confirms activation
   - System moves:
     - create/output/chroma_db/ → backend/targets/chroma_db/
     - create/output/bm25_corpus.jsonl → backend/targets/bm25_corpus.jsonl
     - create/output/manifest.json → backend/targets/manifest.json
     - create/output/{corpus_name}_retriever.py → backend/retrievers/
     - create/output/*.conf → backend/targets/ (preserving existing .conf files)
   - System updates RETRIEVER_MODULE in .env to {corpus_name}_retriever
   - System updates TEST_TARGET in .env to active test target

## Acceptance Criteria

1. System allows selection of exactly 2 folder levels as filters
2. filter_1 and filter_2 are correctly stored in vector store
3. Auto-generated retriever supports queries using filter_1, filter_2, or both
4. Optional enrichment patterns work for parliamentary dates
5. UI displays maximum 2 filter dropdowns
6. NO backward compatibility with legacy configurations
7. Enrichment metadata appears in search result citations
8. System handles corpora with <2 folder levels gracefully
9. Wizard creates valid .conf test target files
10. System loads .conf files correctly (no .txt support)
11. TEST_TARGET in .env is updated automatically
12. Wizard generates corpus-specific retriever from template
13. RETRIEVER_MODULE in .env is updated to point to generated retriever
14. System works from clean default state (no pre-existing corpus)
15. Corpus activation preserves existing test target configurations
16. Generated retriever includes proper 2-filter handling logic
17. Embedding model selection is simple: default or custom with validation
18. Custom embedding models are validated against HuggingFace
19. Selected embedding model is fully documented in manifest.json
20. No brittle auto-recommendation of embedding models