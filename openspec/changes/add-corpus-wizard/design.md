# Design: UI-Driven Corpus Configuration Wizard

## Overview

This design document outlines the architecture for a UI-driven corpus configuration wizard that enables researchers to swap between different text corpora without code changes, supporting both local and GitHub-hosted sources with intelligent filter discovery.

## Design Principles

1. **User-Driven Discovery**: Leverage user's domain knowledge rather than pure automation
2. **Progressive Enhancement**: Start with simple defaults, allow refinement
3. **Fail-Fast**: Clear errors rather than silent degradation
4. **Atomic Operations**: Corpus swaps are all-or-nothing with rollback
5. **Research-Focused**: Optimize for research needs (metadata, citations, provenance)

## Architecture Decisions

### Decision 1: UI Wizard vs Command-Line

**Choice**: UI-based wizard

**Rationale**:
- Non-technical users (humanities researchers) need visual feedback
- Complex configuration benefits from progressive disclosure
- Progress tracking is clearer in UI
- Filter preview/testing requires interactive exploration

**Rejected Alternatives**:
- Pure CLI: Too complex for non-technical users
- Config files only: No discovery or validation
- MCP servers: Overengineered for the use case

### Decision 2: Metadata-First Approach

**Choice**: Collect user metadata before analysis

**Rationale**:
- User knows their corpus better than algorithms
- Metadata guides filter discovery (e.g., knowing "Darwin" is important)
- Time period informs embedding model selection
- Copyright/DOI needed for academic use

**Trade-offs**:
- Requires more user input upfront
- But produces better filter suggestions
- Reduces ambiguity in discovery phase

### Decision 3: GitHub Integration Strategy

**Choice**: Support both git clone and API download

**Rationale**:
- Git clone with sparse checkout is efficient for large repos
- API download works in environments without git
- Local caching prevents repeated downloads
- Supports private repos with tokens

**Implementation**:
```python
if has_git_binary():
    use_sparse_checkout()  # Efficient for large repos
else:
    use_github_api()       # Fallback for restricted environments
```

### Decision 4: Filter Discovery Algorithm

**Choice**: Hybrid approach - metadata hints + structural analysis

**Algorithm**:
1. Use metadata to identify important entities
2. Analyze directory structure for patterns
3. Sample content for metadata extraction (XML tags, headers)
4. Combine all signals with confidence scoring
5. Present ranked suggestions to user

**Example**:
```python
filters = []
# From metadata - high confidence
if "Darwin" in metadata.people:
    filters.append(Filter(
        pattern="**/darwin/**",
        confidence=0.9,
        source="metadata"
    ))

# From structure - medium confidence
if has_year_patterns(directory_structure):
    filters.append(Filter(
        pattern="**/[0-9]{4}/**",
        confidence=0.7,
        source="structure"
    ))
```

### Decision 5: Configuration Schema

**Choice**: YAML with comprehensive metadata

**Schema Structure**:
```yaml
metadata:           # Research metadata
  name: str
  time_period: {from: int, to: int}
  copyright: {status: str, statement: str}
  doi: str?

source:            # Where to get corpus
  type: enum[local, github]
  location: str

filters:           # Discovered/configured filters
  - id: str
    label: str
    pattern: str

embeddings:        # Model configuration
  model: str
  chunk_size: int

vector_store:      # Storage configuration
  type: str
  collection_name: str
```

**Rationale**:
- YAML is human-readable and editable
- Comprehensive metadata for research needs
- Portable between instances
- Version control friendly

### Decision 6: Embedding Model Recommendation

**Choice**: Rule-based recommendations with period matching

**Rules**:
1. Historical texts (pre-1900): Livingwithmachines models
2. Modern texts: sentence-transformers
3. Mixed periods: General purpose models
4. Domain-specific: Future extension point

**Implementation**:
```python
def recommend_model(metadata):
    if metadata.time_period.from < 1900:
        return "Livingwithmachines/bert_1760_1900"
    else:
        return "sentence-transformers/all-MiniLM-L6-v2"
```

### Decision 7: Progress Tracking

**Choice**: Server-Sent Events (SSE) for real-time updates

**Rationale**:
- Unidirectional (server→client) is sufficient
- Built-in reconnection
- Works through proxies
- Simple to implement

**Message Format**:
```json
{
  "stage": "processing",
  "current": 1523,
  "total": 5000,
  "document": "darwin/letters/1859/letter_2534.xml",
  "elapsed": 120,
  "estimated_remaining": 280
}
```

### Decision 8: Atomic Corpus Swapping

**Choice**: Backup-swap-validate pattern

**Process**:
1. Build new corpus in `create/output/`
2. Backup current `backend/targets/` with timestamp
3. Move new corpus to `backend/targets/`
4. Validate with test query
5. On failure: restore from backup

**Rationale**:
- Zero chance of partial state
- Easy rollback
- Preserves corpus history
- Simple to understand

### Decision 9: Wizard Mode

**Choice**: Separate operational mode

**Implementation**:
- Environment variable `CORPUS_WIZARD_MODE=true`
- Redirects all endpoints to wizard UI
- Prevents normal queries during configuration
- Clear separation of concerns

**Benefits**:
- No accidental queries during swap
- Simplified frontend routing
- Clear user expectations
- Easy emergency exit

## Component Design

### Backend Components

