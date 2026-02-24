# ATLAS Configuration

ATLAS uses a layered configuration system. Corpus settings are managed by the wizard and stored in `corpus_active.json`; infrastructure settings (API keys, Redis, telemetry, authentication) live in environment files.

## Configuration Architecture

| Setting type | Managed by | Stored in | To change |
|---|---|---|---|
| Corpus (embedding model, chunk size, collection, filters) | Wizard | `backend/corpus/manifest.json`, `corpus_active.json` | Rebuild via wizard |
| LLM target (provider, model, search_k) | Wizard or manual | `backend/targets/{target}.txt` | Wizard target step, or edit file |
| API keys, Redis, telemetry, auth | Manual | `config/.env.{environment}` | Edit `.env` file |
| Runtime toggles (telemetry, inter-rater) | System Mode UI or API | `config/system_settings.json` | UI toggle or `POST /api/system/configuration` |

### Precedence

1. `corpus_active.json` (corpus settings - created by deploy mode from manifest data)
2. Test target file (LLM and search parameters)
3. Environment variables from `.env.{environment}`
4. `config/system_settings.json` (runtime toggles)
5. Built-in defaults

## Environment File Structure

ATLAS expects environment files in the `config/` directory:

- `.env.development` - Development environment
- `.env.staging` - Staging environment
- `.env.production` - Production environment

The application loads the appropriate file based on the `ENVIRONMENT` variable.

### Getting Started

```bash
# Copy template to create development configuration
cp config/.env.template config/.env.development
```

## Environment File Settings

These settings belong in `.env` files. Corpus-specific settings (embedding model, collection name, chunk size, filters) should **not** be set here; they are managed by the wizard.

### Application Identity

```bash
ATLAS_VERSION="1.0.0"
LAST_MODIFIED="July 2025"
VITE_SITE_TITLE="ATLAS"
ENVIRONMENT=development  # development, staging, or production
```

### API and Frontend Configuration

```bash
# Frontend
VITE_API_URL=https://localhost/api
VITE_LOG_LEVEL=debug               # debug, info, warn, error, silent

# Backend
BACKEND_LOG_LEVEL=debug
PYTHON_VERSION="3.10"
```

### LLM Provider Configuration

```bash
# API Keys (replace <DEFAULT> with actual keys)
OPENAI_API_KEY="<DEFAULT>"
ANTHROPIC_API_KEY="<DEFAULT>"
GOOGLE_API_KEY="<DEFAULT>"

# AWS Bedrock (optional)
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID="<DEFAULT>"
AWS_SECRET_ACCESS_KEY="<DEFAULT>"

# Ollama (optional)
OLLAMA_ENDPOINT="http://localhost:11434"
```

### Authentication Configuration

```bash
VITE_USE_COGNITO_AUTH=false        # Set to true for production

# AWS Cognito settings (when authentication is enabled)
VITE_COGNITO_REGION="<DEFAULT>"
VITE_COGNITO_DOMAIN="<DEFAULT>"
VITE_COGNITO_USERPOOL_ID="<DEFAULT>"
VITE_COGNITO_CLIENT_ID="<DEFAULT>"
VITE_COGNITO_REDIRECT_URI="<DEFAULT>"
VITE_COGNITO_LOGOUT_URL="<DEFAULT>"
VITE_COGNITO_OAUTH_SCOPE="openid email profile"
```

### Performance and Scaling

```bash
GUNICORN_WORKERS=6
LLM_THREAD_POOL_WORKERS=10
GUNICORN_TIMEOUT=300
LLM_MAX_CONCURRENT=20
LLM_MAX_RESPONSE_TOKENS=4000
GUNICORN_MAX_WORKER_MEMORY_MB=1800
RATE_LIMIT_PER_MINUTE=240
LLM_REQUEST_DELAY_MS=1000
```

### Redis Configuration

```bash
REDIS_PASSWORD="<DEFAULT>"
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/1
REDIS_MAX_CONNECTIONS=100
REDIS_MAX_MEMORY_MB=1024
```

### Observability and Monitoring

```bash
TELEMETRY_ENABLED=true
PHOENIX_PROJECT_NAME=ATLAS-Dev

# Phoenix Spaces Configuration
PHOENIX_SPACE_ID=aiinfra
PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"
PHOENIX_API_KEY="<DEFAULT>"
PHOENIX_CLIENT_HEADERS="Authorization=Bearer <DEFAULT>"

# OpenTelemetry
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <DEFAULT>"
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_RESOURCE_ATTRIBUTES="service.name=atlas,project.name=ATLAS-Dev"
```

### Feedback and UI Features

```bash
VITE_FEEDBACK_SIMPLE_ENABLED=true
VITE_FEEDBACK_ENHANCED_ENABLED=true
VITE_FEEDBACK_AI_ASSISTED_ENABLED=true
VITE_FEEDBACK_SKIP_ENABLED=true
VALIDATION_ENABLED=true
VALIDATION_LLM_MODE=alternate
VALIDATION_LLM_DEFAULT=gpt-4o
VALIDATION_LLM_ALTERNATE=claude-3-5-sonnet-20241022
```

## Wizard-Managed Configuration

These settings are controlled by the corpus wizard and stored in `backend/corpus/`. Do not set them in `.env` files.

### What the Wizard Manages

| Setting | Stored in | Notes |
|---|---|---|
| Embedding model | `manifest.json` → `embedding_model.id` | Selected during wizard build |
| Collection name | `manifest.json` → `vector_store.collection_name` | Auto-generated from corpus name |
| Chunk size / overlap | `manifest.json` → `chunk_size`, `chunk_overlap` | Set during wizard build |
| Corpus filters | `manifest.json` → `fields.corpus.values` | Discovered from directory structure |
| Retriever module | `corpus_active.json` → `retriever_module` | Auto-generated adapter |
| Chroma persist directory | `corpus_active.json` | Points to `backend/corpus/chroma_db` |
| BM25 corpus path | `corpus_active.json` | Points to `backend/corpus/bm25_corpus.jsonl` |

