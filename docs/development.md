# Development Environment

This guide covers setting up and working with the ATLAS development environment.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Development Workflow](#development-workflow)
- [Environment Configuration](#environment-configuration)
- [Development Tools](#development-tools)
- [Debugging](#debugging)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Python 3.10** (recommended via pyenv or system package)
- **Node.js 22.14.0** (install via nvm for version management)
- **uv** (optional but recommended for 10-100x faster dependency installation)
- **Redis** (for caching and feedback)

### Installation

**Python 3.10:**
```bash
# Via pyenv (recommended)
pyenv install 3.10.12
pyenv local 3.10.12

# Or via system package manager
sudo apt install python3.10 python3.10-venv python3.10-dev
```

**Node.js 22.14.0:**
```bash
# Install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc

# Install and use Node.js 22.14.0
nvm install 22.14.0
nvm use 22.14.0
nvm alias default 22.14.0
```

**uv (optional but recommended):**
```bash
# Install uv for 10-100x faster dependency installation
curl -LsSf https://astral.sh/uv/install.sh | sh

# Restart shell or source the environment
source $HOME/.local/bin/env

# Verify installation
uv --version

# Note: If uv is not installed, the system will automatically fall back to pip
```

**Redis:**
```bash
# Ubuntu/Debian
sudo apt install redis-server

# macOS
brew install redis

# Start Redis
sudo systemctl start redis-server  # Linux
brew services start redis           # macOS
```

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas.git
cd aiinfra-atlas
```

### 2. Environment Configuration

Create your development environment file:

```bash
cp config/.env.template config/.env.development
```

Edit `config/.env.development` with your settings:

```bash
# Core Configuration
ENVIRONMENT=development
VITE_LOG_LEVEL=debug
BACKEND_LOG_LEVEL=debug

# Development URLs
VITE_API_URL=http://localhost:8000
VITE_SITE_TITLE="ATLAS Development"

# LLM API Keys (set at least one)
ANTHROPIC_API_KEY=your-development-key
OPENAI_API_KEY=your-development-key
GOOGLE_API_KEY=your-development-key

# Development Features
TELEMETRY_ENABLED=false
VITE_USE_COGNITO_AUTH=false

# Redis (development)
REDIS_PASSWORD=dev-password
REDIS_URL=redis://:dev-password@localhost:6379/0
```

### 3. Start Development Servers

```bash
# Terminal 1: Backend (auto-detects GPU, installs dependencies)
make b

# Terminal 2: Frontend (installs npm dependencies automatically)
make f
```

### 4. Build Your First Corpus

1. Open http://localhost:5173 in your browser
2. You will land on the **System Mode** page in Configure Mode
3. Navigate to the **Corpus Wizard**
4. Follow the wizard steps:
   - Select a source directory containing your text files (or a GitHub repository)
   - Configure filters based on directory structure
   - Select embedding model and chunking parameters
   - Configure LLM test target (provider, model, search parameters)
   - Build the corpus (GPU-accelerated when available)
5. After build completes, enter **Deploy Mode** to lock configuration
6. Begin querying through the chat interface

The wizard generates all build artifacts in `backend/corpus/`, including the vector store, BM25 index, manifest, retriever adapter, and runtime configuration (`corpus_active.json`).

## Development Workflow

### Starting Development Servers

ATLAS uses a two-server development setup:

**Option 1: Separate terminals (recommended)**
```bash
# Terminal 1: Backend API server
make b

# Terminal 2: Frontend development server
make f
```

**Option 2: Background processes**
```bash
# Start backend in background
make b &

# Start frontend (foreground)
make f
```

### Accessing the Application

- **Frontend**: http://localhost:5173 (Vite dev server)
- **Backend API**: http://localhost:8000 (FastAPI)
- **API Documentation**: http://localhost:8000/docs (Swagger UI)

### Application Modes

ATLAS operates in two runtime modes:

- **Configure Mode** (default on startup): Wizard and settings are available. Build corpora, configure targets, adjust settings.
- **Deploy Mode** (one-way lock): Configuration is locked. Chat interface is active. Requires server restart to reconfigure.

The System Mode page (`ModeSelector.vue`) is the application entry point and controls mode transitions.

### Development Features

The development setup includes:

- **Hot Reloading**: Both frontend and backend reload automatically on changes
- **Debug Logging**: Verbose logging for development troubleshooting
- **API Documentation**: Interactive Swagger UI for API testing
- **CORS Enabled**: Frontend can communicate with backend during development
- **No Authentication**: Simplified setup for development (unless explicitly enabled)

## Environment Configuration

### Key Development Variables

```bash
# Environment
ENVIRONMENT=development
VITE_LOG_LEVEL=debug        # Frontend logging
BACKEND_LOG_LEVEL=debug     # Backend logging

# Development URLs
VITE_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Features
TELEMETRY_ENABLED=false     # Disable telemetry in development
VITE_USE_COGNITO_AUTH=false # Disable authentication
```

### Configuration Sources

ATLAS configuration comes from multiple sources with the following precedence:

1. **`corpus_active.json`** (created by deploy mode from wizard manifest data) - corpus settings: retriever module, collection name, embedding model, filters
2. **Test target files** (`backend/targets/{target}.txt`) - LLM provider, model, search parameters
3. **`.env.{environment}` files** - API keys, Redis, telemetry, authentication, infrastructure settings

Corpus settings (embedding model, chunk size, collection name, filters) are managed by the wizard and stored in `backend/corpus/manifest.json` and `corpus_active.json`. Do not set these in `.env` files.

See [Configuration Guide](configuration.md) for full details.

## Development Tools

### Code Quality

```bash
# Python linting and formatting (if configured)
flake8 backend/
black backend/

# Frontend linting
cd frontend
npm run lint
```

### Environment Management

```bash
# Check Python environment
make c

# Generate requirements lock file
make l

# Clean development environment
make d
```

### Database and Caching

```bash
# Redis CLI (for debugging)
redis-cli -a dev-password

# Check Redis connection
redis-cli -a dev-password ping
```

## Debugging

### Backend Debugging

**Console Logging:**
```python
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
```

**API Testing:**
- Use the Swagger UI at http://localhost:8000/docs
- Test endpoints directly with curl or Postman
- Check FastAPI logs in the terminal running `make b`

**Python Debugger:**
```python
import pdb; pdb.set_trace()  # Add breakpoint
```

### Frontend Debugging

**Browser DevTools:**
- Console logs from Vue components
- Network tab for API calls
- Vue DevTools browser extension (recommended)

**Vite Debugging:**
- Hot reload issues: Check terminal running `make f`
- Build issues: Clear node_modules and reinstall

### Common Debug Points

**API Connection Issues:**
1. Verify backend is running on port 8000
2. Check CORS configuration in backend
3. Verify `VITE_API_URL` in environment file

**LLM Issues:**
1. Check API keys are set correctly
2. Verify test target configuration
3. Check backend logs for API errors

**Corpus/Filter Issues:**
1. Ensure corpus was built via the wizard
2. Check `backend/corpus/manifest.json` exists and has filter values
3. Verify `corpus_active.json` was created by deploy mode
4. Check retriever adapter exists in `backend/corpus/`

## Testing

### Manual Testing

```bash
# Test backend API directly
curl http://localhost:8000/api/health

# Test document retrieval
curl -X POST http://localhost:8000/api/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query": "test query", "corpus_filter": "all"}'
```

### Load Testing

For performance testing against development environment:

```bash
# Run load test against local development
make lts
```

See [Load Testing Documentation](load_testing.md) for details.

## Troubleshooting

### Common Issues

**1. Port Already in Use:**
```bash
# Find and kill process using port 8000 or 5173
lsof -ti:8000 | xargs kill -9
lsof -ti:5173 | xargs kill -9
```

**2. Python Virtual Environment Issues:**
```bash
# Recreate virtual environment
rm -rf backend/.venv
cd backend
python3.10 -m venv .venv
source .venv/bin/activate
uv pip install -e "..[cpu]"  # or appropriate variant for your GPU
```

**3. Node.js Version Issues:**
```bash
# Ensure correct Node.js version
nvm use 22.14.0

# Clear npm cache if needed
npm cache clean --force
rm -rf frontend/node_modules
cd frontend && npm install
```

**4. Redis Connection Issues:**
```bash
# Check if Redis is running
redis-cli ping

# Start Redis if not running
sudo systemctl start redis-server  # Linux
brew services start redis           # macOS
```

**5. No Corpus Built:**
```bash
# Start servers and use the wizard
make b  # Terminal 1
make f  # Terminal 2
# Open http://localhost:5173 and follow the Corpus Wizard
```

**6. Filters Not Appearing:**
- Verify `backend/corpus/manifest.json` exists and contains filter values under `fields.corpus.values`
- Ensure you entered Deploy Mode after building the corpus
- Check that `corpus_active.json` was created

**7. LLM API Issues:**
```bash
# Verify API keys in environment file
grep -E "(ANTHROPIC|OPENAI|GOOGLE)_API_KEY" config/.env.development
```

### Log Locations

- **Backend logs**: Terminal output from `make b`
- **Frontend logs**: Browser console and terminal output from `make f`
- **Redis logs**: `sudo journalctl -u redis-server` (Linux)

### Performance Considerations

- **Corpus Building**: GPU provides 5-10x speedup for large corpora
- **LLM Response Times**: Development API keys may have rate limits
- **Memory Usage**: Monitor memory usage with large document retrievals

## Best Practices

### Development Workflow

1. **Start with fresh environment**: Use `make d` to clean up between sessions
2. **Use version control**: Commit frequently, use feature branches
3. **Test incrementally**: Test changes as you develop
4. **Monitor logs**: Keep backend terminal visible for error monitoring

### Environment Management

1. **Keep secrets separate**: Never commit API keys to version control
2. **Use development keys**: Separate API keys for development vs production
3. **Document changes**: Update this guide when adding new development requirements

### Code Quality

1. **Follow existing patterns**: Match the established code style
2. **Add logging**: Use appropriate log levels for debugging
3. **Handle errors explicitly**: Fail fast with clear error messages
4. **Test edge cases**: Consider error conditions and edge cases

## Next Steps

After setting up development:

1. **Explore the codebase**: Start with [Key Modules Documentation](key_modules.md)
2. **Test staging**: Deploy to [Staging Environment](staging.md) before production
3. **Read configuration docs**: Understand [Configuration Guide](configuration.md)
4. **Learn about test targets**: Read [Test Targets Documentation](test_targets.md)

For deployment to other environments, see:
- [Staging Environment](staging.md) - Local staging for testing
- [Production Deployment](production.md) - Production deployment guide
