# Build Metadata Specification

## ADDED Requirements

### Requirement: Build Metadata in Manifest
The system SHALL capture comprehensive build metadata during corpus builds and store it in the manifest.

#### Scenario: Build metadata captured during build
- **WHEN** a corpus build completes via the Corpus Wizard
- **THEN** the manifest.json SHALL contain a `build` section with timing, machine specs, and version information

#### Scenario: Build timing recorded
- **WHEN** a corpus build completes
- **THEN** the `build` section SHALL include `started_at`, `completed_at`, and `duration_seconds` fields

#### Scenario: Machine information captured
- **WHEN** a corpus build completes
- **THEN** the `build.machine` section SHALL include `hostname`, `platform`, `platform_version`, `cpu_model`, `cpu_cores`, `cpu_threads`, `ram_gb`, `gpu_available`, and optionally `gpu_model` and `gpu_memory_gb`

#### Scenario: Version information captured
- **WHEN** a corpus build completes
- **THEN** the `build` section SHALL include `processing_mode`, `workers_used`, `atlas_version`, `python_version`, and `embedding_library` fields

### Requirement: System Info Utility
The system SHALL provide a utility to collect machine and environment information for build metadata.

#### Scenario: System info collection
- **WHEN** `system_info.py` utilities are called
- **THEN** they SHALL return accurate information about the host machine including CPU, RAM, GPU availability, and software versions

### Requirement: Build Info Display in UI
The Test Target box and VectorStoreInfo modal SHALL display build metadata from the manifest.

#### Scenario: Test Target box shows build info
- **WHEN** the Test Target box is displayed
- **THEN** it SHALL show build date, duration, processing mode, and machine specs summary

#### Scenario: VectorStoreInfo modal shows detailed build info
- **WHEN** the VectorStoreInfo modal is opened
- **THEN** it SHALL display comprehensive build metadata including full machine specifications

### Requirement: Build Metadata in API Response
The `/api/vector-store-info` endpoint SHALL include build metadata in its response.

#### Scenario: API returns build metadata
- **WHEN** a GET request is made to `/api/vector-store-info`
- **THEN** the response SHALL include the `build` section from the manifest if available

## REMOVED Requirements

### Requirement: Manifest Context Toggle
The system SHALL NO LONGER use the `MANIFEST_CONTEXT_ENABLED` environment variable.

**Reason**: Manifest context injection for meta-questions should always be enabled. With enhanced build metadata, the manifest provides rich context that improves LLM responses.

**Migration**: Remove this variable from .env files. Manifest context will always be included in LLM queries for meta-questions.

#### Scenario: Manifest context env var removed
- **WHEN** checking .env template files
- **THEN** no `MANIFEST_CONTEXT_ENABLED` variable SHALL exist

#### Scenario: Manifest context always included
- **WHEN** processing meta-questions about the corpus
- **THEN** manifest context SHALL always be injected into the LLM prompt
