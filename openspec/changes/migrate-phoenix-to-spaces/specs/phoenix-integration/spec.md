# Phoenix Integration Specification Delta

## ADDED Requirements

### Requirement: Phoenix Space Configuration
The system SHALL support Phoenix spaces-based architecture for cloud telemetry integration. The AIINFRA project uses the `aiinfra` space containing all ATLAS variants (Hansard, Darwin, future variants).

#### Scenario: Core Telemetry with AIINFRA Space Configuration
- **GIVEN** AIINFRA project is configured with `PHOENIX_SPACE_ID=aiinfra` and `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"`
- **WHEN** system initializes telemetry in `backend/telemetry/core.py`
- **THEN** OTEL traces endpoint is constructed as `https://app.phoenix.arize.com/s/aiinfra/v1/traces`
- **AND** all telemetry traces are sent to the `aiinfra` space
- **AND** traces appear in Phoenix Cloud under `aiinfra` space

#### Scenario: Backup with Space Configuration
- **GIVEN** user has configured `PHOENIX_SPACE_ID=aiinfra`
- **WHEN** backup script initializes Phoenix client
- **THEN** client connects to `https://app.phoenix.arize.com/s/aiinfra`
- **AND** spans are retrieved from correct Phoenix space
- **AND** backup data matches Phoenix UI for that space

#### Scenario: Finding AIINFRA Space in Phoenix UI
- **GIVEN** user is logged into Phoenix Cloud with access to AIINFRA space
- **WHEN** user navigates to projects view
- **THEN** URL structure is `https://app.phoenix.arize.com/s/aiinfra/projects`
- **AND** all ATLAS projects (Hansard, Darwin variants) are visible within this space

### Requirement: Consistent Space Configuration
The system SHALL use consistent space configuration across telemetry and backup functionality. All ATLAS variants (Hansard, Darwin) SHALL use the same `aiinfra` space.

#### Scenario: Unified AIINFRA Space Configuration
- **GIVEN** all ATLAS environments are configured with `PHOENIX_SPACE_ID=aiinfra`
- **WHEN** both telemetry and backup systems initialize across Hansard and Darwin codebases
- **THEN** all components use the `aiinfra` space identifier
- **AND** all traces and backups connect to the same Phoenix space
- **AND** configuration is DRY across ATLAS variants

#### Scenario: Configuration Validation
- **GIVEN** telemetry is enabled
- **WHEN** system initializes Phoenix integration
- **THEN** system validates `PHOENIX_COLLECTOR_ENDPOINT` includes space path
- **AND** system logs warning if using non-space endpoint format

## MODIFIED Requirements

### Requirement: Phoenix OTEL Trace Export Endpoint
The Phoenix telemetry collector endpoint SHALL use space-based URL structure.

**Previous behavior**: Default `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com"` (legacy space)
**New behavior**: Explicit `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"` (AIINFRA project space)

#### Scenario: OTEL Trace Export to Space
- **GIVEN** `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"` is configured
- **WHEN** `backend/telemetry/core.py:134` constructs trace endpoint
- **THEN** endpoint is `https://app.phoenix.arize.com/s/aiinfra/v1/traces`
- **AND** traces export to correct space
- **AND** traces appear in correct Phoenix space project

#### Scenario: Multi-Variant Project Isolation
- **GIVEN** ATLAS-Hansard uses `PHOENIX_PROJECT_NAME=ATLAS-Hansard-Dev` in `aiinfra` space
- **AND** ATLAS-Darwin uses `PHOENIX_PROJECT_NAME=ATLAS-Darwin-Dev` in same `aiinfra` space
- **WHEN** traces are exported from each variant
- **THEN** Hansard traces go to `ATLAS-Hansard-Dev` project
- **AND** Darwin traces go to `ATLAS-Darwin-Dev` project
- **AND** both projects are visible within single `aiinfra` space
- **AND** variants can be compared side-by-side in Phoenix UI

### Requirement: Phoenix Client Initialization
Phoenix client in backup script SHALL initialize with space-based URL.

**Previous behavior**: Default `PHOENIX_BASE_URL="https://app.phoenix.arize.com/legacy"`
**New behavior**: Default `PHOENIX_BASE_URL="https://app.phoenix.arize.com/s/aiinfra"`

