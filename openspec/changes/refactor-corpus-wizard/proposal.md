# Proposal: Refactor and Implement UI-Driven Corpus Configuration Wizard

## Change ID
`refactor-corpus-wizard`

## Summary
Implement a UI-driven corpus configuration wizard that enables users to swap between different corpora without manual code changes, supporting both local and GitHub-hosted sources, with intelligent filter discovery and embedding model recommendations based on user-provided metadata.

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
- Recommending appropriate embedding models based on time period
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
- Embedding model recommendations based on corpus characteristics
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
  citation: "Parliamentary Hansard Records, 1901"
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

#### Step 3: Filter Discovery
Combines metadata with structural analysis:
```python
def discover_filters(metadata, source_structure):
    filters = []

    # Time-based filters from metadata
    if metadata.time_period:
        filters.extend(generate_temporal_filters(
            metadata.time_period.from,
            metadata.time_period.to
        ))

    # Entity-based filters from metadata + content
    if metadata.entities.people:
        filters.extend(find_person_filters(
            source_structure,
            expected_people=metadata.entities.people
        ))

    # Structure-based filters
    filters.extend(analyze_directory_patterns(source_structure))

    return filters
```

#### Step 4: Model Recommendation
```python
def recommend_embedding_model(metadata):
    period = metadata.time_period
    material = metadata.material_type

    recommendations = []

    # Historical models for period texts
    if 1760 <= period.from <= 1900:
        recommendations.append({
            'model': 'Livingwithmachines/bert_1760_1900',
            'score': 0.95,
            'reason': 'Optimized for this historical period'
        })

    # Always include general fallback
    recommendations.append({
        'model': 'sentence-transformers/all-MiniLM-L6-v2',
        'score': 0.7,
        'reason': 'General purpose, fast, reliable'
    })

    return recommendations
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
  citation: "Parliamentary Hansard Records, 1901"

source:
  type: "local"
  location: "backend/corpus/sources/"
  file_types: ["txt"]

filters:
  - id: "1901_au"
    label: "Australia 1901"
    pattern: "**/AU/**/*"
    document_count: 1456
  - id: "1901_nz"
    label: "New Zealand 1901"
    pattern: "**/NZ/**/*"
    metadata_field: "country"
    document_count: 892
  - id: "1901_uk"
    label: "United Kingdom 1901"
    pattern: "**/UK/**/*"
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

    <!-- Step 3: Filter Configuration -->
    <div v-if="currentStep === 3" class="wizard-step">
      <h2>Configure Search Filters</h2>
      <FilterConfigurator
        v-model="filters"
        :discovered="discoveredFilters"
        :metadata="metadata"
        @continue="selectModel"
      />
    </div>

    <!-- Step 4: Model Selection -->
    <div v-if="currentStep === 4" class="wizard-step">
      <h2>Select Embedding Model</h2>
      <ModelSelector
        v-model="embeddingModel"
        :recommendations="modelRecommendations"
        :corpus-sample="corpusSample"
        @continue="checkRequirements"
      />
    </div>

    <!-- Step 5: Requirements Check -->
    <div v-if="currentStep === 5" class="wizard-step">
      <h2>System Requirements Check</h2>
      <RequirementsChecker
        :corpus-stats="corpusStats"
        :system-info="systemInfo"
        @select-mode="selectProcessingMode"
      />
    </div>

    <!-- Step 6: Build Progress -->
    <div v-if="currentStep === 6" class="wizard-step">
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

    <!-- Step 7: Test & Activate -->
    <div v-if="currentStep === 7" class="wizard-step">
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

1. **Accessibility**: Non-technical users can configure corpora through UI
2. **Flexibility**: Support for any corpus structure, not just Hansard
3. **Discoverability**: Intelligent filter suggestions based on metadata
4. **Optimization**: Appropriate embedding models for each corpus
5. **Provenance**: Tracking of copyright and DOI information
6. **Portability**: GitHub support enables sharing corpus configurations
7. **Reliability**: Atomic swapping with automatic backup
8. **Cleaner Configuration**: Removes corpus-specific settings from environment files, making deployment simpler
9. **Dynamic Branding**: ATLAS automatically adapts its title and telemetry based on active corpus
10. **Reduced Complexity**: Single source of truth for corpus configuration in corpus.yaml

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

## Acceptance Criteria

- [ ] Wizard mode can be enabled/disabled via make command
- [ ] Metadata collection includes copyright and DOI fields
- [ ] GitHub repositories can be used as corpus sources
- [ ] Filters are discovered from metadata + structure
- [ ] Embedding models are recommended based on time period
- [ ] Progress is tracked during vector store build
- [ ] Corpus swap is atomic with automatic backup
- [ ] Test case: Successfully swap between Hansard and Darwin corpora
- [ ] Configuration files are portable and shareable
- [ ] Wizard can be exited without applying changes
- [ ] All documentation is updated to reflect new corpus wizard functionality