# Implementation Tasks

## Phase 1: Remove Session Validation Feature

### 1.1 Remove Backend Validation Code
- [ ] Delete `backend/services/validation_service.py`
- [ ] Delete `backend/routers/validation.py`
- [ ] Remove validation router import from `backend/app.py`
- [ ] Remove validation export from `backend/routers/__init__.py`
- [ ] Verify no other code imports validation_service or validation router

### 1.2 Remove Validation Environment Variables
- [ ] Remove `VALIDATION_LLM_MODE` from `config/.env.template`
- [ ] Remove `VALIDATION_LLM_DEFAULT` from `config/.env.template`
- [ ] Remove `VALIDATION_LLM_ALTERNATE` from `config/.env.template`
- [ ] Remove `VALIDATION_PROVIDER_DEFAULT` from `config/.env.template`
- [ ] Remove `VALIDATION_PROVIDER_ALTERNATE` from `config/.env.template`
- [ ] Remove `VALIDATION_ENABLED` from `config/.env.template`
- [ ] Remove same from `config/.env.development`
- [ ] Remove same from `config/.env.staging` (if exists)
- [ ] Remove same from `config/.env.production` (if exists)

### 1.3 Remove AI-Assisted Feedback
- [ ] Remove `VITE_FEEDBACK_AI_ASSISTED_ENABLED` from all .env files
- [ ] Remove AI-assisted option from `InlineFeedback.vue` (`isAIAssistedEnabled` computed property)
- [ ] Remove AI-assisted button from template
- [ ] Evaluate if `AIEnhancedFeedback.vue` can be deleted or if it's used elsewhere
- [ ] Update `hasAnyFeedbackOptions` computed property

## Phase 2: Move Feedback Type Toggles to Wizard

### 2.1 Add Manifest Support for Feedback Config
- [ ] Add `FeedbackConfig` model to `backend/modules/corpus_config.py`
  ```python
  class FeedbackConfig(BaseModel):
      simple_enabled: bool = Field(default=True)
      enhanced_enabled: bool = Field(default=True)
      skip_enabled: bool = Field(default=True)
  ```
- [ ] Add `feedback` field to `CorpusConfig` model
- [ ] Update `corpus_builder.py` to include feedback config in manifest
- [ ] Bump manifest version to 1.4

### 2.2 Add Backend API for Feedback Config
- [ ] Create `GET /api/system/feedback-config` endpoint
- [ ] Read feedback config from manifest (with defaults fallback)
- [ ] Return JSON with enabled/disabled status for each feedback type

### 2.3 Update Corpus Wizard Backend
- [ ] Add feedback fields to build request handling in `corpus_wizard.py`
- [ ] Include feedback config when generating manifest
- [ ] Add validation for boolean fields

### 2.4 Add Feedback Config UI to Corpus Wizard
- [ ] Add "Feedback Configuration" section to `RequirementsChecker.vue`
- [ ] Add toggle for Simple Feedback (default: enabled)
- [ ] Add toggle for Enhanced Feedback (default: enabled)
- [ ] Add toggle for Skip option (default: enabled)
- [ ] Add help text explaining each option
- [ ] Wire up to build request payload

### 2.5 Update Frontend to Read from API
- [ ] Update `InlineFeedback.vue` to fetch config from `/api/system/feedback-config`
- [ ] Add loading state while config is fetched
- [ ] Add error handling if API fails (fallback to all enabled)
- [ ] Remove `VITE_FEEDBACK_*` env var usage
- [ ] Cache config to avoid repeated API calls

### 2.6 Remove Feedback Type Env Vars
- [ ] Remove `VITE_FEEDBACK_SIMPLE_ENABLED` from `config/.env.template`
- [ ] Remove `VITE_FEEDBACK_ENHANCED_ENABLED` from `config/.env.template`
- [ ] Remove `VITE_FEEDBACK_SKIP_ENABLED` from `config/.env.template`
- [ ] Remove same from `config/.env.development`
- [ ] Remove same from other .env files

## Phase 3: Documentation Updates

### 3.1 Update Configuration Documentation
- [ ] Update `docs/configuration.md` to remove VALIDATION_* vars
- [ ] Update `docs/configuration.md` to remove VITE_FEEDBACK_* vars
- [ ] Document that feedback config is now in manifest
- [ ] Add section on Corpus Wizard feedback configuration

### 3.2 Update Telemetry Documentation
- [ ] Document that `TELEMETRY_ENABLED` is a system-level override
- [ ] Document that `VITE_TELEMETRY_ENABLED` controls UI visibility
- [ ] Clarify relationship between env vars and wizard settings

## Phase 4: Remove MANIFEST_CONTEXT_ENABLED and Enhance Build Metadata

