# Corpus Configuration Wizard

The ATLAS Corpus Configuration Wizard provides a user-friendly interface for configuring and swapping between different text corpora used for RAG (Retrieval Augmented Generation).

## Overview

The corpus wizard allows:
- Configuration of new corpora from local directories or GitHub repositories
- Dynamic filter generation based on corpus structure
- Embedding model selection with period-specific defaults
- Real-time build progress tracking
- Atomic corpus swapping with automatic backup
- **Isolated environment** that doesn't interfere with main development

## Key Design Principles

### 1. Automatic GPU Detection & Configuration
- **Zero-configuration GPU support** - `make b` detects your GPU and installs appropriate PyTorch
- **Broad GPU compatibility** - Supports all NVIDIA generations (GTX 10xx through RTX 50xx)
- **Smart PyTorch selection** - Automatically chooses CUDA 11.8, 12.1, or 12.4+ based on your GPU
- **Graceful fallback** - Falls back to CPU if GPU initialization fails
- **Transparent operation** - UI shows actual mode (GPU/CPU) after any fallback
- **Single unified environment** - Everything runs from main `.venv`

### 2. Simplified Workflow
- **Just `make b` and `make f`** - No special setup commands needed
- **GPU-accelerated when available** - Automatically uses GPU for 5-10x faster corpus building
- **Works without GPU** - Seamlessly falls back to CPU if no GPU detected

## Quick Start

### Initial Setup

Simply start the backend and frontend servers:

```bash
# Terminal 1: Start backend (GPU auto-detected and configured)
make b

# Terminal 2: Start frontend
make f

# Navigate to corpus wizard
# Open http://localhost:5173/corpus-wizard
```

The backend startup script will automatically:
1. **Detect your GPU** using `nvidia-smi`
2. **Identify compute capability** (e.g., 6.1, 8.6, 12.0)
3. **Select appropriate PyTorch:**
   - CUDA 11.8 for older GPUs (GTX 10xx, RTX 20xx/30xx)
   - CUDA 12.1 for RTX 40xx series
   - CUDA 12.4+ nightly for RTX 50xx series
4. **Install and configure** PyTorch with GPU support (~2GB) or CPU-only (~200MB)
5. **Test GPU functionality** and fall back to CPU if initialization fails
6. **Log detailed info** about GPU detection and mode selection

See [GPU Compatibility Guide](gpu_compatibility.md) for complete details.

### Quick Corpus Swapping
```bash
# Backup current corpus
make corpus-backup

# Restore from most recent backup
make corpus-restore

# List available corpus configurations
make corpus-list
```

### Production Deployment

The corpus wizard deploys with the main application:

```bash
# On production server
make p  # Deploy production (includes corpus wizard)
```

### Dependencies

The corpus wizard requires the following additional dependency:
- `gitpython==3.1.41` - For GitHub corpus integration

This is included in `config/requirements.txt` and will be installed automatically.

## Usage

### Web Interface

Navigate to `/corpus-wizard` in your browser to access the wizard interface.

### Command Line

#### Complete Command Reference

**Corpus Operations:**
```bash
# List available corpus configurations
make corpus-list

# Backup current corpus
make corpus-backup

# Restore from most recent backup
make corpus-restore
```

#### Environment Structure

```
aiinfra-atlas/
├── .venv/              # Main environment (backend, frontend, corpus building)
├── corpus_configs/     # Saved corpus configurations
├── corpus_backups/     # Automatic backups
└── backend/
    ├── corpus/         # Active corpus
    │   └── tmp/        # Temporary corpus builds
    └── targets/        # Active corpus vector store
```

## Architecture

### Backend Components

- `backend/modules/corpus_config.py` - Configuration models and validation
- `backend/modules/corpus_analyzer.py` - Corpus structure analysis
- `backend/modules/github_corpus.py` - GitHub repository integration
- `backend/modules/corpus_requirements.py` - System requirements checking
- `backend/routers/corpus_wizard.py` - API endpoints
- `create/create_corpus_store.py` - Universal corpus builder

### Frontend Components

- `frontend/src/pages/CorpusWizardComplete.vue` - Main wizard interface
- `frontend/src/components/wizard/` - Wizard step components

### Configuration Storage

Corpus configurations are stored as YAML files in:
- `corpus_configs/` - Saved corpus configurations
- `corpus_backups/` - Automatic backups of previous corpora

## Directory Structure Handling

### Recursive File Discovery

The corpus wizard automatically discovers files in **any directory structure** using recursive glob patterns. It will find all files of the specified type(s) regardless of how deeply nested they are.

**How it works:**
- Uses `**/*.{file_type}` pattern to recursively search all subdirectories
- Analyzes directory hierarchy to understand organization
- Suggests filters based on discovered structure
- Works with flat, nested, or mixed directory layouts

