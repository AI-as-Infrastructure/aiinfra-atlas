# ATLAS Configuration

ATLAS uses environment-specific configuration files to manage settings across development, staging, and production environments. This document explains how to configure ATLAS using the environment file system.

## Configuration File Structure

ATLAS expects environment files to be located in the `config/` directory with the following naming convention:

- `.env.development` - Development environment
- `.env.staging` - Staging environment  
- `.env.production` - Production environment

The application automatically loads the appropriate configuration based on the `ENVIRONMENT` variable set during deployment.

## Getting Started

### 1. Create Your Environment Files

Start by copying the template file and creating environment-specific configurations:

```bash
# Copy template to create development configuration
cp config/.env.template config/.env.development

# Copy template for staging
cp config/.env.template config/.env.staging

# Copy template for production
cp config/.env.template config/.env.production
```

### 2. Customize Each Environment

Edit each file to match your environment requirements. See the sections below for environment-specific recommendations.

## Core Configuration Sections

### Application Identity

```bash
# ATLAS Version and identification
ATLAS_VERSION="1.0.0"
LAST_MODIFIED="July 2025"
VITE_SITE_TITLE="ATLAS Hansard"
ENVIRONMENT=development  # development, staging, or production
```

### API and Frontend Configuration

```bash
# Frontend configuration
VITE_API_URL=https://localhost/api  # Adjust for each environment
VITE_LOG_LEVEL=debug               # debug, info, warn, error, silent

# Backend configuration  
BACKEND_LOG_LEVEL=debug            # debug, info, warn, error, silent
PYTHON_VERSION="3.10"             # Required Python version
```

### Vector Store and Retrieval Configuration

```bash
# Test target defines the LLM and retrieval configuration
TEST_TARGET=k40_claude4            # See backend/targets/ for options

# Retriever module for document retrieval
RETRIEVER_MODULE=hansard_retriever

# Embedding model for vector store
EMBEDDING_MODEL=Livingwithmachines/bert_1890_1900

# Vector store settings
CHROMA_PERSIST_DIRECTORY="backend/targets/chroma_db"
CHROMA_COLLECTION_NAME="blert_1000"

# Multi-corpus support
MULTI_CORPUS_VECTORSTORE=True
MULTI_CORPUS_METADATA="1901_au,1901_nz,1901_uk"

# Retrieval size limits
LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS=500
LARGE_RETRIEVAL_SIZE_ALL_CORPUS=200
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
# Toggle authentication on/off
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

### Performance and Scaling Configuration

```bash
# Worker configuration
GUNICORN_WORKERS=6                 # Adjust based on server cores
LLM_THREAD_POOL_WORKERS=10        # Concurrent LLM processing
GUNICORN_TIMEOUT=300               # Request timeout in seconds

# Memory limits
LLM_MAX_CONCURRENT=20              # Max concurrent LLM requests
LLM_MAX_RESPONSE_TOKENS=4000       # Max tokens per response
GUNICORN_MAX_WORKER_MEMORY_MB=1800 # Memory limit per worker

# Rate limiting
RATE_LIMIT_PER_MINUTE=240          # Requests per minute per user
LLM_REQUEST_DELAY_MS=1000          # Delay between LLM requests
```

### Redis Configuration

```bash
# Redis for session management and concurrent users
REDIS_PASSWORD="<DEFAULT>"
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/1
REDIS_MAX_CONNECTIONS=100
REDIS_MAX_MEMORY_MB=1024
```

### Observability and Monitoring

```bash
# Telemetry settings
TELEMETRY_ENABLED=true             # Enable/disable telemetry
PHOENIX_PROJECT_NAME=ATLAS-Dev

# Phoenix Spaces Configuration
# Created by AIINFRA (https://aiinfra.anu.edu.au) - configure for your own Phoenix space
# PHOENIX_SPACE_ID: AIINFRA project space used across ATLAS deployments
PHOENIX_SPACE_ID=aiinfra
PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"
PHOENIX_API_KEY="<DEFAULT>"
PHOENIX_CLIENT_HEADERS="Authorization=Bearer <DEFAULT>"

