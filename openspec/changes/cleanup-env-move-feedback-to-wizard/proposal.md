# OpenSpec Change Proposal: Cleanup Environment Variables and Move Feedback Config to Wizard

## Change ID
`cleanup-env-move-feedback-to-wizard`

## Summary
Remove deprecated/redundant environment variables and move feedback type configuration from .env files to the Corpus Wizard UI. This continues the pattern established in `move-inter-rater-to-wizard` by consolidating runtime configuration into the corpus manifest.

## Motivation

### Current State
The .env files contain several categories of settings that should be cleaned up:

1. **Telemetry Settings** - `TELEMETRY_ENABLED` and `VITE_TELEMETRY_ENABLED` exist but telemetry is already configurable via the wizard and stored in `system_settings.json`. The env vars now act only as override/kill-switches.

2. **Session Validation Configuration** - 6 env vars (`VALIDATION_*`) control an optional AI-assisted feedback validation feature that is disabled in production and development. This feature appears to be unused and adds complexity.

3. **AI-Assisted Feedback Toggle** - `VITE_FEEDBACK_AI_ASSISTED_ENABLED` is tied to the Session Validation feature and can be removed if validation is removed.

4. **Feedback Type Toggles** - `VITE_FEEDBACK_SIMPLE_ENABLED`, `VITE_FEEDBACK_ENHANCED_ENABLED`, `VITE_FEEDBACK_SKIP_ENABLED` control which feedback buttons appear. These should be corpus-specific and configurable via the wizard.

### Problems with Current Approach
- **Build-time configuration**: VITE_* vars are baked in at build time, requiring rebuilds to change
- **Scattered configuration**: Related settings spread across .env files instead of unified in manifest
- **Unused code**: Session Validation feature adds LLM API costs and code complexity but is disabled
- **Inconsistent pattern**: Inter-rater moved to wizard, but similar settings remain in .env

## Proposed Changes

### Phase 1: Remove Session Validation Feature (BREAKING)
Remove the Session Validation feature entirely:
- Delete `backend/services/validation_service.py`
- Delete `backend/routers/validation.py`
- Remove validation router from `backend/app.py`
- Remove `VALIDATION_*` env vars from all .env files
- Remove `VITE_FEEDBACK_AI_ASSISTED_ENABLED` from .env files
- Remove AI-Assisted feedback button from `InlineFeedback.vue`
- Remove `AIEnhancedFeedback.vue` component (or keep if used elsewhere)

**Rationale**: Feature is disabled in production/development, adds LLM costs when enabled, and complicates the codebase. If needed in future, can be re-implemented as a proper wizard-configured feature.

### Phase 2: Move Feedback Type Toggles to Wizard
Move feedback button visibility to corpus manifest:
- Add `feedback` section to manifest schema with `simple_enabled`, `enhanced_enabled`, `skip_enabled`
- Add Feedback Configuration UI section to Corpus Wizard (RequirementsChecker step)
- Update `InlineFeedback.vue` to read from API endpoint instead of env vars
- Add `/api/system/feedback-config` endpoint to serve feedback configuration
- Remove `VITE_FEEDBACK_*` env vars from .env files

### Phase 3: Simplify Telemetry Configuration
Keep telemetry env vars as system-level overrides but document clearly:
- `TELEMETRY_ENABLED` - System-level kill switch (keep for ops override)
- `VITE_TELEMETRY_ENABLED` - Controls UI toggle visibility (keep for now, may remove later)
- Document that wizard configures user-facing settings, env vars are for ops overrides

### Phase 4: Remove MANIFEST_CONTEXT_ENABLED and Enhance Build Metadata
The `MANIFEST_CONTEXT_ENABLED` env var controls whether vector store metadata is injected into LLM context for meta-questions. This should be:
- Removed as an env var (always enabled, or configured per-corpus)
- Enhanced: The manifest currently lacks detailed build information that would be useful in the Test Target box UI

