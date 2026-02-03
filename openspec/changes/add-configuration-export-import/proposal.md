# Add Configuration Export/Import Functionality

## Summary

Add the ability to export and import complete corpus and test target configurations through the UI, allowing users to save, share, and restore their ATLAS setup configurations. This is distinct from the existing session export feature and focuses on system configuration portability.

## Motivation

Currently, users who have carefully configured a corpus with specific settings (source paths, embedding models, chunk sizes, retrieval parameters, etc.) and test targets cannot easily:
- Save their configuration for backup
- Share configurations with colleagues
- Replicate setups across different environments
- Quickly switch between different configuration profiles
- Document their experimental setups for research reproducibility

This feature addresses these needs by providing a comprehensive configuration export/import mechanism that captures all settings needed to reproduce an ATLAS setup.

## Detailed Design

### 1. Configuration Export

**Export Button Location:**
- Add "Export Configuration" button in the main UI above the Test Target box
- Clearly labeled to distinguish from session export
- Icon: download icon with gear/cog symbol

**Export Contents:**
The exported JSON file will include:
- **Corpus Configuration:**
  - Source file paths/URLs
  - Embedding model settings
  - Chunk size and overlap
  - Text splitter configuration
  - Retrieval parameters
  - Filter configurations
  - Corpus metadata
- **Test Target Settings:**
  - LLM provider and model
  - Temperature and other parameters
  - System prompts
  - Search settings
- **System Configuration:**
  - Telemetry settings (from the previous proposal)
  - Inter-rater feedback settings
  - Any other toggle states
- **Metadata:**
  - Export timestamp
  - ATLAS version
  - Configuration name/description

**File Format:**
```json
{
  "atlas_config_version": "1.0",
  "exported_at": "2024-02-03T10:30:00Z",
  "atlas_version": "1.2.3",
  "config_name": "Production Setup - Feb 2024",
  "description": "Standard configuration for parliamentary corpus",
  "corpus": {
    "source": {
      "type": "file_path",
      "path": "/data/corpus/parliamentary",
      "url": null
    },
    "embedding": {
      "model": "Livingwithmachines/bert_1890_1900",
      "chunk_size": 1500,
      "chunk_overlap": 150,
      "pooling": "mean"
    },
    "retrieval": {
      "algorithm": "hnsw",
      "large_retrieval_size_single": 120,
      "large_retrieval_size_all": 80
    },
    "filters": {
      "enabled_filters": ["date", "location", "speaker"],
      "filter_config": {...}
    }
  },
  "test_target": {
    "provider": "anthropic",
    "model": "claude-3-5-haiku",
    "temperature": 0.7,
    "search_k": 20,
    "search_type": "similarity",
    "system_prompt": "..."
  },
  "system": {
    "telemetry_enabled": false,
    "inter_rater_enabled": true
  }
}
```

### 2. Configuration Import

**Import Access:**
- New option in corpus wizard: "Import Configuration" button on first step
- Also available from main settings/configuration menu
- Clear distinction from session import

**Import Process:**
1. User selects "Import Configuration"
2. File picker opens (accepts .json files)
3. System validates the configuration file
4. Shows preview of what will be imported
5. User confirms or cancels import
6. System applies configuration with appropriate validations

**Validation Steps:**
- Check configuration version compatibility
- Validate required fields are present
- Verify file paths/URLs are accessible (with option to update)
- Check model availability
- Warn about any incompatible settings

### 3. UI Components

**Main UI Changes:**
- Add "Export Configuration" button with gear-download icon
- Tooltip: "Export corpus and test target configuration"
- Position: Above test target box, aligned right

**Wizard Changes:**
- Add "Import Configuration" option on metadata step
- Show configuration preview dialog
- Allow editing paths/URLs if needed during import

### 4. Backend Implementation

**New Endpoints:**
- `GET /api/configuration/export` - Generate and return configuration JSON
- `POST /api/configuration/import` - Validate and apply imported configuration
- `POST /api/configuration/validate` - Validate configuration without applying

### 5. Security Considerations

- Sanitize file paths in exports (use relative paths where possible)
- No sensitive data (API keys, passwords) in exports
- Validate all imported data to prevent injection
- File size limits for imports (e.g., 10MB max)

## Breaking Changes

None. This is purely additive functionality.

## Alternatives Considered

1. **Merge with Session Export:**
   - Rejected: Different use cases and data types
   - Session export is for conversation history
   - Configuration export is for system setup

2. **YAML Format:**
   - Rejected: JSON is already used throughout the system
   - Better browser support for JSON
   - Consistent with existing corpus_active.json format

3. **Database Storage:**
   - Rejected for initial implementation
   - File export provides better portability
   - Could be added as additional option later

## Testing Strategy

1. Unit tests for export/import functions
2. Integration tests for configuration application
3. E2E tests for complete workflow
4. Edge cases: missing fields, version mismatches, invalid paths

## Implementation Priority

Medium-High. This significantly improves usability for:
- Researchers sharing experimental setups
- System administrators managing deployments
- Users backing up their configurations
- Documentation of reproducible experiments