# OpenTelemetry configuration
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer <DEFAULT>"
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_RESOURCE_ATTRIBUTES="service.name=atlas,project.name=ATLAS-Dev"
```

**Phoenix Spaces Architecture:**
- **Space = Organizational Boundary**: A Phoenix space provides isolation for your research project
- **Projects within Space**: Different environments use different project names:
  - `ATLAS-Dev`, `ATLAS-Staging`, `ATLAS-Prod` (example naming)
- **Shared AIINFRA Space**: Keep `PHOENIX_SPACE_ID=aiinfra` so all ATLAS variants (including Hansard and Darwin) report to the same organizational boundary
- **Authentication**: Use Bearer token authentication obtained from Phoenix Cloud settings
- **Finding Your Space**: Log into Phoenix Cloud and check the URL structure: `https://app.phoenix.arize.com/s/{space-id}/projects`
- **Getting Started**: Create a space at https://app.phoenix.arize.com and generate API keys from settings

### Feedback and UI Features

```bash
# Feedback system toggles
VITE_FEEDBACK_SIMPLE_ENABLED=true
VITE_FEEDBACK_ENHANCED_ENABLED=true
VITE_FEEDBACK_AI_ASSISTED_ENABLED=true
VITE_FEEDBACK_SKIP_ENABLED=true

# Session validation
VALIDATION_ENABLED=true
VALIDATION_LLM_MODE=alternate      # "default" or "alternate"
VALIDATION_LLM_DEFAULT=gpt-4o
VALIDATION_LLM_ALTERNATE=claude-3-5-sonnet-20241022
```

## Environment-Specific Recommendations

### Development Environment

For local development, focus on debugging and ease of use:

```bash
# Development-friendly settings
ENVIRONMENT=development
VITE_LOG_LEVEL=debug
BACKEND_LOG_LEVEL=debug
TELEMETRY_ENABLED=true             # Optional for development
VITE_USE_COGNITO_AUTH=false        # Disable auth for easier testing
GUNICORN_WORKERS=2                 # Fewer workers for local machine
VITE_API_URL=http://localhost:8000/api
```

### Staging Environment

For staging, mirror production but with additional debugging:

```bash
# Staging settings
ENVIRONMENT=staging
VITE_LOG_LEVEL=info
BACKEND_LOG_LEVEL=info
TELEMETRY_ENABLED=true
VITE_USE_COGNITO_AUTH=false        # Often disabled for load testing
GUNICORN_WORKERS=6                 # Match production sizing
VITE_API_URL=https://staging.example.com/api
```

### Production Environment

For production, prioritize performance and security:

```bash
# Production settings
ENVIRONMENT=production
VITE_LOG_LEVEL=warn
BACKEND_LOG_LEVEL=warn
TELEMETRY_ENABLED=true
VITE_USE_COGNITO_AUTH=true         # Enable authentication
GUNICORN_WORKERS=8                 # Full worker count
RATE_LIMIT_PER_MINUTE=120          # Stricter rate limiting
VITE_API_URL=https://atlas.example.com/api
```

## Test Targets

Test targets define the LLM provider, model, and retrieval configuration. Available targets are located in `backend/targets/`. Common targets include:

- `k40_claude4` - Claude 4 with 40-document retrieval
- `k30_openai4` - OpenAI GPT-4 with 30-document retrieval  
- `k20_google_gemini` - Google Gemini with 20-document retrieval

Each target file defines:
- LLM provider and model
- Retrieval parameters (search_k, search_type)
- Memory and performance settings
- System prompts

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
- Monitor for abuse patterns

## Validation and Testing

### Verify Configuration
Use the environment check command:
```bash
make c  # Check Python environment and configuration
```

### Test Each Environment
- Development: `make b` then `make f`
- Staging: `make sr` 
- Production: `make p`