**Add comprehensive build metadata to manifest:**
```json
{
  "build": {
    "started_at": "2026-02-09T18:30:00.000000",
    "completed_at": "2026-02-09T18:36:38.821375",
    "duration_seconds": 398,
    "machine": {
      "hostname": "build-server-01",
      "platform": "linux",
      "platform_version": "Ubuntu 22.04.3 LTS",
      "cpu_model": "Intel(R) Xeon(R) CPU E5-2680 v4 @ 2.40GHz",
      "cpu_cores": 14,
      "cpu_threads": 28,
      "ram_gb": 64,
      "gpu_available": true,
      "gpu_model": "NVIDIA Tesla V100",
      "gpu_memory_gb": 16
    },
    "processing_mode": "gpu",
    "workers_used": 4,
    "atlas_version": "1.0.0",
    "python_version": "3.10.12",
    "embedding_library": "sentence-transformers==2.2.2"
  }
}
```

This information would:
- Show in the Test Target box UI for transparency
- Help debug performance issues
- Document the build environment for reproducibility
- Replace the need for `MANIFEST_CONTEXT_ENABLED` since manifest always has rich metadata

### Phase 5: Simplify Makefile Targets
Remove redundant Makefile targets now that the Corpus Wizard handles corpus management and model preparation:

**Remove from main Makefile:**
- `pm` - Wizard handles model preparation
- `hansard-analysis` - Too specific, can be run directly via Python
- `health-verbose`, `health-json`, `health-critical` - Use flags on `health` instead
- `backup-prod` - Move to ops documentation

**Remove from deploy/Makefile:**
- `clean-tests` - Covered by `d` (clean dev)
- `corpus-backup`, `corpus-restore`, `corpus-list` - Wizard handles corpus management

**Remove from help files:**
- All `help-*` targets in `deploy/help.mk` and `utils/help.mk` - Overly detailed, basic `help` is sufficient

**Retained targets (essentials only):**
- Development: `b`, `f`, `d`, `reset`, `stop-wizard`
- Production: `p`, `dp`, `sp`
- Staging: `s`, `ds`
- Load testing: `lts`, `ltp` (optional, for specific use cases)
- Utilities: `l`, `c`, `venv`
- System: `health`, `help`

### Phase 6: Wizard UI Redesign for Consistency
The Corpus Wizard UI currently uses colored styling (blue buttons, colored borders) that does not match the main application's minimalist black-and-white design. This phase aligns the wizard with the established design language.