### 4.1 Remove MANIFEST_CONTEXT_ENABLED Environment Variable
- [ ] Remove `MANIFEST_CONTEXT_ENABLED` from `config/.env.template`
- [ ] Remove `MANIFEST_CONTEXT_ENABLED` from `config/.env.development`
- [ ] Remove same from other .env files
- [ ] Update `backend/modules/manifest_context.py` to always include manifest context (remove env var check)
- [ ] Update documentation to reflect change

### 4.2 Create System Info Utility
- [ ] Create `backend/utils/system_info.py` with functions to collect:
  - Hostname
  - Platform (OS name and version)
  - CPU model, cores, threads
  - RAM total (GB)
  - GPU availability, model, memory (if available)
  - Python version
  - Key library versions (sentence-transformers, torch, etc.)

### 4.3 Add Build Metadata to Manifest
- [ ] Add `BuildMetadata` model to `backend/modules/corpus_config.py`
  ```python
  class MachineInfo(BaseModel):
      hostname: str
      platform: str
      platform_version: str
      cpu_model: str
      cpu_cores: int
      cpu_threads: int
      ram_gb: float
      gpu_available: bool
      gpu_model: Optional[str] = None
      gpu_memory_gb: Optional[float] = None

  class BuildMetadata(BaseModel):
      started_at: datetime
      completed_at: datetime
      duration_seconds: float
      machine: MachineInfo
      processing_mode: str  # cpu or gpu
      workers_used: int
      atlas_version: str
      python_version: str
      embedding_library: str
  ```
- [ ] Add `build` field to manifest schema
- [ ] Update `corpus_builder.py` to collect and include build metadata
- [ ] Record build start time at beginning of build
- [ ] Record build end time and calculate duration at completion

### 4.4 Update Corpus Wizard to Collect Build Metadata
- [ ] Import system_info utility in `corpus_wizard.py`
- [ ] Collect machine info at start of build
- [ ] Include build metadata in manifest generation
- [ ] Store ATLAS version from config

### 4.5 Update Test Target Box UI to Display Build Info
- [ ] Update `TestTargetBox.vue` to display new build metadata fields
- [ ] Add "Build Information" section showing:
  - Build date/time
  - Build duration
  - Processing mode (CPU/GPU)
  - Machine specs summary
- [ ] Update `VectorStoreInfo.vue` modal to include detailed build information
- [ ] Update `/api/vector-store-info` to include build metadata in response

### 4.6 Bump Manifest Version
- [ ] Update manifest version to 1.5 to reflect build metadata addition

## Phase 5: Simplify Makefile Targets

### 5.1 Remove Targets from Main Makefile
- [ ] Remove `pm` target (prepare embedding model)
- [ ] Remove `hansard-analysis` target
- [ ] Remove `health-verbose` target
- [ ] Remove `health-json` target
- [ ] Remove `health-critical` target
- [ ] Remove `backup-prod` target (document in ops guide instead)

### 5.2 Remove Targets from deploy/Makefile
- [ ] Remove `clean-tests` target
- [ ] Remove `corpus-backup` target
- [ ] Remove `corpus-restore` target
- [ ] Remove `corpus-list` target

### 5.3 Delete Help Files
- [ ] Delete `deploy/help.mk` file entirely
- [ ] Delete `utils/help.mk` file entirely
- [ ] Remove `include deploy/help.mk` from main Makefile
- [ ] Remove `include utils/help.mk` from main Makefile

### 5.4 Update Help Target
- [ ] Ensure `make help` still works after removing help.mk files
- [ ] Verify all essential targets are documented in help output

## Phase 6: Wizard UI Redesign

### 6.1 Update SourceSelector.vue
- [ ] Remove default placeholder from directory input field
- [ ] Add hint text below field: "Enter relative path (./data) or absolute path (/home/user/data)"
- [ ] Replace `#3498db` (blue) with `#000` (black) for active/hover states
- [ ] Replace `#e3f2fd` (blue tint) with `#f5f5f5` (light gray) for backgrounds
- [ ] Update `.btn-primary` to use `background: #000; color: #fff;`
- [ ] Update hover states to use `background: #888;`

### 6.2 Update CorpusWizard.vue
- [ ] Convert step indicators to monochrome (black filled, gray outline)
- [ ] Replace colored progress bar with black/gray
- [ ] Update navigation buttons to monochrome styling
- [ ] Ensure Times New Roman font is applied consistently

### 6.3 Update RequirementsChecker.vue
- [ ] Convert toggle switches from colored to black/gray
- [ ] Update section headers and dividers to monochrome
- [ ] Replace any blue/green status indicators with black/gray

### 6.4 Update EmbeddingConfig.vue
- [ ] Convert form styling to monochrome
- [ ] Update selection cards to use black border for active state
- [ ] Replace colored badges with text-only or monochrome badges