### Supported Directory Organizations

The wizard supports any directory structure and automatically adapts:

#### 1. Hierarchical with Meaningful Names (Recommended)
```
backend/corpus/sources/
├── Australia/
│   └── House_of_Representatives/
│       └── 1901/
│           ├── Wednesday_19_June_1901.txt
│           └── Thursday_20_June_1901.txt
├── New_Zealand/
│   └── House_of_Representatives/
│       └── 1901/
│           ├── Monday_1_July_1901.txt
│           └── Tuesday_2_July_1901.txt
└── United_Kingdom/
    └── House_of_Commons/
        └── 1901/
            ├── Wednesday_23_January_1901.txt
            └── Friday_15_February_1901.txt
```
**Benefits:**
- **Folder names become filter labels directly** - no guessing or expansion
- Creates filters: "Australia", "New_Zealand", "United_Kingdom"
- Clear, self-documenting structure
- Users control exact filter names through folder naming

**Important:** Name your folders as you want them to appear as filters!

#### 2. Temporal Organization
```
darwin_letters/
├── 1850s/
│   ├── 1850/
│   ├── 1859/
│   └── ...
└── 1860s/
    ├── 1860/
    └── ...
```
**Benefits:**
- Wizard detects year/decade patterns
- Suggests temporal filters automatically
- Good for chronological research

#### 3. Flat Structure
```
corpus/
├── document001.txt
├── document002.txt
└── ...
```
**Benefits:**
- Simple to set up
- Works fine for single-collection corpora
- Less specific filter suggestions (mainly "all")

#### 4. Mixed/Custom
```
project/
├── primary_sources/
│   ├── manuscripts/
│   └── letters/
└── secondary_sources/
    └── publications/
```
**Benefits:**
- Flexible organization
- Wizard adapts to whatever structure exists
- You can manually adjust suggested filters

### Example: Current Hansard Structure (Suboptimal)

The default ATLAS corpus currently uses abbreviated folder names:

```
backend/corpus/sources/
├── au/hofreps/txt/     # Australia House of Representatives
├── nz/hofreps/txt/     # New Zealand House of Representatives
└── uk/hofcoms/txt/     # United Kingdom House of Commons
```

**Wizard behavior:**
1. Points to `backend/corpus/sources/` directory
2. Discovers 206 .txt files across all subdirectories
3. Creates filters using **exact folder names**:
   - "au" → `backend/corpus/sources/au/**/*.txt`
   - "nz" → `backend/corpus/sources/nz/**/*.txt`
   - "uk" → `backend/corpus/sources/uk/**/*.txt`
   - "All Documents" → `backend/corpus/sources/**/*.txt` (always included)

**Better approach:** Rename folders to be meaningful:
```
backend/corpus/sources/
├── Australia/
├── New_Zealand/
└── United_Kingdom/
```

## Corpus Configuration Format

### Complete Example: Hansard Parliamentary Records (1901)

```yaml
metadata:
  name: "Hansard Parliamentary Records 1901"
  description: "Parliamentary debates from Australia, New Zealand, and United Kingdom (1901)"
  time_period_from: 1901
  time_period_to: 1901
  material_type: "parliamentary"
  people: ["Winston Churchill", "Edmund Barton", "Richard Seddon"]
  topics: ["empire", "federation", "trade", "defense"]
  copyright_status: "public_domain"
  copyright_statement: "Parliamentary records are Crown Copyright but available under open license"
  doi: "10.5281/zenodo.example"
  citation: "Hansard Parliamentary Debates, 1901. Retrieved from ATLAS corpus."

source:
  type: "local"
  location: "/path/to/aiinfra-atlas/backend/corpus/sources"
  file_types: ["txt"]

filters:
  - id: "australia"
    label: "Australia"
    pattern: "au/**/*.txt"
  - id: "new_zealand"
    label: "New Zealand"
    pattern: "nz/**/*.txt"
  - id: "united_kingdom"
    label: "United Kingdom"
    pattern: "uk/**/*.txt"
  - id: "all"
    label: "All Hansard"
    pattern: "**/*.txt"

embeddings:
  model: "Livingwithmachines/bert_1890_1900"
  pooling: "mean"
  chunk_size: 1000
  chunk_overlap: 100
  batch_size: 100

vector_store:
  type: "chromadb"
  collection_name: "hansard_1901"
  persist_directory: "backend/targets/chroma_db"

search:
  type: "hybrid"
  k_default: 10
  large_single_corpus: 120
  large_all_corpus: 80
```

### Alternative Example: Darwin Correspondence