**Design Principles (matching main UI):**
- Text-only interface whenever possible
- Minimalist black and white icons only where necessary
- No colored buttons or highlights
- Times New Roman serif font family
- Monochrome color palette: black (#000), white (#fff), gray (#888, #eee)

**Specific Changes:**

1. **Color Replacements:**
   - Replace blue (#3498db) with black (#000) for primary actions and active states
   - Replace green (#4caf50) success states with gray (#888) or black
   - Replace red (#e74c3c) error states with dark gray (#333) or black with text indicators
   - Replace colored backgrounds (#e3f2fd, #d4edda) with light gray (#f5f5f5)

2. **Button Styling:**
   - Primary buttons: `background: #000; color: #fff; border-radius: 2px;`
   - Hover states: `background: #888;`
   - Secondary buttons: `background: #fff; color: #000; border: 1px solid #000;`

3. **Form Inputs:**
   - Remove default placeholder values from directory input fields
   - Add hint text below fields for path format guidance
   - Example hint: "Enter relative path (./data) or absolute path (/home/user/data)"

4. **Card/Panel Styling:**
   - Active states: black border instead of colored border
   - Hover states: light gray background (#f5f5f5) instead of colored tint
   - Remove all colored badges or indicators

5. **Progress Indicators:**
   - Replace colored step indicators with monochrome (filled/unfilled circles)
   - Active step: black filled circle
   - Completed step: black outline with checkmark
   - Pending step: gray outline

## Impact Assessment

### Breaking Changes
- Session Validation API endpoints removed (`/api/validate_session`, `/api/validate_config`)
- AI-Assisted feedback option removed from UI
- Existing deployments with VALIDATION_ENABLED=true will lose that feature
- `MANIFEST_CONTEXT_ENABLED` env var removed (manifest context always included)

### Non-Breaking Changes
- Feedback type visibility becomes corpus-configurable
- Telemetry env vars remain as overrides
- Build metadata enhanced in manifest (backward compatible - old manifests work without build section)

### Migration Path
1. Remove Session Validation code and env vars
2. Deploy: existing feedback types continue working via env vars
3. Add manifest support for feedback config
4. Deploy: reads from manifest with env var fallback
5. Remove env var fallback in future release
6. Add build metadata collection during corpus builds
7. Update Test Target box UI to display build information

## Files Affected

### Delete
- `backend/services/validation_service.py`
- `backend/routers/validation.py`

### Modify
- `config/.env.template` - Remove VALIDATION_*, VITE_FEEDBACK_AI_ASSISTED_ENABLED, MANIFEST_CONTEXT_ENABLED
- `config/.env.development` - Remove same
- `backend/app.py` - Remove validation router import
- `backend/routers/__init__.py` - Remove validation export
- `frontend/src/components/InlineFeedback.vue` - Remove AI-assisted option, add API config fetch
- `backend/modules/corpus_config.py` - Add FeedbackConfig and BuildMetadata models
- `backend/modules/corpus_builder.py` - Include feedback config and build metadata in manifest
- `backend/routers/corpus_wizard.py` - Handle feedback config in build, collect build metadata
- `frontend/src/components/wizard/RequirementsChecker.vue` - Add feedback config UI
- `backend/modules/manifest_context.py` - Remove env var check (always include manifest context)
- `frontend/src/components/TestTargetBox.vue` - Display build metadata
- `frontend/src/components/VectorStoreInfo.vue` - Display enhanced build information
- `backend/routers/retriever.py` - Include build metadata in `/api/vector-store-info` response

### Create
- `backend/routers/system.py` - Add feedback config endpoint (if not exists)
- `backend/utils/system_info.py` - Utility to collect machine/build information

### Phase 5 Makefile Simplification
- `Makefile` - Remove `pm`, `hansard-analysis`, `health-verbose`, `health-json`, `health-critical`, `backup-prod`
- `deploy/Makefile` - Remove `clean-tests`, `corpus-backup`, `corpus-restore`, `corpus-list`
- `deploy/help.mk` - Delete file (remove all `help-*` targets)
- `utils/help.mk` - Delete file (remove all `help-*` targets)

### Phase 6 UI Modifications
- `frontend/src/components/wizard/SourceSelector.vue` - Remove placeholder, add path hint, convert colors
- `frontend/src/components/wizard/CorpusWizard.vue` - Convert step indicators and buttons to monochrome
- `frontend/src/components/wizard/RequirementsChecker.vue` - Convert toggle and button styles
- `frontend/src/components/wizard/EmbeddingConfig.vue` - Convert form styling
- `frontend/src/components/wizard/FilterConfig.vue` - Convert card and button styles
- `frontend/src/components/wizard/BuildProgress.vue` - Convert progress indicators
- `frontend/src/components/wizard/ReviewConfig.vue` - Convert summary styling

## Acceptance Criteria

1. No `VALIDATION_*` env vars in codebase
2. No `VITE_FEEDBACK_AI_ASSISTED_ENABLED` env var in codebase
3. No `VITE_FEEDBACK_SIMPLE_ENABLED`, `VITE_FEEDBACK_ENHANCED_ENABLED`, `VITE_FEEDBACK_SKIP_ENABLED` in .env files
4. No `MANIFEST_CONTEXT_ENABLED` env var in codebase
5. Feedback type visibility configurable via Corpus Wizard
6. Feedback config stored in manifest.json
7. Frontend reads feedback config from API, not env vars
8. Telemetry env vars documented as system-level overrides
9. Build metadata captured during corpus wizard builds
10. Test Target box displays build information (machine specs, duration, processing mode)
11. Makefile contains only essential targets (no redundant corpus/health/help targets)
12. No `help-*` detailed help targets remain
13. Wizard UI uses monochrome color scheme (no blue, green, or red colors)
14. Directory input has no default placeholder value
15. Directory input includes hint text for path format guidance
16. Wizard styling matches main application design language

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing validation workflows | Feature is already disabled in prod/dev; low impact |
| Build-time vs runtime config mismatch | Add API endpoint for frontend to fetch config at runtime |
| Migration complexity | Implement env var fallback during transition |

## Timeline
- Phase 1: 1 day (remove validation)
- Phase 2: 2 days (feedback wizard integration)
- Phase 3: 0.5 day (telemetry documentation)
- Phase 4: 1.5 days (build metadata + UI enhancement)
- Phase 5: 0.5 day (Makefile simplification)
- Phase 6: 1 day (wizard UI redesign)

## References
- Previous change: `move-inter-rater-to-wizard`
- Related docs: `docs/configuration.md`, `docs/inter_rater.md`
- Related components: `TestTargetBox.vue`, `VectorStoreInfo.vue`