### Load Testing Configuration
For load testing, ensure:
```bash
VITE_USE_COGNITO_AUTH=false        # Disable auth for load tests
BACKEND_LOG_LEVEL=warn             # Reduce log noise
TELEMETRY_ENABLED=true             # Monitor performance
```

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
- Solution: Ensure `PHOENIX_SPACE_ID=aiinfra` is set in your environment file and `PHOENIX_COLLECTOR_ENDPOINT` uses the `/s/aiinfra` path format
- Error: 401/403 authentication errors against Phoenix
- Solution: Verify your API key has write access to the `aiinfra` space in Phoenix Cloud settings. Generate a new space-specific key if needed.
- Error: Traces appearing in legacy endpoint instead of space
- Solution: Confirm `PHOENIX_COLLECTOR_ENDPOINT` is `https://app.phoenix.arize.com/s/aiinfra` (not the legacy `/v1/traces` URL)

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
  - `compress` (optional, boolean) — when `true`, returns `application/gzip` (`.json.gz`)

Example:

```bash
curl -L "http://localhost:8000/api/configuration/export?config_name=Demo&description=Research%20baseline&compress=true" \
  -o atlas-config.json.gz
```

### Import Endpoint

- `POST /api/configuration/import` (multipart form with `file`)
- Input limit: 10MB JSON file
- Applies corpus, target, and system settings with backup + diff + rollback safety

Example:

```bash
curl -X POST "http://localhost:8000/api/configuration/import" \
  -F "file=@atlas-config.json"
```

### Validate Endpoint

- `POST /api/configuration/validate` (multipart form with `file`)
- Validates structure/resources/version without applying changes
- Returns `valid`, `errors`, and `warnings`

### Configuration Schema Reference (v1.0)

Top-level structure:

```json
{
  "atlas_config_version": "1.0",
  "exported_at": "2026-02-17T00:00:00",
  "atlas_version": "1.0.0",
  "config_name": "My Configuration",
  "description": "Optional description",
  "corpus": {},
  "test_target": {},
  "system": {}
}
```

Notes:
- Empty/null fields are pruned during export to reduce payload size
- Sensitive system keys (tokens/passwords/secrets) are excluded from export

### Validation Rules

- JSON must parse successfully
- Required top-level structure must be present
- Version compatibility must pass (`atlas_config_version`)
- Referenced resources (paths/URLs/models) are validated and reported as warnings/errors
- Import API is rate-limited for safety

### Version Compatibility and Migration Guidance

- Current export schema version: `1.0`
- Always validate older exports before import using `/api/configuration/validate`
- For future schema updates, treat migration as:
  1. Validate old payload
  2. Transform to new schema shape
  3. Re-validate
  4. Import and confirm diff output

### Troubleshooting Export/Import

- `400 Invalid JSON file format`: file is malformed JSON
- `413 Configuration file too large`: file exceeds 10MB
- `429 Too many import attempts`: wait for rate-limit window to reset
- `207 Multi-Status`: import partially failed; inspect `errors`, `warnings`, `backup_path`, `diff`
- If import fails, restore from `backup_path` recorded in response

### Example Configuration Usage

- Use wizard export to capture a known-good corpus/target/system baseline
- Commit sanitized example exports to your internal runbooks (never include secrets)
- Use validate endpoint in CI-style pre-checks before applying imports in shared environments

## Advanced Configuration

### Custom Test Targets
Create new test targets in `backend/targets/` by copying existing ones and modifying:
- LLM provider and model
- Retrieval parameters
- System prompts
- Performance settings

### Custom Vector Stores
Build new vector stores using:
```bash
make vs  # Create vector store with current EMBEDDING_MODEL
```

### Multi-Environment Deployment
Use different configurations for blue-green deployments or A/B testing by creating additional environment files and adjusting the `ENVIRONMENT` variable.

---

For additional help with configuration, see the [troubleshooting guide](troubleshooting.md) or consult the individual component documentation.