### Changing Corpus Settings

To change embedding model, chunk size, filters, or other corpus settings:
1. Return to Configure Mode (requires server restart from Deploy Mode)
2. Open the Corpus Wizard
3. Rebuild the corpus with new settings
4. Enter Deploy Mode

### corpus_active.json

Created by deploy mode from manifest data. This is the central runtime configuration for corpus settings. The backend reads it on startup to configure the retriever, collection, and filters.

Example structure:
```json
{
  "retriever_module": "Test33_adapter",
  "chroma_collection_name": "test33",
  "chroma_persist_directory": "backend/corpus/chroma_db",
  "embedding_model": "Livingwithmachines/bert_1890_1900",
  "bm25_corpus": "backend/corpus/bm25_corpus.jsonl",
  "search_type": "hybrid"
}
```

## Test Targets

Test targets define the LLM provider, model, and search parameters. They are stored in `backend/targets/` as `.txt` files. The wizard can generate these, or you can create them manually.

See [Test Targets Documentation](test_targets.md) for details.

## Environment-Specific Recommendations

### Development

```bash
ENVIRONMENT=development
VITE_LOG_LEVEL=debug
BACKEND_LOG_LEVEL=debug
TELEMETRY_ENABLED=false
VITE_USE_COGNITO_AUTH=false
GUNICORN_WORKERS=2
VITE_API_URL=http://localhost:8000/api
```

### Staging

```bash
ENVIRONMENT=staging
VITE_LOG_LEVEL=info
BACKEND_LOG_LEVEL=info
TELEMETRY_ENABLED=true
VITE_USE_COGNITO_AUTH=false
GUNICORN_WORKERS=6
VITE_API_URL=https://staging.example.com/api
```

### Production

```bash
ENVIRONMENT=production
VITE_LOG_LEVEL=warn
BACKEND_LOG_LEVEL=warn
TELEMETRY_ENABLED=true
VITE_USE_COGNITO_AUTH=true
GUNICORN_WORKERS=8
RATE_LIMIT_PER_MINUTE=120
VITE_API_URL=https://atlas.example.com/api
```

## Configuration Export and Import

ATLAS supports full configuration portability through API endpoints and the corpus wizard UI.

### What Export Includes

- Corpus configuration (active corpus metadata, source and embedding/retrieval settings)
- Test target configuration (provider, model, retrieval/search settings)
- System settings (runtime toggles such as telemetry and inter-rater)
- Export metadata (`atlas_config_version`, `exported_at`, `atlas_version`, `config_name`, `description`)

### Export Endpoint

- `GET /api/configuration/export`
- Query parameters:
  - `config_name` (optional)
  - `description` (optional)
  - `compress` (optional, boolean) -- when `true`, returns `application/gzip` (`.json.gz`)

Example:

```bash
curl -L "http://localhost:8000/api/configuration/export?config_name=Demo&description=Research%20baseline&compress=true" \
  -o atlas-config.json.gz
```

### Import Endpoint

- `POST /api/configuration/import` (multipart form with `file`)
- Input limit: 10MB JSON file
- Applies corpus, target, and system settings with backup + diff + rollback safety

```bash
curl -X POST "http://localhost:8000/api/configuration/import" \
  -F "file=@atlas-config.json"
```

### Validate Endpoint

- `POST /api/configuration/validate` (multipart form with `file`)
- Validates structure/resources/version without applying changes
- Returns `valid`, `errors`, and `warnings`

### Troubleshooting Export/Import

- `400 Invalid JSON file format`: file is malformed JSON
- `413 Configuration file too large`: file exceeds 10MB
- `429 Too many import attempts`: wait for rate-limit window to reset
- `207 Multi-Status`: import partially failed; inspect `errors`, `warnings`, `backup_path`, `diff`
- If import fails, restore from `backup_path` recorded in response

## Security Considerations

### API Keys
- Replace all `<DEFAULT>` placeholders with actual API keys
- Use environment-specific keys (separate keys for dev/staging/prod)
- Store production keys securely (AWS Secrets Manager, etc.)

### Authentication
- Enable `VITE_USE_COGNITO_AUTH=true` in production
- Configure all Cognito parameters properly
- Test authentication flow in staging before production

### Rate Limiting
- Adjust `RATE_LIMIT_PER_MINUTE` based on expected usage
- Consider stricter limits in production

## Validation and Testing

### Verify Configuration
```bash
make c  # Check Python environment and configuration
```

### Test Each Environment
- Development: `make b` then `make f`
- Staging: `make sr`
- Production: `make p`

## Common Configuration Issues

### Missing Environment File
- Error: "Required environment file not found"
- Solution: Create the appropriate `.env.{environment}` file in `config/`

### Invalid API Keys
- Error: Authentication failures with LLM providers
- Solution: Verify API keys are valid and have sufficient credits

### Port Conflicts
- Error: "Address already in use"
- Solution: Check `VITE_API_URL` and ensure ports aren't conflicting

### Memory Issues
- Error: Workers crashing or high memory usage
- Solution: Adjust `GUNICORN_WORKERS`, `LLM_MAX_CONCURRENT`, and memory limits

### Phoenix Spaces Issues
- Error: "PHOENIX_SPACE_ID not configured" or traces not appearing
- Solution: Ensure `PHOENIX_SPACE_ID=aiinfra` is set and `PHOENIX_COLLECTOR_ENDPOINT` uses the `/s/aiinfra` path format

---

For additional help, see the individual component documentation or the [Development Guide](development.md).
