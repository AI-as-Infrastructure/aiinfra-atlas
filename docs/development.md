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
- **Git with LFS** (for large model files)
- **Redis** (for caching and async operations)

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

**Git LFS:**
```bash
# Ubuntu/Debian
sudo apt install git-lfs

# macOS
brew install git-lfs

# Initialize in repository
git lfs install
```

## Initial Setup

### 1. Clone Repository

```bash
git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas.git
cd aiinfra-atlas
git lfs pull
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

### 3. Backend Setup

```bash
# Check Python environment
make c

# Set up virtual environment and install dependencies
cd backend
python3.10 -m venv .venv
source .venv/bin/activate
pip install -r ../config/requirements.txt

# Return to project root
cd ..
```

### 4. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

### 5. Vector Store Setup

Generate the vector store and retriever (required for first run):

```bash
# Create vector store (this will take some time)
make vs

# Generate retriever
make r
```

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

### Test Targets

ATLAS uses "test targets" to configure LLM and retrieval settings:

```bash
# Current test target (defines LLM model and parameters)
TEST_TARGET=k40_claude4

# Vector store configuration
RETRIEVER_MODULE=hansard_retriever
CHROMA_COLLECTION_NAME=blert_1000
```

See [Test Targets Documentation](test_targets.md) for more details.

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

**Vector Store Issues:**
1. Ensure vector store was built (`make vs`)
2. Check retriever was generated (`make r`)
3. Verify Chroma database exists

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
pip install -r ../config/requirements.txt
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

**5. Vector Store Missing:**
```bash
# Rebuild vector store and retriever
make vs
make r
```

**6. LLM API Issues:**
```bash
# Verify API keys in environment file
grep -E "(ANTHROPIC|OPENAI|GOOGLE)_API_KEY" config/.env.development

# Test API key directly
curl -H "Authorization: Bearer your-api-key" \
  https://api.anthropic.com/v1/messages
```

### Log Locations

- **Backend logs**: Terminal output from `make b`
- **Frontend logs**: Browser console and terminal output from `make f`
- **Redis logs**: `sudo journalctl -u redis-server` (Linux)

### Performance Considerations

- **Vector Store Size**: Large vector stores slow startup times
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
3. **Handle errors gracefully**: Implement proper error handling
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