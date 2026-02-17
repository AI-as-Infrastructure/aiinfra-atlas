# Simplify Corpus Wizard to 2-Filter System with Test Target Configuration

## Change Summary

Simplify the corpus wizard to support exactly 2 top-level filters (matching UI constraints), add optional filename metadata extraction for enrichment, and create test target configuration files (.conf) to replace the legacy .txt format.

## Problem Statement

Currently, the corpus wizard:
- Creates unlimited filters from directory structure (UI can only display 2)
- Uses a single "corpus" field for filtering (limiting for multi-dimensional data)
- Does NOT extract metadata from filenames (missing context for users)
- Has a mismatch between filter creation and UI display capabilities
- Doesn't create test targets, requiring manual configuration
- Uses inappropriate .txt extension for configuration files

Example: The Hansard corpus has:
- Directory structure: `data/au/house_of_reps/1901/*.txt` (creates 3+ filters)
- Filenames like: `Friday, 02 August, 1901.txt` (metadata ignored)
- UI constraint: Can only display 2 filter dropdowns
- Test targets: Must be manually created in backend/targets/
- Result: Incomplete setup requiring manual intervention

## Proposed Solution

Complete the wizard with a practical 2-filter system, enrichment, and test targets:

1. **Limit to 2 top-level filters from directory structure**
   - filter_1: First meaningful folder level (e.g., country)
   - filter_2: Second meaningful folder level (e.g., parliament)
   - Stored in vector store metadata for filtering

2. **Optional filename metadata extraction (enrichment only)**
   - Extract dates, names, etc. from filenames
   - Store as additional metadata fields
   - Display in citations for context
   - NOT used for filtering (keeps system simple)

3. **Update retriever to support 2-filter queries**
   - Support filter_1 only queries
   - Support filter_1 AND filter_2 combined queries
   - Maintain backward compatibility with single "corpus" field

4. **Create test target .conf files in wizard**
   - Replace legacy .txt format with proper .conf (INI format)
   - Move all test config from .env to .conf files
   - Auto-generate target file and update TEST_TARGET in .env
   - Provide model name guidance for each provider

## Success Criteria

- [ ] Wizard allows selection of exactly 2 folder levels as filters
- [ ] filter_1 and filter_2 are stored in vector store metadata
- [ ] Retriever supports filtering by filter_1, filter_2, or both
- [ ] Optional filename metadata extraction works with common patterns
- [ ] Enrichment metadata appears in search result citations
- [ ] System maintains backward compatibility with existing corpora
- [ ] UI displays exactly 2 filter dropdowns when available
- [ ] Wizard creates test target .conf files
- [ ] System loads .conf files instead of .txt files
- [ ] Test configuration moved from .env to .conf files

## Implementation Approach

### 1. Simplified Filter Selection (Step 3: "Select Filters")

Modify existing filter step to limit selection:
- Display folder structure analysis
- Allow selection of up to 2 folder levels as filters
- Show preview of filter values from selected levels
- Optional: Enable filename metadata extraction

### 2. Test Target Configuration (Step 6: "Create Test Target")

Add new final wizard step:
- Select LLM provider and input model name
- Configure search parameters (search_k, citation_limit)
- Generate .conf file in INI format
- Update TEST_TARGET in .env automatically

### 3. Configuration Formats

#### Corpus Configuration (YAML)
```yaml
filters:
  # Exactly 2 filters from directory structure
  - id: "filter_1"
    label: "Country"
    source_level: 0  # First folder level
    values: ["au", "nz", "uk"]
  - id: "filter_2"
    label: "Parliament"
    source_level: 1  # Second folder level
    values: ["house_of_reps", "senate"]

# Optional enrichment metadata (not for filtering)
metadata_extraction:
  enabled: false  # User can enable if desired
  filename_pattern: "hansard_date"  # Pre-defined pattern template
  extracted_fields:
    - day_of_week
    - day
    - month
    - year
```

#### Test Target Configuration (.conf)
```ini
# backend/targets/hansard_claude4.conf
[metadata]
name = Hansard Claude-4 Configuration
corpus = hansard_1901
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

### 4. UI Components

#### Simplified Filter Selection Interface
```
┌─────────────────────────────────────────────────────────┐
│ Step 3: Select Filters (Maximum 2)                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Detected folder structure:                             │
│ data/                                                   │
│ ├── au/           (3 folders)                          │
│ │   ├── house_of_reps/                                 │
│ │   └── senate/                                       │
│ ├── nz/           (1 folder)                           │
│ └── uk/           (1 folder)                           │
│                                                         │
│ Select up to 2 levels as filters:                      │
│                                                         │
│ ☑ Level 1: [Country        ▼] → au, nz, uk            │
│ ☑ Level 2: [Parliament     ▼] → house_of_reps, senate │
│ ☐ Level 3: (Year - 124 values, too many for filter)   │
│                                                         │
│ Optional Enrichment:                                   │
│ ☐ Extract metadata from filenames                      │
│    Pattern detected: "Friday, 02 August, 1901.txt"     │
│    Would extract: day_of_week, day, month, year        │
│                                                         │
│ [Continue] [Skip Enrichment]                           │
└─────────────────────────────────────────────────────────┘
```

#### Test Target Creation Interface
```
┌─────────────────────────────────────────────────────────┐
│ Step 6: Create Test Target (Optional)                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│ Configure your search and LLM settings:                │
│                                                         │
│ LLM Provider:  [Anthropic       ▼]                     │
│                OpenAI                                   │
│                Google                                   │
│                Bedrock                                  │
│                                                         │
│ Model Name:    [claude-sonnet-4-20250514___________]   │
│ (Paste exact model string from provider docs)          │
│                                                         │
│ Common Models:                                         │
│ • Anthropic: claude-sonnet-4-20250514                  │
│ • OpenAI: gpt-4o, gpt-4-turbo                         │
│ • Google: gemini-2.0-flash                            │
│                                                         │
│ Search Settings:                                       │
│ Search K:        [20] (documents sent to LLM)          │
│ Citation Limit:  [10] (max citations displayed)        │
│                                                         │
│ Target Name: hansard_claude4.conf                      │
│                                                         │
│ ☑ Create test target file                              │
│ ☑ Set as default TEST_TARGET in .env                   │
│                                                         │
│ [Complete Setup] [Skip]                                │
└─────────────────────────────────────────────────────────┘
```

### 5. Backend Changes

#### create_corpus_store.py
```python
def _apply_filters(self, documents: List[Document]) -> List[Document]:
    """Apply 2-filter system to documents."""
    for doc in documents:
        doc_path = Path(doc.metadata.get("source", ""))
        parts = doc_path.parts

        # Extract filter values from path
        if len(parts) > 1:
            doc.metadata["filter_1"] = parts[1]  # e.g., "au"
        if len(parts) > 2:
            doc.metadata["filter_2"] = parts[2]  # e.g., "house_of_reps"

        # Optional: Extract enrichment metadata from filename
        if config.metadata_extraction.enabled:
            metadata = extract_filename_metadata(doc_path.name)
            doc.metadata.update(metadata)  # Adds day_of_week, month, etc.
