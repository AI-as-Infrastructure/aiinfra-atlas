# Proposal: Refactor and Implement UI-Driven Corpus Configuration Wizard

## Change ID
`refactor-corpus-wizard`

## Summary
Implement a UI-driven corpus configuration wizard that enables users to configure and swap between different corpora within ATLAS's supported structural patterns. The wizard guides users through organizing their corpus into one of four supported patterns (single-layer directories, two-layer directories, flat XML, or flat text with metadata), ensuring reliable processing and consistent citation generation.

## Motivation

Currently, swapping corpora in ATLAS requires:
1. Manually reorganizing source files to match hardcoded patterns (AU/NZ/UK)
2. Editing Python scripts to change corpus IDs
3. Running multiple make commands with specific environment variables
4. Manually copying generated files to correct locations
5. No support for non-Hansard corpora without code modifications
6. No tracking of corpus metadata (copyright, DOI, provenance)

The corpus wizard solves these problems by:
- Providing a guided UI for corpus configuration
- Supporting arbitrary corpus structures (not just parliamentary records)
- Auto-discovering filters from both structure and user metadata
- Providing a default embedding model with custom HuggingFace options
- Supporting GitHub repos as corpus sources
- Tracking academic metadata (copyright status, DOI)
- Enabling single-command corpus swapping

## Scope

### In Scope
- Corpus wizard mode (separate from normal operation)
- Metadata collection UI (time period, entities, organization preferences)
- Support for local directories and GitHub repositories as sources
- Copyright and DOI metadata tracking
- Intelligent filter discovery combining user metadata and structure analysis
- Default embedding model with custom HuggingFace model support
- Config-driven corpus generation (replacing hardcoded patterns)
- Progress tracking and validation during vector store creation
- Atomic corpus swapping with backup
- Support for both TXT and XML corpora

### Out of Scope
- Agent-based search (separate change process)
- PDF or CSV corpus support (future enhancement)
- Multi-corpus simultaneous search
- Zero-downtime corpus swapping
- Automatic corpus updates from GitHub
- MCP server implementation

## Current State Analysis

### Recent Directory Restructuring
The codebase has undergone significant restructuring:
- **Removed**: The `create/` directory and all Hansard-specific files
- **New structure**:
  - `backend/corpus/` - Active corpus data (chroma_db, manifest.json, bm25_corpus.jsonl)
  - `backend/corpus/sources/` - Source documents for corpus building
  - `backend/corpus/tmp/` - Temporary workspace for corpus building
  - `backend/targets/` - Test target configurations (LLM settings)
  - `config/corpus.yaml` - Main corpus configuration
  - `utils/scripts/` - All operational scripts including `prepare_model.py`

### Hardcoded Assumptions
The previous corpus creation pipeline (removed from `create/` directory) had:
- Hardcoded region mapping: `{"au": "1901_au", "nz": "1901_nz", "uk": "1901_uk"}`
- Fixed directory patterns: `/AU/`, `/NZ/`, `/UK/`
- Hardcoded test query: `"parliament"`
- No metadata tracking (copyright, DOI, provenance)
- No support for alternative embedding models per corpus

### Missing Capabilities
- No UI for corpus configuration
- No GitHub repository support
- No metadata-driven filter discovery
- No embedding model recommendations
- No progress tracking during build
- Manual file copying required after generation

### Existing Foundation
The codebase already includes:
- `backend/routers/corpus_wizard.py` - Basic corpus wizard router with activation endpoint
- `backend/modules/corpus_builder.py` - Corpus building functionality (needs config-driven refactoring)
- `backend/modules/build_progress.py` - Progress tracking infrastructure
- New directory structure supporting corpus/sources, corpus/tmp, and corpus data separation

### Environment Variable Cleanup
The current .env files contain corpus-specific variables that will become redundant with the wizard:

#### Variables to be Deprecated/Moved to corpus.yaml:
```bash
# These will move to corpus configuration YAML files
RETRIEVER_MODULE=hansard_retriever  # → Corpus-specific, managed by wizard
MULTI_CORPUS_METADATA="1901_au,1901_nz,1901_uk"  # → Dynamic from manifest.json
EMBEDDING_MODEL=Livingwithmachines/bert_1890_1900  # → Per-corpus setting
POOLING=mean+max  # → Per-corpus embedding setting
CHUNK_SIZE=1000  # → Per-corpus chunking strategy
CHUNK_OVERLAP=100  # → Per-corpus chunking strategy
TEXT_SPLITTER_TYPE=RecursiveCharacterTextSplitter  # → Per-corpus setting
CHROMA_COLLECTION_NAME="blert_1000"  # → Corpus-specific collection
HANSARD_SOURCES_ROOT=/path/to/sources  # → Replaced by corpus/sources/

# Frontend/branding variables move to corpus.yaml
VITE_SITE_TITLE="ATLAS Hansard"  # → corpus.yaml: display_name

# Telemetry naming becomes dynamic
PHOENIX_PROJECT_NAME=Hansard-Dev  # → Dynamic: "{corpus_name}-{env}"
```

