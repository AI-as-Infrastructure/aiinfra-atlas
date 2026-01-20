# Proposal: Add UI-Driven Corpus Configuration Wizard

## Change ID
`add-corpus-wizard`

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

### Hardcoded Assumptions
The current corpus creation pipeline (`create/txt/create_hansard_store.py`) has:
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
  name: "Darwin Correspondence Project"
  description: "Letters and papers of Charles Darwin"
  time_period:
    from: 1825
    to: 1882
  material_type: "personal_correspondence"
  entities:
    people: ["Charles Darwin", "Thomas Huxley", "Alfred Wallace"]
    places: ["London", "Cambridge", "Down House"]
    topics: ["evolution", "natural selection", "biology"]
  organization_preferences:
    - by_time_period
    - by_person
    - by_topic
  copyright:
    status: "public_domain"
    statement: "Original letters public domain, transcriptions CC-BY 4.0"
  doi: "10.5281/zenodo.1234567"  # Optional
  citation: "Darwin Correspondence Project, University of Cambridge"
```

#### Step 2: Source Selection
```yaml
source_config:
  type: "github"  # or "local"
  location: "https://github.com/AI-as-Infrastructure/aiinfra-atlas-darwin"
  branch: "main"
  path: "corpus/"  # Path within repo
  # OR for local:
  # type: "local"
  # location: "/data/darwin_correspondence/"
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
# corpus_configs/darwin_correspondence.yaml
metadata:
  name: "Darwin Correspondence Project"
  created: "2024-01-20T10:30:00Z"
  created_by: "corpus_wizard_v1"
  time_period:
    from: 1825
    to: 1882
  copyright:
    status: "public_domain"
    statement: "Original letters public domain, transcriptions CC-BY 4.0"
  doi: "10.5281/zenodo.1234567"
  citation: "Darwin Correspondence Project, University of Cambridge"

source:
  type: "github"
  location: "https://github.com/AI-as-Infrastructure/aiinfra-atlas-darwin"
  branch: "main"
  path: "corpus/"
  file_types: ["xml", "txt"]

filters:
  - id: "1820s"
    label: "1820s"
    pattern: "**/182[0-9]/**/*"
    document_count: 45
  - id: "darwin"
    label: "Charles Darwin"
    pattern: "**/darwin/**/*"
    metadata_field: "author"
    document_count: 8234
  - id: "evolution"
    label: "Evolution"
    xpath: "//subject[contains(., 'evolution')]"
    document_count: 3456

embeddings:
  model: "Livingwithmachines/bert_1760_1900"
  pooling: "mean"
  chunk_size: 1000
  chunk_overlap: 100

vector_store:
  type: "chromadb"
  collection_name: "darwin_correspondence"
  persist_directory: "backend/targets/chroma_db"

search:
  type: "hybrid"
  k_default: 10
  test_query: "evolution natural selection"
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
        backup_dir = f"backend/targets.backup.{int(time.time())}"

        # Backup current
        shutil.move("backend/targets", backup_dir)

        # Install new
        shutil.move(new_corpus_path, "backend/targets")

        # Clear caches
        manifest_loader.invalidate_cache()

        # Exit wizard mode and restart
        os.environ["CORPUS_WIZARD_MODE"] = "false"
        await self.restart_server()
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
        @continue="buildCorpus"
      />
    </div>

    <!-- Step 5: Build Progress -->
    <div v-if="currentStep === 5" class="wizard-step">
      <h2>Building Vector Store</h2>
      <BuildProgress
        :progress="buildProgress"
        :logs="buildLogs"
        @complete="testCorpus"
      />
    </div>

    <!-- Step 6: Test & Activate -->
    <div v-if="currentStep === 6" class="wizard-step">
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