```

#### hansard_retriever.py
```python
def invoke(self, query: str, config: Optional[Dict] = None, k: int = 10):
    """Handle 2-filter queries."""
    filter_dict = {}

    # Build filter dict from filter_1 and filter_2
    if config:
        if config.get("filter_1") and config["filter_1"] != "all":
            filter_dict["filter_1"] = config["filter_1"]
        if config.get("filter_2") and config["filter_2"] != "all":
            filter_dict["filter_2"] = config["filter_2"]

        # Backward compatibility with single corpus filter
        if config.get("corpus_filter"):
            filter_dict["corpus"] = config["corpus_filter"]

    # Perform search with combined filters
    return self.vector_store.similarity_search(query=query, k=k, filter=filter_dict)
```

#### config.py
```python
def _load_target_config(_config, target_id):
    """Load target configuration from .conf file (replacing .txt)."""
    import configparser

    # Path to target config file - now using .conf extension
    target_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'targets', f"{target_id}.conf"
    )

    if not os.path.isfile(target_file):
        logger.warning(f"Target config {target_file} not found")
        return

    # Parse INI-style .conf file
    parser = configparser.ConfigParser()
    parser.read(target_file)

    # Load LLM configuration
    if 'llm' in parser:
        _config['llm_config']['provider'] = parser.get('llm', 'provider')
        _config['llm_config']['model'] = parser.get('llm', 'model')

    # Load retrieval configuration
    if 'retrieval' in parser:
        for key in ['search_k', 'citation_limit', 'search_score_threshold',
                    'large_retrieval_single_corpus', 'large_retrieval_all_corpus']:
            if parser.has_option('retrieval', key):
                value = parser.get('retrieval', key)
                # Convert numeric values
                if key in ['search_k', 'citation_limit', 'large_retrieval_single_corpus',
                          'large_retrieval_all_corpus']:
                    value = int(value)
                elif key == 'search_score_threshold':
                    value = float(value)
                _config['retriever_config'][key] = value
```

## Benefits

1. **Practical**: Matches UI capability (exactly 2 filters)
2. **Simple**: No complex pattern matching required
3. **Flexible**: Works with any directory structure
4. **Enriched**: Optional metadata provides context in citations
5. **Backwards compatible**: Existing corpora continue to work
6. **Complete workflow**: Wizard handles corpus to test target creation
7. **Cleaner configuration**: Test settings in .conf, environment in .env
8. **Shareable**: Test targets can be shared without exposing API keys

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Limited to 2 filters | Covers most use cases; complex needs use enrichment metadata |
| Breaking change for existing corpora | Maintain backward compatibility with "corpus" field |
| Filename patterns might not match | Make extraction optional, provide templates |
| Filter naming confusion | Auto-suggest sensible names based on content |
| Breaking change from .txt to .conf | Clean cutover, no dual support needed |
| Users entering wrong model names | Provide common examples, validation in UI |

## Alternative Approaches Considered

1. **Unlimited filters**: UI can't display them all
2. **Complex pattern matching**: Too difficult for users
3. **Filename-based filtering**: Too slow for large corpora
4. **Single filter only**: Not flexible enough for multi-dimensional data

## Dependencies

- No new Python packages required
- Uses Python's built-in `re` module for optional patterns
- Frontend modifications to existing components only

## Testing Strategy

1. Unit tests for 2-filter extraction
2. Integration tests with existing and new corpora
3. UI tests for filter selection
4. Backward compatibility tests
5. Performance tests with combined filters

## Documentation Requirements

- User guide for 2-filter system
- Migration guide for existing corpora
- Optional enrichment patterns documentation
- API documentation for filter_1/filter_2 fields

## Open Questions

1. Should filter names be auto-detected or user-defined?
2. How to handle corpora with < 2 folder levels?
3. Should enrichment metadata be searchable (full-text)?
4. What filename patterns to include as templates?

## Timeline Estimate

- Design: 1 day (simpler approach)
- 2-filter implementation: 2 days
- Test target .conf implementation: 2 days
- Testing: 1 day
- Documentation: 1 day
- **Total: 7 days**