### 6.5 Update FilterConfig.vue
- [ ] Convert filter cards to monochrome styling
- [ ] Update add/remove buttons to black/white
- [ ] Replace colored indicators with monochrome

### 6.6 Update BuildProgress.vue
- [ ] Convert progress bar from colored to black/gray
- [ ] Update status indicators to monochrome
- [ ] Replace success green (#4caf50) with black or gray
- [ ] Replace error red (#e74c3c) with dark gray (#333) plus text indicator

### 6.7 Update ReviewConfig.vue
- [ ] Convert summary cards to monochrome styling
- [ ] Update confirmation buttons to black/white
- [ ] Ensure consistent monochrome throughout

## Acceptance Criteria

### Validation Removal
- [ ] No `VALIDATION_*` env vars in any .env file
- [ ] No validation_service.py or validation.py files
- [ ] No `/api/validate_session` or `/api/validate_config` endpoints
- [ ] No "AI Assisted Feedback" button in UI

### Feedback Config Migration
- [ ] Feedback toggles configurable via Corpus Wizard UI
- [ ] Feedback config stored in manifest.json under `feedback` key
- [ ] Frontend fetches feedback config from API at runtime
- [ ] No `VITE_FEEDBACK_*` env vars in .env files
- [ ] Defaults to all enabled when manifest has no feedback section

### Build Metadata Enhancement
- [ ] No `MANIFEST_CONTEXT_ENABLED` env var in any .env file
- [ ] Manifest context always included in LLM queries (no toggle)
- [ ] Build metadata captured during corpus wizard builds
- [ ] Manifest includes `build` section with machine specs and timing
- [ ] Test Target box displays build information
- [ ] VectorStoreInfo modal shows detailed build info

### Makefile Simplification
- [ ] No `pm`, `hansard-analysis`, `health-verbose`, `health-json`, `health-critical`, `backup-prod` targets in main Makefile
- [ ] No `clean-tests`, `corpus-backup`, `corpus-restore`, `corpus-list` targets in deploy/Makefile
- [ ] No `deploy/help.mk` file exists
- [ ] No `utils/help.mk` file exists
- [ ] `make help` still works and shows essential targets
- [ ] Essential targets still function: `b`, `f`, `d`, `reset`, `p`, `dp`, `sp`, `s`, `ds`, `l`, `c`, `health`

### Wizard UI Redesign
- [ ] No blue (#3498db) colors in wizard components
- [ ] No green (#4caf50) colors in wizard components
- [ ] No red (#e74c3c) colors in wizard components (use text indicators instead)
- [ ] Directory input has no default placeholder
- [ ] Directory input has path format hint text
- [ ] All buttons use monochrome styling (black/white/gray)
- [ ] Step indicators use monochrome styling
- [ ] Wizard visually matches main application design

### Documentation
- [ ] Configuration docs updated
- [ ] Removed references to deleted env vars
- [ ] Wizard feedback configuration documented
- [ ] Build metadata fields documented

## Testing Requirements

### Phase 1 Tests
- [ ] Verify validation endpoints return 404 after removal
- [ ] Verify AI-assisted feedback button not visible
- [ ] Verify other feedback types still work

### Phase 2 Tests
- [ ] Unit test: FeedbackConfig model validates correctly
- [ ] Unit test: Manifest generation includes feedback config
- [ ] Integration test: `/api/system/feedback-config` returns correct values
- [ ] E2E test: Feedback buttons show/hide based on manifest config
- [ ] E2E test: Corpus Wizard feedback config persists to manifest

### Phase 4 Tests
- [ ] Unit test: system_info collects correct machine information
- [ ] Unit test: BuildMetadata model validates correctly
- [ ] Integration test: Corpus build includes build metadata in manifest
- [ ] Integration test: `/api/vector-store-info` includes build metadata
- [ ] E2E test: Test Target box displays build information
- [ ] Verify manifest context works without MANIFEST_CONTEXT_ENABLED env var

### Phase 5 Tests
- [ ] Verify `make help` works after removing help.mk files
- [ ] Verify essential targets still work: `make b`, `make f`, `make d`
- [ ] Verify removed targets return error: `make pm`, `make corpus-backup`
- [ ] Verify no include errors in Makefile

### Phase 6 Tests
- [ ] Visual test: No blue (#3498db) colors appear in wizard
- [ ] Visual test: No green (#4caf50) colors appear in wizard
- [ ] Visual test: Directory input has no default placeholder
- [ ] Visual test: Directory input shows path format hint
- [ ] Visual test: Step indicators use monochrome styling
- [ ] Visual test: Buttons match main UI styling (black/white/gray)

### Regression Tests
- [ ] Simple feedback still works
- [ ] Enhanced feedback still works
- [ ] Skip option still works
- [ ] Telemetry toggle still works
- [ ] Manifest context injection still works for meta-questions
- [ ] Wizard functionality unchanged after styling updates
