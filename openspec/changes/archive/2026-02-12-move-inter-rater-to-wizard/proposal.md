# Move Inter-Rater Configuration to Corpus Wizard

## Summary
Move inter-rater reliability settings from environment files into the corpus wizard configuration, making them corpus-specific and eliminating the redundant `INTER_RATER_PROJECT` variable.

## Problem
Currently, inter-rater configuration is stored in environment files (`.env.development`, `.env.staging`, `.env.production`):

```
INTER_RATER_ENABLED=false
INTER_RATER_PROJECT=ATLAS-Dev
INTER_RATER_MAX_RATINGS=1
INTER_RATER_SESSIONS_PER_USER=10
```

Issues with this approach:
1. **Redundant variable**: `INTER_RATER_PROJECT` duplicates `PHOENIX_PROJECT_NAME` - the inter-rater system queries the same Phoenix project as telemetry
2. **Environment-level config**: Inter-rater settings are research methodology choices that should be configurable per corpus, not per deployment environment
3. **Manual editing required**: Researchers must edit `.env` files directly to configure inter-rater studies
4. **No UI**: Settings are hidden from the corpus wizard configuration flow

## Solution
1. **Remove `INTER_RATER_PROJECT`**: Use `PHOENIX_PROJECT_NAME` directly (already the fallback behavior)
2. **Add inter-rater settings to corpus wizard**: Include in the target/system configuration step
3. **Store in manifest.json**: Persist settings with corpus metadata
4. **Backend reads from config**: Services read from corpus config, falling back to env vars for backward compatibility

## Capabilities
- `inter-rater-config`: Inter-rater settings in corpus wizard UI and manifest storage

## Dependencies
- `backend/services/inter_rater_service.py`
- `backend/services/phoenix_client.py`
- `backend/routers/corpus_wizard.py`
- `frontend/src/components/CorpusWizard.vue`
- `config/.env.template`

## Risks & Mitigations
- **Risk**: Breaking existing deployments that rely on env vars
  - **Mitigation**: Clear migration path - remove env vars, configure via wizard before next deployment
- **Risk**: Users unaware of configuration change
  - **Mitigation**: Document the change; inter-rater defaults to disabled so no unexpected behavior

## Technical Design

### Configuration Structure
Add to manifest.json under a new `inter_rater` section:

```json
{
  "metadata": { ... },
  "inter_rater": {
    "enabled": false,
    "max_ratings": 3,
    "sessions_per_user": 5
  }
}
```

### Service Changes
Update `InterRaterService` to read from corpus config only:

```python
class InterRaterService:
    def __init__(self):
        # Load from manifest only - no env var fallback
        corpus_config = self._load_corpus_config()
        inter_rater_config = corpus_config.get('inter_rater', {})

        self.enabled = inter_rater_config.get('enabled', False)
        self.max_ratings = inter_rater_config.get('max_ratings', 3)
        self.sessions_per_user = inter_rater_config.get('sessions_per_user', 5)
```

### Phoenix Client Changes
Remove `INTER_RATER_PROJECT` usage:

```python
# Before
self.project_name = os.getenv("INTER_RATER_PROJECT", os.getenv("PHOENIX_PROJECT_NAME", "atlas-telemetry"))

# After
self.project_name = os.getenv("PHOENIX_PROJECT_NAME", "atlas-telemetry")
```

### Wizard UI Addition
Add collapsible "Inter-Rater Reliability" section in the target configuration step:
- Toggle: Enable inter-rater mode
- Number input: Maximum ratings per session (1-10, default 3)
- Number input: Sessions per user (1-20, default 5)

## Validation
- Verify inter-rater functionality works with manifest-based config
- Verify wizard correctly saves inter-rater settings to manifest
- Verify `INTER_RATER_PROJECT` removal doesn't break Phoenix queries
- Verify no INTER_RATER_* env vars remain in codebase

## Implementation Order
1. Remove all `INTER_RATER_*` variables from .env files (.env.template, .env.development, .env.staging, .env.production)
2. Remove `INTER_RATER_PROJECT` from phoenix_client.py
3. Update inter_rater_service.py to read from manifest only (no env var fallback)
4. Update telemetry/api.py to remove INTER_RATER env var checks
5. Update corpus wizard backend to include inter-rater in build config
6. Update frontend wizard to add inter-rater configuration UI
7. Update documentation to reflect new configuration method
8. Update tests to remove INTER_RATER env var fixtures