#### New Wizard-Related Variables:
```bash
# Corpus wizard mode control
CORPUS_WIZARD_MODE=false  # Enable/disable wizard mode
CORPUS_CONFIG_PATH=config/corpus.yaml  # Active corpus configuration
CORPUS_BACKUP_DIR=backend/corpus.backup  # Backup location for swaps

# Build process configuration (system-wide defaults)
BUILD_CPU_THREADS=4  # CPU threads for corpus building
BUILD_GPU_ENABLED=auto  # auto|true|false - GPU usage for builds
BUILD_MEMORY_LIMIT_GB=8  # Memory limit for build process
```

#### Variables that Remain:
- All authentication settings (Cognito, API keys)
- Redis configuration
- Test target settings (TEST_TARGET)
- Telemetry settings (base configuration)
- Rate limiting and worker configuration
- WebSocket configuration
- ATLAS_VERSION (core ATLAS application version, e.g., "0.2.3")
- LAST_MODIFIED (application code update date)

### Build-Time Configuration Generation

The `config/generate_vue_files.sh` script will be enhanced to merge corpus-specific settings from `corpus.yaml` with environment variables at build time:

```bash
#!/bin/bash
# Enhanced generate_vue_files.sh

# Load corpus configuration if exists
if [ -f "config/corpus.yaml" ]; then
    # Extract corpus display name and version
    CORPUS_NAME=$(yq eval '.metadata.display_name // "ATLAS"' config/corpus.yaml)
    CORPUS_VERSION=$(yq eval '.metadata.version // "0.0.0"' config/corpus.yaml)
else
    # Fallback to generic values
    CORPUS_NAME="ATLAS"
    CORPUS_VERSION="0.0.0"
fi

# Generate VITE_SITE_TITLE dynamically
echo "VITE_SITE_TITLE=\"$CORPUS_NAME\"" >> frontend/.env

# Generate dynamic telemetry project name
export PHOENIX_PROJECT_NAME="${CORPUS_NAME}-${ENVIRONMENT}"
```

This ensures that:
1. Frontend gets corpus-specific branding at build time
2. No manual .env editing needed when switching corpora
3. Telemetry automatically uses corpus-appropriate naming
4. Single source of truth in corpus.yaml

### Corpus Swap Deployment Flow

When a user activates a new corpus through the wizard:
1. **Backup current corpus**: Move `backend/corpus/` to timestamped backup
2. **Install new corpus**: Move built corpus from `backend/corpus/tmp/` to `backend/corpus/`
3. **Update configuration**: Replace `config/corpus.yaml` with new corpus config
4. **Regenerate frontend config**: Run enhanced `generate_vue_files.sh` to update `frontend/.env`
5. **Rebuild frontend**: `npm run build` in frontend directory with new VITE_SITE_TITLE
6. **Restart services**: Reload backend and frontend to use new corpus

This automated flow ensures consistency across all components without manual intervention.

## Supported Corpus Structures

ATLAS is designed to support common academic and research corpus patterns. While flexible, the system implements specific structural patterns for practical and performance reasons:

### Supported Patterns

1. **Single-Layer Directory Structure** (e.g., Hansard)
   - One level of categorization folders (countries, topics, years)
   - Multiple documents within each folder
   - Best for: Parliamentary records, news archives, correspondence collections

2. **Two-Layer Directory Structure** (e.g., Literary collections)
   - Two levels of categorization (genre/author, period/topic)
   - Documents organized hierarchically
   - Best for: Literature collections, academic papers, mixed-type archives

3. **Flat XML Collection** (e.g., Darwin Correspondence)
   - Single directory of XML files
   - Metadata extracted from XML structure
   - Best for: Digital editions, TEI-encoded texts, structured datasets

4. **Flat Text Collection with Metadata in Filenames**
   - Single directory with descriptive filenames
   - Metadata extracted via regex patterns
   - Best for: Simple document collections, converted archives

### Structural Constraints

**What ATLAS requires:**
- Consistent file naming within a corpus
- UTF-8 encoded text files (TXT) or well-formed XML
- Directory names that can serve as meaningful filters
- Files under 50MB each (larger files should be pre-split)

**What ATLAS does NOT support:**
- Deeply nested structures (>2 directory levels)
- Binary formats (PDF, DOCX) without pre-conversion
- Mixed encodings within a corpus
- Database exports or CSV files as primary sources
- Dynamically generated content

### File Naming Conventions

For optimal metadata extraction, follow these patterns:
- **Literary works**: `Author_FirstName_Title_Year.txt`
- **Correspondence**: `Date_From_To_Subject.txt`
- **Parliamentary**: `Date_Location_Session.txt`
- **Academic**: `Author_Year_Title_Journal.txt`

These constraints ensure reliable processing, consistent citation generation, and predictable search behavior across different corpus types.

## Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────┐
│                 Frontend (Vue 3)                 │
├─────────────────────────────────────────────────┤
│              Corpus Wizard UI                    │
│  • Metadata Collection                          │
│  • Source Selection (Local/GitHub)              │
│  • Filter Configuration                         │
│  • Model Selection                              │
│  • Progress Tracking                            │
└────────────┬────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────┐
│         Backend API (FastAPI)                   │
├─────────────────────────────────────────────────┤
│       /api/corpus-wizard/*                      │
│  • analyze-corpus                               │
│  • suggest-filters                              │
│  • recommend-model                              │
│  • build-vector-store                           │
│  • swap-corpus                                  │
└────────────┬────────────────────────────────────┘
             │
┌────────────▼────────────────────────────────────┐
│     Corpus Configuration Engine                 │
├─────────────────────────────────────────────────┤
│  • Metadata-driven analysis                     │
│  • GitHub repo cloning                          │
│  • Filter inference                             │
│  • Model matching                               │
│  • Config generation (YAML)                     │
└─────────────────────────────────────────────────┘
```

### Wizard Flow

#### Step 1: Metadata Collection
```yaml
corpus_metadata:
  name: "Parliamentary Hansard 1901"
  description: "Parliamentary debates from Australia, New Zealand, and United Kingdom"
  time_period:
    from: 1901
    to: 1901
  material_type: "parliamentary_records"

  # Citation metadata - used in UI when displaying sources
  citation_template:
    format: "{title}, {date}, {location}"  # Template for citation display
    base_url: "https://hansard.parliament.uk/historic/{date}/{id}"  # URL pattern
    source_name: "Historic Hansard"  # Source attribution
    repository: "Parliamentary Archives"  # Repository/archive name

  # Additional metadata for citations
  document_metadata:
    title_pattern: "regex: ^([^,]+)"  # Extract title from filename
    date_format: "ISO-8601"  # Expected date format in documents
    id_pattern: "regex: _(\\d+)\\."  # Extract document ID for URLs
    location_field: "directory_name"  # Use directory as location (e.g., "Australia")

  entities:
    people: ["Edmund Barton", "Richard Seddon", "Arthur Balfour"]
    places: ["Sydney", "Wellington", "London"]
    topics: ["federation", "trade", "empire", "parliament"]
  organization_preferences:
    - by_country
    - by_date
    - by_topic
  copyright:
    status: "public_domain"
    statement: "Parliamentary records are in the public domain"
  doi: "10.5281/zenodo.7654321"  # Optional
  citation: "Parliamentary Hansard Records, 1901"  # Default citation text
```

#### Step 2: Source Selection
```yaml
source_config:
  type: "local"
  location: "backend/corpus/sources/"
  # OR for GitHub:
  # type: "github"
  # location: "https://github.com/AI-as-Infrastructure/aiinfra-atlas-hansard"
  # branch: "main"
  # path: "corpus/"  # Path within repo
```

#### Step 3: Corpus Structure Selection
Users select from supported structural patterns:

```yaml
corpus_structure:
  pattern: "single_layer_directory"  # Guided selection from 4 supported patterns
  # Options:
  # - single_layer_directory (e.g., Hansard: Country folders)
  # - two_layer_directory (e.g., Gutenberg: Genre/Work structure)
  # - flat_xml_collection (e.g., Darwin: XML letters in single folder)
  # - flat_text_metadata (e.g., Simple corpus with metadata in filenames)

filter_method:
  type: "directory_structure"  # Automatically set based on pattern

  # For directory_structure type:
  directory_options:
    depth: 1  # or 2 (number of folder layers to use as filters)
    layer_1_name: "Country"  # e.g., Australia, New Zealand, UK
    layer_2_name: "Year"  # (only if depth=2) e.g., 1901, 1902

  # Extract metadata from filenames
  filename_metadata:
    enabled: true
    patterns:
      - date: "regex: (\\d{4}-\\d{2}-\\d{2})"  # Extract date
      - author: "regex: ^([^_]+)_"  # Extract author before underscore
      - session: "regex: _session_(\\d+)"  # Extract session number

  # For xml_structure type:
  xml_options:
    use_directories: true  # Still use first layer directories as filters
    entities:
      people: "//person/@name"  # XPath to extract people
      dates: "//date/@value"  # XPath to extract dates
      titles: "//title/text()"  # XPath to extract titles
    date_range_generation: true  # Auto-generate year/decade ranges from dates
```

#### Filter Generation Examples:

**Directory Structure (1 layer):**
```
sources/
├── Australia/
│   ├── Friday, 02 August, 1901.txt
│   └── Monday, 09 December, 1901.txt
├── New Zealand/
│   └── Tuesday, 16 July, 1901.txt
└── United Kingdom/
    └── Thursday, 28th February, 1901.txt

Generates filters:
- "Australia" (all files in Australia/)
- "New Zealand" (all files in New Zealand/)
- "United Kingdom" (all files in United Kingdom/)
```

**Directory Structure (2 layers):**
```
sources/
├── Fiction/
│   ├── 1800-1850/
│   │   └── pride_prejudice.txt
│   └── 1851-1900/
│       └── oliver_twist.txt
└── Non-Fiction/
    ├── 1800-1850/
    │   └── origin_species.txt
    └── 1851-1900/
        └── capital_marx.txt

Generates filters:
- "Fiction" (all Fiction files)
- "Non-Fiction" (all Non-Fiction files)
- "Fiction: 1800-1850"
- "Fiction: 1851-1900"
- "Non-Fiction: 1800-1850"
- "Non-Fiction: 1851-1900"
```

**XML Structure (Darwin Correspondence):**
```xml
<!-- in sources/Darwin/DCP-LETT-1.xml -->
<TEI xml:id="DCP-LETT-1">
  <teiHeader>
    <titleStmt>
      <title>From Mary Congreve 27 October [1821]</title>
    </titleStmt>
  </teiHeader>
  <text>...</text>
</TEI>

Generates filters:
- "Mary Congreve" (from person entity)
- "1821" (from date)
- "1820-1830" (auto-generated decade range)
```

**Literary Corpus (2 layers - Gutenberg example):**
```
sources/
├── Fiction/
│   ├── Trollope_Anthony_The_Warden_1855.txt
│   ├── Trollope_Anthony_Barchester_Towers_1857.txt
│   └── Dickens_Charles_Oliver_Twist_1838.txt
└── Non-Fiction/
    ├── Trollope_Anthony_North_America_1862.txt
    └── Darwin_Charles_Origin_Species_1859.txt

Generates filters:
- "Fiction" (all fiction works)
- "Non-Fiction" (all non-fiction works)
- Plus author/date metadata from filenames
```

#### Step 4: Validation with Sample Subset

Before processing the full corpus, the system performs a validation pass with a minimal viable sample:

```yaml
validation_config:
  sample_size: "auto"  # or specific number/percentage
  sampling_strategy: "representative"  # Ensures samples from each filter/category

  # Auto-sampling targets
  auto_sample_rules:
    min_documents: 10  # Minimum documents to sample
    max_documents: 50  # Maximum for quick processing
    per_filter_min: 2  # At least 2 docs from each filter category
    percentage: 5  # Or 5% of corpus, whichever is smaller

# Sample selection for different patterns
sample_selection:
  single_layer:
    # For Hansard: 2-3 documents from each country
    - "Australia/Friday, 02 August, 1901.txt"
    - "New Zealand/Tuesday, 16 July, 1901.txt"
    - "United Kingdom/1-Friday, 15th March, 1901.txt"

  two_layer:
    # For Gutenberg: 1 work from each genre (first chapter only)
    - "Fiction/Trollope_Anthony_The_Warden_1855.txt" (first 10000 chars)
    - "Non-Fiction/Darwin_Charles_Origin_Species_1859.txt" (first 10000 chars)

  flat_xml:
    # For Darwin: Random sample of letters
    - Random 10 XML files

# Validation outputs for user review
validation_results:
  filters_discovered:
    - name: "Australia"
      document_count: 2
      sample_citation: "Friday, 02 August, 1901, Sydney Parliament"

  metadata_extracted:
    - document: "The_Warden_1855.txt"
      author: "Anthony Trollope"
      title: "The Warden"
      year: "1855"
      citation_preview: "Trollope, Anthony. The Warden (1855), Chapter 1"

  issues_detected:
    - type: "inconsistent_naming"
      files: ["Tuesday, 8th October, 1501.txt"]  # Year typo
      suggestion: "Check date format consistency"

    - type: "missing_metadata"
      files: ["Unknown_Author_Title.txt"]
      suggestion: "Add author/date to filename"

  processing_estimates:
    sample_processing_time: "45 seconds"
    estimated_full_corpus_time: "~15 minutes"
    chunks_per_document_avg: 12
    total_estimated_chunks: 14400
```

The user can then:
1. **Review discovered filters** - Confirm they match expectations
2. **Check citation previews** - Ensure formatting is correct
3. **Fix detected issues** - Rename files, adjust patterns
4. **Adjust configuration** - Modify extraction patterns if needed
5. **Proceed or iterate** - Run another validation or proceed to full build

#### Step 5: Model Selection
```python
def get_model_options():
    # Provide default model and allow custom selection
    return {
        'default': {
            'model_id': 'sentence-transformers/all-MiniLM-L6-v2',
            'description': 'General-purpose model suitable for most corpora',
            'performance': 'Fast processing with good accuracy',
            'size_mb': 90,
            'dimensions': 384
        },
        'custom_option': True,
        'custom_help': 'Enter any HuggingFace sentence-transformers model ID'
    }

def validate_custom_model(model_id):
    # Validate HuggingFace model exists and is compatible
    try:
        from sentence_transformers import SentenceTransformer
        # Attempt to load model metadata
        model = SentenceTransformer(model_id, cache_folder='.cache')
        return {
            'valid': True,
            'dimensions': model.get_sentence_embedding_dimension(),
            'max_seq_length': model.max_seq_length
        }
    except Exception as e:
        return {'valid': False, 'error': str(e)}
```

### Configuration Output

The wizard generates a comprehensive corpus configuration:

```yaml
# config/corpus.yaml
metadata:
  name: "Parliamentary Hansard 1901"
  display_name: "ATLAS Hansard"  # Used for VITE_SITE_TITLE
  version: "1.0.0"  # Corpus version
  created: "2024-01-20T10:30:00Z"
  created_by: "corpus_wizard_v1"
  time_period:
    from: 1901
    to: 1901
  copyright:
    status: "public_domain"
    statement: "Parliamentary records are in the public domain"
  doi: "10.5281/zenodo.7654321"
  default_citation: "Parliamentary Hansard Records, 1901"

# Citation configuration for UI display
citation_config:
  template: "{title}, {date}, {location}"
  base_url: "https://hansard.parliament.uk/historic/{date}/{id}"
  source_name: "Historic Hansard"
  repository: "Parliamentary Archives"
  extraction_patterns:
    title: "regex: ^([^,]+)"
    date: "regex: ([A-Za-z]+, \\d{1,2}[a-z]{0,2} [A-Za-z]+, \\d{4})"
    id: "regex: _(\\d+)\\."
    location: "from_directory"  # Extract from parent directory name

source:
  type: "local"
  location: "backend/corpus/sources/"
  file_types: ["txt"]

filter_method:
  type: "directory_structure"
  depth: 1
  layer_1_name: "Country"
  filename_metadata:
    enabled: true
    patterns:
      - date: "regex: ([A-Za-z]+, \\d{1,2}[a-z]{0,2} [A-Za-z]+, \\d{4})"

filters:
  - id: "australia"
    label: "Australia"
    type: "directory"
    path: "Australia/"
    document_count: 1456
  - id: "new_zealand"
    label: "New Zealand"
    type: "directory"
    path: "New Zealand/"
    document_count: 892
  - id: "united_kingdom"
    label: "United Kingdom"
    type: "directory"
    path: "United Kingdom/"
    document_count: 2341

embeddings:
  model: "Livingwithmachines/bert_1890_1900"
  pooling: "mean"
  chunk_size: 1000
  chunk_overlap: 100

vector_store:
  type: "chromadb"
  collection_name: "hansard_1901"
  persist_directory: "backend/corpus/chroma_db"

search:
  type: "hybrid"
  k_default: 10
  test_query: "parliament federation"
```

### Parent-Source Association During Chunking

For corpora with large documents (novels, long letters, parliamentary sessions), maintaining the parent-source relationship is critical:

```python
class ChunkProcessor:
    """Ensures chunks maintain parent document association"""

    def process_document(self, file_path: str, content: str, config: Dict) -> List[Dict]:
        """Process a document into chunks with parent metadata"""

        # Extract parent document metadata
        parent_metadata = self.extract_parent_metadata(file_path)

        # For large documents like novels, add source-level metadata
        if self.is_large_document(content):
            parent_metadata['doc_type'] = 'full_work'
            parent_metadata['total_length'] = len(content)
            parent_metadata['work_title'] = self.extract_title(file_path)
            parent_metadata['author'] = self.extract_author(file_path)

        # Create chunks with parent reference
        chunks = []
        chunk_texts = self.text_splitter.split_text(content)

        for i, chunk_text in enumerate(chunk_texts):
            chunk = {
                'text': chunk_text,
                'metadata': {
                    **parent_metadata,  # Include all parent metadata
                    'chunk_index': i,
                    'total_chunks': len(chunk_texts),
                    'source_file': os.path.basename(file_path),
                    'source_path': file_path,
                    'parent_id': self.generate_doc_id(file_path),
                    # Maintain filter associations
                    'filter_1': os.path.basename(os.path.dirname(file_path)),  # e.g., "Fiction"
                    'filter_2': os.path.basename(os.path.dirname(os.path.dirname(file_path)))  # if 2-layer
                }
            }

            # For literary works, add chapter/section context if detectable
            if 'Chapter' in chunk_text[:100] or 'CHAPTER' in chunk_text[:100]:
                chapter_match = re.search(r'Chapter\s+(\d+|[IVXLC]+)', chunk_text[:100], re.I)
                if chapter_match:
                    chunk['metadata']['chapter'] = chapter_match.group(1)

            chunks.append(chunk)

        return chunks

    def extract_title(self, file_path: str) -> str:
        """Extract title from filename pattern like 'Author_Name_Title_Year.txt'"""
        filename = os.path.basename(file_path).replace('.txt', '')
        parts = filename.split('_')
        # Assuming pattern: Author_FirstName_Title_Words_Year
        if len(parts) >= 4:
            return ' '.join(parts[2:-1])  # Title is everything between author and year
        return filename

    def extract_author(self, file_path: str) -> str:
        """Extract author from filename pattern"""
        filename = os.path.basename(file_path)
        parts = filename.split('_')
        if len(parts) >= 2:
            return f"{parts[1]} {parts[0]}"  # "FirstName LastName"
        return ""
```

This ensures:
1. **Every chunk knows its parent document** - Essential for novels, long letters
2. **Chunks inherit all parent metadata** - Author, title, date, etc.
3. **Chunk position is tracked** - Know where in the document each chunk comes from
4. **Filter associations maintained** - Chunks correctly associated with directory-based filters

### Citation Metadata Implementation

The citation metadata collected during the wizard will be embedded in each chunk during vector store creation and used to generate rich citations in the UI:

```python
class CitationEnricher:
    """Enriches document chunks with citation metadata"""

    def __init__(self, citation_config: Dict):
        self.config = citation_config
        self.template = citation_config['template']
        self.base_url = citation_config.get('base_url', '')
        self.patterns = citation_config.get('extraction_patterns', {})

    def enrich_chunk(self, chunk: Dict, file_path: str) -> Dict:
        """Add citation metadata to a document chunk"""

        # Extract metadata using configured patterns
        metadata = {}
        filename = os.path.basename(file_path)
        directory = os.path.basename(os.path.dirname(file_path))

        # Extract title
        if 'title' in self.patterns:
            match = re.search(self.patterns['title'], filename)
            metadata['title'] = match.group(1) if match else filename

        # Extract date
        if 'date' in self.patterns:
            match = re.search(self.patterns['date'], filename)
            metadata['date'] = match.group(1) if match else ''

        # Extract ID for URL generation
        if 'id' in self.patterns:
            match = re.search(self.patterns['id'], filename)
            metadata['doc_id'] = match.group(1) if match else ''

        # Use directory as location if specified
        if self.patterns.get('location') == 'from_directory':
            metadata['location'] = directory

        # Generate URL if base_url provided
        if self.base_url and metadata.get('doc_id'):
            metadata['url'] = self.base_url.format(
                date=metadata.get('date', ''),
                id=metadata.get('doc_id', ''),
                location=metadata.get('location', '')
            )

        # Generate citation text using template
        metadata['citation_text'] = self.template.format(**metadata)

        # Add source attribution
        metadata['source_name'] = self.config.get('source_name', '')
        metadata['repository'] = self.config.get('repository', '')

        # Merge with chunk metadata
        chunk['metadata'] = {**chunk.get('metadata', {}), **metadata}
        return chunk
```

This ensures every chunk has rich citation metadata that can be displayed in the UI, making sources transparent and verifiable for researchers.

### Corpus Swap Implementation

```python
# backend/modules/corpus_wizard.py
class CorpusWizard:
    """Orchestrates corpus configuration and swapping"""

    async def enable_wizard_mode(self):
        """Switch application to wizard mode"""
        os.environ["CORPUS_WIZARD_MODE"] = "true"
        # Disable normal query endpoints
        # Enable wizard UI at /corpus-wizard

    async def fetch_github_corpus(self, repo_url: str, branch: str = "main"):
        """Clone or download corpus from GitHub"""
        temp_dir = Path(tempfile.mkdtemp())

        if repo_url.endswith(".git"):
            # Clone with sparse checkout for corpus only
            subprocess.run([
                "git", "clone", "--depth=1",
                f"--branch={branch}",
                "--filter=blob:none",
                "--sparse",
                repo_url, temp_dir
            ])
        else:
            # Download via GitHub API
            await self.download_github_archive(repo_url, branch, temp_dir)

        return temp_dir

    async def build_corpus(self, config: Dict, progress_callback):
        """Build vector store with progress tracking"""
        builder = CorpusBuilder(config)

        # Fetch source if GitHub
        if config['source']['type'] == 'github':
            source_path = await self.fetch_github_corpus(
                config['source']['location'],
                config['source'].get('branch', 'main')
            )
        else:
            source_path = config['source']['location']

        # Build with progress
        async for progress in builder.build_async(source_path):
            await progress_callback(progress)

    async def swap_corpus(self, new_corpus_path: str):
        """Atomically swap to new corpus"""
        backup_dir = f"backend/corpus.backup.{int(time.time())}"

        # Backup current
        shutil.move("backend/corpus", backup_dir)

        # Install new
        shutil.move(new_corpus_path, "backend/corpus")

        # Clear caches
        manifest_loader.invalidate_cache()

        # Exit wizard mode and restart
        os.environ["CORPUS_WIZARD_MODE"] = "false"
        await self.restart_server()
```

### Enhanced Build Progress and Requirements

#### System Requirements Check
Before building, the system analyzes hardware capabilities and provides estimates:

```python
class SystemRequirements:
    """Check system capabilities and estimate build time"""

    def analyze_system(self):
        return {
            'cpu': {
                'cores': psutil.cpu_count(),
                'model': platform.processor(),
                'available': True
            },
            'gpu': {
                'available': torch.cuda.is_available(),
                'name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                'memory': torch.cuda.get_device_properties(0).total_memory if torch.cuda.is_available() else 0
            },
            'memory': {
                'total': psutil.virtual_memory().total,
                'available': psutil.virtual_memory().available,
                'required': self.estimate_memory_requirement()
            },
            'disk': {
                'free': shutil.disk_usage('/').free,
                'required': self.estimate_disk_requirement()
            }
        }

    def estimate_build_time(self, doc_count, mode='cpu'):
        """Estimate build time based on document count and processing mode"""
        if mode == 'gpu':
            docs_per_second = 4.0  # Based on benchmarks
        else:
            docs_per_second = 1.2  # CPU is ~3x slower

        estimated_seconds = doc_count / docs_per_second
        return {
            'seconds': estimated_seconds,
            'formatted': self.format_duration(estimated_seconds),
            'confidence': 0.75  # 75% confidence in estimate
        }
```

#### Real-Time Progress Tracking
Detailed progress with multiple metrics:

```python
class BuildProgressTracker:
    """Track and report detailed build progress"""

    def __init__(self, total_docs, websocket=None):
        self.total_docs = total_docs
        self.processed_docs = 0
        self.start_time = time.time()
        self.websocket = websocket
        self.metrics = {
            'current_doc': None,
            'current_chunk': 0,
            'total_chunks': 0,
            'docs_per_second': 0,
            'memory_usage': 0,
            'gpu_usage': 0,
            'errors': 0,
            'warnings': 0
        }

    async def update_progress(self, doc_path, chunk_num=None):
        """Send detailed progress update"""
        self.processed_docs += 1
        elapsed = time.time() - self.start_time

        progress_data = {
            'percentage': (self.processed_docs / self.total_docs) * 100,
            'processed': self.processed_docs,
            'total': self.total_docs,
            'current_document': doc_path,
            'current_chunk': chunk_num,
            'elapsed_seconds': elapsed,
            'estimated_remaining': self.estimate_remaining_time(),
            'docs_per_second': self.processed_docs / elapsed if elapsed > 0 else 0,
            'memory': {
                'ram_used_gb': psutil.Process().memory_info().rss / 1e9,
                'ram_percent': psutil.virtual_memory().percent,
                'gpu_used_gb': self.get_gpu_memory() if torch.cuda.is_available() else 0,
                'gpu_percent': self.get_gpu_usage() if torch.cuda.is_available() else 0
            },
            'performance': {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'disk_io_mb': self.get_disk_io()
            },
            'filter_progress': self.get_filter_progress()
        }

        if self.websocket:
            await self.websocket.send_json(progress_data)

        return progress_data

    def get_filter_progress(self):
        """Track progress per corpus filter"""
        # Returns progress for each filter
        # e.g., {"1901_au": {"processed": 450, "total": 1456}}
```

### Frontend Wizard UI

```vue
<!-- frontend/src/components/CorpusWizard.vue -->
<template>
  <div class="corpus-wizard">
    <WizardSteps :current="currentStep" :steps="wizardSteps" />

    <!-- Step 1: Metadata -->
    <div v-if="currentStep === 1" class="wizard-step">
      <h2>Tell us about your corpus</h2>
      <CorpusMetadataForm
        v-model="metadata"
        @continue="analyzeCorpus"
      />
    </div>

    <!-- Step 2: Source Selection -->
    <div v-if="currentStep === 2" class="wizard-step">
      <h2>Where is your corpus located?</h2>
      <SourceSelector
        v-model="source"
        :suggestions="sourceSuggestions"
        @continue="discoverFilters"
      />
    </div>

    <!-- Step 3: Filter Definition Method -->
    <div v-if="currentStep === 3" class="wizard-step">
      <h2>Choose Filter Definition Method</h2>
      <FilterMethodSelector
        v-model="filterMethod"
        :corpus-type="source.fileTypes"
        @continue="configureFilters"
      />
      <!-- Shows dropdown with:
        - Directory Structure (1 or 2 layers)
        - XML Structure (with entity extraction)
        Plus configuration options based on selection -->
    </div>

    <!-- Step 4: Filter Configuration -->
    <div v-if="currentStep === 4" class="wizard-step">
      <h2>Configure Search Filters</h2>
      <FilterConfigurator
        v-model="filters"
        :method="filterMethod"
        :discovered="discoveredFilters"
        :metadata="metadata"
        @continue="selectModel"
      />
    </div>

    <!-- Step 5: Validation Preview -->
    <div v-if="currentStep === 5" class="wizard-step">
      <h2>Validate Configuration with Sample</h2>
      <ValidationPreview
        :sample-config="validationConfig"
        :validation-results="validationResults"
        :issues="detectedIssues"
        @fix-issues="returnToConfiguration"
        @adjust-patterns="adjustExtractionPatterns"
        @continue="selectModel"
      />
      <!-- Shows:
        - Sample documents being processed
        - Discovered filters with counts
        - Citation format previews
        - Detected issues with suggestions
        - Time estimates for full processing
      -->
    </div>

    <!-- Step 6: Model Selection -->
    <div v-if="currentStep === 6" class="wizard-step">
      <h2>Select Embedding Model</h2>
      <ModelSelector
        v-model="embeddingModel"
        :recommendations="modelRecommendations"
        :corpus-sample="corpusSample"
        @continue="checkRequirements"
      />
    </div>

    <!-- Step 7: Requirements Check -->
    <div v-if="currentStep === 7" class="wizard-step">
      <h2>System Requirements Check</h2>
      <RequirementsChecker
        :corpus-stats="corpusStats"
        :system-info="systemInfo"
        @select-mode="selectProcessingMode"
      />
    </div>

    <!-- Step 7: Build Progress -->
    <div v-if="currentStep === 7" class="wizard-step">
      <h2>Building Vector Store</h2>
      <BuildProgress
        :progress="buildProgress"
        :logs="buildLogs"
        :mode="processingMode"
        :detailed-metrics="detailedMetrics"
        @pause="pauseBuild"
        @resume="resumeBuild"
        @complete="testCorpus"
      />
    </div>

    <!-- Step 8: Test & Activate -->
    <div v-if="currentStep === 8" class="wizard-step">
      <h2>Test & Activate Corpus</h2>
      <CorpusTester
        :config="finalConfig"
        :test-results="testResults"
        @activate="activateCorpus"
        @save-only="saveConfiguration"
      />
    </div>
  </div>
</template>
```

### API Endpoints

```python
# backend/routers/corpus_wizard.py
@router.post("/api/corpus-wizard/analyze")
async def analyze_corpus(
    source_type: str,
    source_location: str,
    metadata: CorpusMetadata
):
    """Analyze corpus structure and suggest configuration"""

@router.post("/api/corpus-wizard/suggest-filters")
async def suggest_filters(
    metadata: CorpusMetadata,
    structure_analysis: Dict
):
    """Suggest filters based on metadata and structure"""

@router.post("/api/corpus-wizard/recommend-model")
async def recommend_model(
    metadata: CorpusMetadata
):
    """Recommend embedding models for corpus"""

@router.post("/api/corpus-wizard/build")
async def build_corpus(
    background_tasks: BackgroundTasks,
    config: CorpusConfig
):
    """Build vector store in background"""

@router.get("/api/corpus-wizard/progress/{build_id}")
async def get_build_progress(build_id: str):
    """SSE endpoint for build progress"""

@router.post("/api/corpus-wizard/activate")
async def activate_corpus(
    corpus_id: str,
    backup: bool = True
):
    """Swap to new corpus and restart"""
```

## Benefits

1. **Guided Structure**: Users are guided to organize corpora into proven patterns that work reliably
2. **Predictable Behavior**: Limited structural patterns ensure consistent processing and searching
3. **Clear Boundaries**: Explicit constraints prevent configuration errors and processing failures
4. **Accessibility**: Non-technical users can configure corpora through UI within clear guidelines
5. **Quality Assurance**: Structural constraints ensure proper citation generation and filter discovery
6. **Optimization**: Default embedding model with option for custom HuggingFace models
7. **Provenance**: Tracking of copyright and DOI information for academic rigor
8. **Portability**: Corpus configurations can be shared between ATLAS instances
9. **Cleaner Configuration**: Removes corpus-specific settings from environment files
10. **Academic Focus**: Constraints are designed specifically for humanities and social science research needs

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub API rate limits | Medium | Low | Cache repos locally, support direct downloads |
| Large corpus build time | High | Medium | Progress tracking, ability to resume |
| Incorrect filter discovery | Medium | Medium | User validation and editing step |
| Model mismatch | Low | High | Test with corpus samples before commit |
| Swap failure | Low | High | Automatic backup, rollback capability |
| Wizard mode lock | Low | Medium | Admin override to exit wizard mode |

## Testing Strategy

1. **Unit tests**: Filter discovery, model recommendation logic
2. **Integration tests**: GitHub fetching, corpus building
3. **E2E tests**: Full wizard flow with test corpora
4. **Performance tests**: Large corpus handling
5. **Validation**: Hansard ↔ Darwin swapping as primary test case

## Dependencies

- Builds on `add-dynamic-corpus-filters` change (manifest loading)
- No breaking changes to existing corpus generation
- Compatible with current vector store structure

## Documentation Requirements

The implementation will include comprehensive documentation updates:
- User guide for the corpus wizard with screenshots and examples
- Developer documentation for the configuration schema and APIs
- Migration guide from hardcoded patterns to config-driven approach
- Updates to all affected existing documentation files
- Example configurations for common corpus types (Hansard, Darwin, etc.)

## Example Configurations

### Gutenberg Literary Corpus (2-layer structure)
```yaml
# config/corpus.yaml for Trollope collection
metadata:
  name: "Anthony Trollope Complete Works"
  display_name: "ATLAS Trollope"
  version: "1.0.0"
  time_period:
    from: 1847
    to: 1883

citation_config:
  template: "{author}, {title} ({year}), Chapter {chapter}"
  base_url: "https://www.gutenberg.org/ebooks/{gutenberg_id}"
  source_name: "Project Gutenberg"
  extraction_patterns:
    author: "regex: ^([^_]+_[^_]+)"  # "Trollope_Anthony"
    title: "regex: _([^_]+(?:_[^_]+)*?)_\\d{4}"  # Title between author and year
    year: "regex: (\\d{4})\\."
    gutenberg_id: "from_metadata"  # Would need to be added during processing

filter_method:
  type: "directory_structure"
  depth: 2
  layer_1_name: "Genre"  # Fiction, Non-Fiction
  layer_2_name: "Work"   # Individual novels/books
  filename_metadata:
    enabled: true
    patterns:
      - author: "regex: ^([^_]+)_([^_]+)"
      - title: "regex: _([^_]+(?:_[^_]+)*?)_\\d{4}"
      - year: "regex: (\\d{4})"

# Chunking configuration critical for novels
chunking:
  strategy: "preserve_chapters"  # Special handling for literary works
  chunk_size: 2000  # Larger chunks for narrative coherence
  chunk_overlap: 200
  parent_tracking: true  # Ensure all chunks know their parent work
  detect_chapters: true  # Try to identify chapter boundaries
```

This configuration ensures that when a user searches for themes in Trollope's work, each chunk returned will properly cite the specific novel and chapter it comes from.

## Acceptance Criteria

- [ ] Wizard mode can be enabled/disabled via make command
- [ ] Metadata collection includes copyright and DOI fields
- [ ] GitHub repositories can be used as corpus sources
- [ ] Filters are discovered from metadata + structure
- [ ] Default embedding model is provided with custom HuggingFace option
- [ ] Progress is tracked during vector store build
- [ ] Corpus swap is atomic with automatic backup
- [ ] Test case: Successfully swap between Hansard and Darwin corpora
- [ ] Configuration files are portable and shareable
- [ ] Wizard can be exited without applying changes
- [ ] All documentation is updated to reflect new corpus wizard functionality