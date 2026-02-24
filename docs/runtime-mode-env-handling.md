# Runtime Mode System

## Overview

ATLAS operates in two runtime modes that control what the user can do:

- **Configure Mode** (default on startup): Wizard and settings are accessible. Configuration can be changed.
- **Deploy Mode** (one-way lock): Configuration is locked. Chat interface is active. Server restart required to reconfigure.

The System Mode page (`ModeSelector.vue`) is the application entry point and landing page.

## Mode Lifecycle

```
Server Start
  -> Configure Mode (default)
    -> Corpus Wizard available
    -> Settings editable
    -> .env files can be updated
    -> corpus_active.json NOT yet created
  -> User clicks "Deploy"
    -> corpus_active.json created from manifest data
    -> Configuration locked
    -> Chat interface activated
  -> Deploy Mode
    -> No wizard access
    -> No settings changes
    -> Queries processed using corpus_active.json + target file
  -> Server Restart required to return to Configure Mode
```

## Environment File Handling

The mode system handles different environment files based on the `ENVIRONMENT` variable:

| Environment | File | Behaviour in Configure Mode |
|---|---|---|
| development | `config/.env.development` | Wizard updates `TEST_TARGET` and `VITE_SITE_TITLE` |
| staging | `config/.env.staging` | Same as development |
| production | `config/.env.production` | `.env` file updates are logged but may be skipped in production |

### What Gets Updated

When the wizard activates a corpus or the user enters deploy mode:

1. **`backend/corpus/corpus_active.json`** is created from manifest data with:
   - `retriever_module` - Name of the generated adapter
   - `chroma_collection_name` - ChromaDB collection name
   - `chroma_persist_directory` - Path to vector store
   - `embedding_model` - Embedding model identifier
   - `bm25_corpus` - Path to BM25 index (if hybrid)
   - `search_type` - `hybrid` or `dense`

2. **`.env.{environment}`** may be updated with:
   - `TEST_TARGET` - Active target configuration name
   - `VITE_SITE_TITLE` - Display name from corpus metadata

3. **`config/system_settings.json`** stores runtime toggles:
   - `telemetryEnabled` - Phoenix telemetry export toggle
   - `interRaterEnabled` - Inter-rater feedback workflow toggle

## Configuration Precedence

In deploy mode, the backend loads configuration in this order:

1. **`corpus_active.json`** - Corpus settings (retriever, collection, embedding model)
2. **Target file** (`backend/targets/{TEST_TARGET}.txt`) - LLM provider, model, search parameters
3. **`.env.{environment}`** - API keys, Redis, telemetry, authentication
4. **`config/system_settings.json`** - Runtime toggles
5. **Built-in defaults**

Corpus settings in `corpus_active.json` take precedence over any equivalent environment variables. This ensures the wizard's configuration cannot be accidentally overridden by stale `.env` values.

## API Endpoints

### Mode Status

`GET /api/mode`

Returns current mode and corpus information:
```json
{
  "mode": "deploy",
  "corpus_info": {
    "name": "my_corpus",
    "embedding_model": "Livingwithmachines/bert_1890_1900",
    "collection_name": "my_corpus",
    "total_documents": 206
  }
}
```

### Enter Deploy Mode

`POST /api/mode/deploy`

One-way transition. Creates `corpus_active.json` and locks configuration.

### System Configuration

`GET /api/system/configuration` - Read current toggles
`POST /api/system/configuration` - Update toggles (rate-limited)

Toggles are persisted to `config/system_settings.json` and take effect on next request (no restart needed).

## Implementation Details

### mode_manager.py

Manages mode state. Key functions:
- `get_current_mode()` - Returns `configure` or `deploy`
- `enter_deploy_mode()` - Creates `corpus_active.json`, locks mode
- `is_deploy_mode()` - Check if deployed

### config.py

On startup, loads `corpus_active.json` if it exists. Falls back to environment variables only for non-corpus settings (API keys, Redis, etc.).

### manifest_loader.py

Loads `manifest.json` from `backend/corpus/` (primary) or `backend/targets/` (fallback). Used by the mode endpoint to display corpus info.

## Frontend Integration

### ModeSelector.vue

The landing page component. Shows:
- Current mode (configure/deploy)
- Corpus information (from manifest)
- Mode transition controls
- Links to wizard (in configure mode) or chat (in deploy mode)

### Route Guards

Frontend routes enforce mode restrictions:
- Wizard routes: Only accessible in configure mode
- Chat routes: Only accessible in deploy mode (or if corpus exists)
- System Mode page: Always accessible

## Related Documentation

- [Configuration Guide](configuration.md) - Full configuration architecture
- [Key Modules](key_modules.md) - mode_manager.py and config.py details
- [Development Guide](development.md) - Development workflow with modes