#### Scenario: Backup Client Initialization with Space
- **GIVEN** `PHOENIX_SPACE_ID=aiinfra` is configured
- **WHEN** `utils/scripts/phoenix_backup_prod.py` initializes client
- **THEN** base URL is constructed as `https://app.phoenix.arize.com/s/aiinfra`
- **AND** Phoenix client connects to correct space
- **AND** backup retrieves data from user's space project

#### Scenario: Backup Client Fallback to Collector Endpoint
- **GIVEN** `PHOENIX_SPACE_ID` is not set
- **AND** `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/myspace"` is configured
- **WHEN** backup script initializes
- **THEN** script uses collector endpoint base URL for backup client
- **AND** backup connects to correct space

### Requirement: Phoenix API Calls
All Phoenix REST API calls SHALL use space-based URL structure.

**Affected files**:
- `backend/services/phoenix_client.py` (lines 362, 412, 589, 656)
- `backend/telemetry/feedback.py` (line 224)

#### Scenario: Annotation API with Space
- **GIVEN** `PHOENIX_COLLECTOR_ENDPOINT` includes space path
- **WHEN** system queries span annotations via `phoenix_client.py:412`
- **THEN** API endpoint is `{phoenix_endpoint}/v1/projects/{project}/span_annotations`
- **AND** endpoint includes space in URL path
- **AND** annotations are retrieved from correct space

#### Scenario: Feedback Submission with Space
- **GIVEN** user submits feedback annotation
- **WHEN** `feedback.py:224` sends annotation to Phoenix
- **THEN** annotation is sent to space-based API endpoint
- **AND** annotation appears in correct Phoenix space project
- **AND** annotation is associated with correct span

## Configuration Changes

### Environment Variables

**Added**:
- `PHOENIX_SPACE_ID` - Required. Set to `aiinfra` for AIINFRA project. Identifies the Phoenix space for organizational isolation.

**Modified**:
- `PHOENIX_COLLECTOR_ENDPOINT` - **Required change**. Must be set to `https://app.phoenix.arize.com/s/aiinfra` instead of `https://app.phoenix.arize.com`
- `PHOENIX_BASE_URL` - (Backup script only) Update default from `/legacy` to `https://app.phoenix.arize.com/s/aiinfra`

**Deprecated**:
- Legacy URL format without space path (still works but logs deprecation warning)

### Documentation Requirements

Documentation SHALL include:

1. **AIINFRA Space**: Explanation that `aiinfra` is the AIINFRA project space containing all ATLAS variants
2. **Configuration Examples**: Complete examples showing `PHOENIX_SPACE_ID=aiinfra` for all environments
3. **Migration Steps**: How to update from legacy to `aiinfra` space
4. **Organizational Structure**: How space boundaries enable future research projects
5. **Darwin Fork**: Instructions for applying same configuration to ATLAS Darwin codebase

## Non-Functional Requirements

### Requirement: Clear Error Messages for Configuration Issues
The system SHALL provide actionable warnings for legacy configuration.

#### Scenario: Legacy Endpoint Warning
- **GIVEN** user has configured `PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com"` (no space)
- **WHEN** Phoenix integration initializes
- **THEN** system logs warning: "Phoenix endpoint does not include space path - traces may go to legacy space"
- **AND** system logs recommendation: "Update PHOENIX_COLLECTOR_ENDPOINT to include space: https://app.phoenix.arize.com/s/{your-space}"

### Requirement: Zero Data Loss During Migration
Migration SHALL not cause loss of telemetry data or feedback annotations.

#### Scenario: Safe Migration Without Service Disruption
- **GIVEN** user updates configuration to include space path
- **WHEN** services restart with new configuration
- **THEN** new telemetry exports to new space successfully
- **AND** feedback annotations continue to be collected
- **AND** no traces are lost during transition

#### Scenario: Rollback Support
- **GIVEN** migration encounters issues
- **WHEN** user reverts configuration
- **THEN** system falls back to previous configuration
- **AND** telemetry continues flowing
- **AND** no data is lost during rollback

### Requirement: Performance Unchanged
Space-based URL structure SHALL not impact telemetry or backup performance.

#### Scenario: Trace Export Performance
- **GIVEN** system uses space-based URLs
- **WHEN** telemetry traces are exported during normal operation
- **THEN** export latency is comparable to previous configuration
- **AND** throughput is not degraded
- **AND** batch processing works as before

#### Scenario: Backup Performance
- **GIVEN** backup uses space-based client
- **WHEN** backup script runs
- **THEN** backup completion time is comparable to previous configuration
- **AND** data retrieval speed is maintained
- **AND** no timeout issues occur