#### CorpusWizard (Orchestrator)
```python
class CorpusWizard:
    """Main orchestrator for wizard operations"""

    async def analyze_corpus(source, metadata) -> AnalysisResult
    async def build_corpus(config) -> AsyncIterator[Progress]
    async def swap_corpus(new_path) -> None
    async def rollback() -> None
```

#### CorpusAnalyzer
```python
class CorpusAnalyzer:
    """Analyzes corpus structure and content"""

    def analyze_structure(path) -> StructureAnalysis
    def extract_metadata(samples) -> ExtractedMetadata
    def suggest_filters(analysis, hints) -> List[Filter]
```

#### FilterInferenceEngine
```python
class FilterInferenceEngine:
    """Infers filters from patterns"""

    def infer_temporal(date_range) -> List[Filter]
    def infer_entities(entities, content) -> List[Filter]
    def infer_structural(directory_tree) -> List[Filter]
```

#### ModelRecommender
```python
class ModelRecommender:
    """Recommends embedding models"""

    def recommend(metadata) -> List[Recommendation]
    def test_model(model, sample_text) -> Performance
```

### Frontend Components

#### WizardController
- Manages wizard state
- Handles navigation
- Persists progress
- Coordinates API calls

#### Step Components
1. `MetadataCollector`: Form for corpus information
2. `SourceSelector`: Local/GitHub selection
3. `FilterConfigurator`: Filter discovery and editing
4. `ModelSelector`: Model recommendations and testing
5. `ProgressTracker`: Build progress with logs
6. `CorpusTester`: Validation before activation

### Data Flow

```
User Input → Metadata Collection → Structure Analysis →
Filter Discovery → Model Selection → Configuration Generation →
Vector Store Build → Validation → Atomic Swap → Restart
```

## Error Handling

### Failure Points and Mitigation

1. **GitHub Connection Failure**
   - Mitigation: Offer download link for manual placement
   - Fallback: Support zip file upload

2. **Filter Discovery Produces No Results**
   - Mitigation: Provide manual filter creation
   - Default: Single "all" filter

3. **Build Failure Mid-Process**
   - Mitigation: Resumable builds from checkpoint
   - Cleanup: Remove partial outputs

4. **Model Unavailable**
   - Mitigation: Fallback to general purpose model
   - Warning: Clear performance implications

5. **Swap Failure**
   - Mitigation: Automatic rollback from backup
   - Recovery: Manual restore command

## Performance Considerations

### Large Corpus Handling

**Challenge**: Corpora with >100k documents

**Solutions**:
1. Streaming processing (no full memory load)
2. Batched vector store updates
3. Progress checkpointing
4. Parallel processing where possible

### GitHub Download Optimization

**Strategies**:
1. Sparse checkout (only corpus directory)
2. Shallow clone (--depth=1)
3. Local caching with TTL
4. CDN usage for public repos

### UI Responsiveness

**Techniques**:
1. Debounced analysis requests
2. Virtualized lists for many filters
3. Lazy loading of corpus samples
4. Background prefetch of next step

## Security Considerations

1. **GitHub Token Storage**: Use environment variables, never store in config
2. **Path Traversal**: Validate all file paths, restrict to corpus directory
3. **XML Parsing**: Use defusedxml to prevent XXE attacks
4. **YAML Loading**: Use safe_load to prevent code execution
5. **Corpus Isolation**: Each corpus in separate collection

## Extensibility Points

### Future Enhancements

1. **Additional File Formats**
   - PDF support with PyMuPDF
   - CSV/TSV with pandas
   - DOCX with python-docx

2. **Advanced Filter Types**
   - NER-based filters (automatic entity extraction)
   - Topic modeling filters
   - Semantic similarity filters

3. **Corpus Updates**
   - Incremental updates from GitHub
   - Scheduled refresh
   - Change detection

4. **Multi-Corpus Support**
   - Parallel corpus search
   - Cross-corpus linking
   - Corpus federation

## Testing Strategy

### Test Scenarios

1. **Happy Path**: Hansard ↔ Darwin swap
2. **Edge Cases**: Empty corpus, single file, 1M+ documents
3. **Failure Recovery**: Network loss, disk full, invalid config
4. **Performance**: Large corpus build time < 30 minutes

### Test Data

```
test_corpora/
├── minimal/        # 10 files
├── standard/       # 1,000 files
├── large/          # 100,000 files
└── edge_cases/     # Various problem scenarios
```

## Migration Path

### From Current System

1. Generate configs for existing Hansard corpus
2. No breaking changes to current flow
3. Wizard as opt-in feature
4. Gradual migration of hardcoded values

### Backward Compatibility

- Existing corpus continues to work
- Manual corpus creation still supported
- Config files can be hand-edited
- Make commands remain available

## Success Metrics

1. **Usability**: Non-technical user can swap corpus in <30 minutes
2. **Reliability**: 95% success rate for corpus swaps
3. **Performance**: <1 second to load wizard, <30 min for typical corpus
4. **Flexibility**: Support 5+ different corpus structures
5. **Adoption**: 50% of users use wizard vs manual process

## Conclusion

This design provides a user-friendly, robust solution for corpus configuration that balances automation with user control. The metadata-first approach, combined with intelligent discovery and clear progress tracking, makes corpus swapping accessible to non-technical researchers while maintaining the flexibility needed for diverse corpus types.