```yaml
metadata:
  name: "Darwin Correspondence Project"
  description: "Complete letters of Charles Darwin"
  time_period_from: 1825
  time_period_to: 1882
  material_type: "personal_correspondence"
  people: ["Charles Darwin", "Thomas Huxley", "Joseph Hooker"]
  topics: ["evolution", "natural selection", "geology", "botany"]
  copyright_status: "mixed"

source:
  type: "github"
  location: "https://github.com/cambridge-collection/darwin-correspondence-data"
  branch: "main"
  path: "letters/"
  file_types: ["xml", "txt"]

filters:
  - id: "1850s"
    label: "1850s"
    pattern: "**/185*/**/*.xml"
  - id: "1860s"
    label: "1860s (Origin period)"
    pattern: "**/186*/**/*.xml"
  - id: "early_letters"
    label: "Early Letters (1825-1850)"
    pattern: "**/{1825..1850}/**/*.xml"

embeddings:
  model: "Livingwithmachines/bert_1760_1900"
  pooling: "mean"
  chunk_size: 1000
  chunk_overlap: 100

vector_store:
  type: "chromadb"
  collection_name: "darwin_letters"

search:
  type: "hybrid"
  k_default: 10
```

## Filter Discovery Algorithm

### Overview

The corpus wizard uses a **hybrid discovery approach** that combines three sources of information to automatically suggest filters:

1. **Directory structure** (highest priority) - Your folder names ARE your filters
2. **User metadata hints** (medium priority) - Only used if few folders exist
3. **Content analysis** (lowest priority) - Fallback for flat structures

### Discovery Process

The filter discovery runs in sequence:

```
Directory Structure Analysis (FIRST)
    ↓
[If <3 folders] → User Metadata Hints
    ↓
[If <5 filters] → Content Sampling (up to 100 files)
    ↓
Filter Synthesis & Ranking
    ↓
Suggested Filters (editable)
```

### Key Principle: Folder Names = Filter Names

**The wizard uses folder names EXACTLY as they are.** This gives you complete control:
- Folder `Australia/` → Filter "Australia"
- Folder `au/` → Filter "au" (NOT expanded)
- Folder `Darwin_Letters/` → Filter "Darwin_Letters"

**Best Practice:** Name your folders as you want them to appear in the filter list!

### 1. Directory Structure (Highest Priority)

Top-level folders automatically become filters with confidence 0.95.

**How it works:**
- **Every top-level folder becomes a filter**
- **Folder name = Filter label** (exact match, no expansion)
- **Pattern:** `folder_name/**/*` (all files in that folder and subfolders)
- **Confidence:** 0.95 (very high - explicit user organization)

**Examples:**
```
backend/corpus/sources/
├── Australia/      → Filter: "Australia"
├── New_Zealand/    → Filter: "New_Zealand"
├── UK/            → Filter: "UK"
└── US/            → Filter: "US"
```

**Note:** Abbreviations like "au", "nz", "uk" will NOT be expanded. Name folders meaningfully!

### 2. User Metadata Hints (Medium Priority)

Only used if directory structure has fewer than 3 folders.

#### Time Period Filters

If you provide `time_period_from` and `time_period_to`:

**Large span (>50 years)** → Decade filters:
```yaml
# Input: 1825-1882
# Output:
- id: "1820s"
  label: "1820s"
  pattern: "**/182*/**/*"
- id: "1830s"
  label: "1830s"
  pattern: "**/183*/**/*"
```

**Medium span (10-50 years)** → Year filters:
```yaml
# Input: 1898-1902
# Output:
- id: "1898"
  label: "1898"
  pattern: "**/1898/**/*"
- id: "1899"
  label: "1899"
  pattern: "**/1899/**/*"
```

#### People Filters

If you provide `people: ["Charles Darwin", "Joseph Hooker"]`:

```yaml
# Output:
- id: "charles_darwin"
  label: "Charles Darwin"
  pattern: "**/Charles*Darwin/**/*"
  type: "entity"
  subtype: "person"
  confidence: 0.9
```

#### Topic Filters

If you provide `topics: ["evolution", "natural selection"]`:

```yaml
# Output:
- id: "evolution"
  label: "Evolution"
  pattern: "**/*evolution*/**/*"
  type: "thematic"
  confidence: 0.7
```

### 3. Content Analysis (Lowest Priority)

Only used when directory structure provides fewer than 5 filters. The analyzer samples **up to 100 files** to discover metadata patterns.

#### XML File Analysis

Scans XML files for:
- **Element tags**: Counts frequency of all XML elements
- **Metadata fields**: `<author>`, `<date>`, `<subject>`, `<title>`, `<recipient>`, `<location>`
- **Date formats**: Extracts date patterns for temporal filtering

**Example XML filter generation:**
```xml
<!-- If many files contain: -->
<author>Charles Darwin</author>
<recipient>Joseph Hooker</recipient>

<!-- Generated filters: -->
- id: "author_charles_darwin"
  label: "Author: Charles Darwin"
  type: "metadata"
  xpath: "//author[contains(., 'Charles Darwin')]"
  confidence: 0.75
```

#### Text File Analysis

Scans text files for:
- **Header patterns**: `Author: Charles Darwin\nDate: 1850-01-15`
- **Date formats**: ISO dates, various formats
- **Structured metadata**: Key-value pairs at file start

### Filter Synthesis & Ranking

After collecting all signals, filters are:

1. **Deduplicated** - Same ID only appears once
2. **Ordered by priority**:
   - "All Documents" filter (always first)
   - Metadata hint filters (confidence 0.8-0.9)
   - Structure filters (confidence 0.85)
   - Content filters (confidence 0.75)
3. **Limited** - Top 5 examples per pattern type
4. **Presented** - User can edit, add, or remove

### Confidence Scores

Filters include confidence scores indicating reliability:

| Source | Confidence | Meaning |
|--------|-----------|---------|
| All filter | 1.0 | Always matches everything |
| User metadata (people) | 0.9 | User knows their corpus |
| User metadata (time) | 0.8 | Directory might use dates |
| Structure patterns | 0.85 | Clear organizational pattern |
| Content (XML) | 0.75 | Found in sample files |
| User metadata (topics) | 0.7 | Might be in filenames |

### User Editing

After discovery, you can:

- ✏️ **Edit labels** - Change display names
- ❌ **Remove filters** - Delete unhelpful suggestions
- ➕ **Add custom filters** - Create your own patterns
- 🎯 **Adjust patterns** - Refine glob patterns

### Best Practices for Filter Discovery

1. **Provide rich metadata** - More hints = better filters
2. **Organize hierarchically** - Clear structure improves detection
3. **Use consistent naming** - Patterns easier to detect
4. **Review suggestions** - Always check/edit generated filters
5. **Test patterns** - Wizard will show estimated document counts

### Example: Full Discovery Process

**Input:**
```yaml
metadata:
  name: "Hansard 1901"
  time_period_from: 1901
  time_period_to: 1901
  people: ["Winston Churchill", "Edmund Barton"]

source:
  location: "backend/corpus/sources/"
  file_types: ["txt"]
```

**Directory structure:**
```
backend/corpus/sources/
├── au/hofreps/txt/  (70 files)
├── nz/hofreps/txt/  (68 files)
└── uk/hofcoms/txt/  (68 files)
```

**Discovered filters:**
```yaml
# 1. Always included
- id: "all"
  label: "All Documents"
  confidence: 1.0

# 2. From structure (geographical)
- id: "au"
  label: "Australia"
  pattern: "**/au/**/*"
  confidence: 0.85
  source: "structure"

- id: "nz"
  label: "New Zealand"
  pattern: "**/nz/**/*"
  confidence: 0.85
  source: "structure"

- id: "uk"
  label: "United Kingdom"
  pattern: "**/uk/**/*"
  confidence: 0.85
  source: "structure"

# 3. From metadata hints (people) - if directories exist
- id: "winston_churchill"
  label: "Winston Churchill"
  pattern: "**/Winston*Churchill/**/*"
  confidence: 0.9
  source: "metadata_hint"
```

## System Requirements

The corpus wizard automatically checks system requirements before building:
- Python 3.10+
- Sufficient disk space (varies by corpus size)
- CPU or GPU support for embeddings
- Git (for GitHub sources)
- Internet connection (for downloading models/repos)

## Progress Tracking

The build process provides real-time progress via Server-Sent Events:
- Document processing progress
- Filter generation progress
- Embedding generation progress
- Vector store creation progress
- Detailed logging of all operations

## Security Considerations

- GitHub tokens are handled securely (never stored in configs)
- Corpus configurations are validated before building
- Automatic backups prevent data loss
- Atomic swapping ensures consistency

## Troubleshooting

### Common Issues

1. **Build fails with memory error**
   - Use smaller batch sizes in embeddings config
   - Switch to CPU mode if GPU memory is limited

2. **GitHub repository not accessible**
   - Check repository is public or provide access token
   - Verify branch and path exist

3. **Corpus swap fails**
   - Check disk space for backup
   - Ensure no processes are using the corpus

## Best Practices

1. **Test configurations locally first** before deploying to production
2. **Use descriptive filter IDs** for better user experience
3. **Include complete metadata** for research reproducibility
4. **Regular backups** are created automatically but can be triggered manually
5. **Monitor disk usage** as corpora and backups can be large

## Future Enhancements

- Support for additional source types (S3, Azure, etc.)
- Incremental corpus updates
- Multi-corpus search capabilities
- Corpus versioning and rollback
- Automated corpus quality assessment