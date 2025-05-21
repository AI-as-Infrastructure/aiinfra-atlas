###############################################################################
# ATLAS Makefile
#
# This Makefile provides commands for development, building, and deployment of ATLAS.
###############################################################################

#------------------------------------------------------------------------------
# Development Environment Commands
#------------------------------------------------------------------------------

# Start the backend development environment (FastAPI server)
# This includes database setup, environment initialization, and running the API server
.PHONY: db
db:
	bash deploy/dev/dev.sh

# Start the frontend development server (Vue.js)
# This runs the Vue development server on port 5173 and opens it in a browser
.PHONY: df
df:
	@echo "Starting ATLAS frontend development server..."
	cd frontend && \
		export NVM_DIR="$$HOME/.nvm"; \
		if [ ! -s "$$NVM_DIR/nvm.sh" ]; then \
			echo "Error: nvm is not installed. Please install nvm (https://github.com/nvm-sh/nvm) and run 'nvm install' in the frontend directory."; \
			exit 1; \
		fi; \
		. "$$NVM_DIR/nvm.sh"; \
		nvm use; \
		([ -d node_modules ] || npm install) && npm run dev

# Destroy the development environment
# This stops all running servers, removes containers, and cleans up dependencies
.PHONY: dd
dd:
	@echo "Stopping any process running on port 8000 (FastAPI server)..."
	@lsof -ti :8000 | xargs -r kill -9 || true
	@echo "Removing virtual environment..."
	@rm -rf .venv
	@echo "Removing node_modules and package-lock.json from project root and frontend/ ..."
	@rm -rf node_modules package-lock.json
	@rm -rf frontend/node_modules frontend/package-lock.json
	@rm -rf frontend/dist
	@echo "Removed frontend/dist directory"
	@echo "FastAPI dev environment destroyed."

#------------------------------------------------------------------------------
# Build and Deployment Commands
#------------------------------------------------------------------------------

# Build frontend for staging environment
.PHONY: build-staging
build-staging:
	@echo "Building ATLAS frontend for staging environment..."
	cd vue && npm run build:staging

# Build frontend for production environment
.PHONY: build-production
build-production:
	@echo "Building ATLAS frontend for production environment..."
	cd vue && npm run build:production

#------------------------------------------------------------------------------
# Dependencies Management
#------------------------------------------------------------------------------

.PHONY: lock

# Generates a locked requirements file with exact versions
# NOTE: This creates a machine-specific lock file that works for your local dev environment
# and staging Docker deployment. Other developers may need to generate their own lock file.
lock:
	@echo "CAUTION: This will generate a machine-specific requirements.lock file"
	@echo "Generating requirements.lock file with Python $${PYTHON_VERSION}..."
	./config/generate-lockfile.sh
	@echo "Lock file generated successfully for your specific environment."

# Check your Python environment
.PHONY: check-env

check-env:
	@echo "Checking Python environment..."
	@echo "Recommended: Python 3.10.12 (app developed and tested with this version)"
	@echo "Current: $$(python3 --version)"
	@echo ""
	@echo "The app may work with newer Python versions (3.11, 3.12), but for"
	@echo "maximum compatibility and consistency, Python 3.10.12 is recommended."
	@echo ""
	@echo "IMPORTANT: The requirements.lock file was generated on Pop_OS! with NVIDIA GPU support."
	@echo "If you are using a different system (especially without NVIDIA GPU),"
	@echo "the lock file may not work for you due to platform-specific dependencies."
	@echo ""
	@echo "If using a different system or Python version:"
	@echo "1. You may need to generate your own requirements.lock file with 'make lock'"
	@echo "2. Or install directly from requirements.txt if the lock file doesn't work"

#------------------------------------------------------------------------------
# Data Management Commands
#------------------------------------------------------------------------------

# Create the Chroma vector store using the script in create/
.PHONY: store
store:
	@echo "Creating Chroma vector store..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@bash -c 'set -e && \
		. .venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r config/requirements.lock && \
		python create/create_hansard_retriever.py'
	@echo "\nChroma vector store created in backend/targets/chroma_db"
	@echo "\nTo distribute this database:"
	@echo "1. Copy the database and statistics file to backend/targets/:"
	@echo "   mkdir -p backend/targets/chroma_db"
	@echo "   cp -r create/output/chroma_db/* backend/targets/chroma_db/"
	@echo "   cp create/output/blert_1000.txt backend/targets/"
	@echo "2. Commit and push with Git LFS"
	@echo "\nNote: The database will be used from the location specified by CHROMA_PERSIST_DIRECTORY in config/.env.development"

# Generate the retriever: ensure venv, install deps, run script
retriever:
	bash -c 'if [ ! -d ".venv" ]; then python3 -m venv .venv; fi && \
		. .venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r config/requirements.lock && \
		python create/create_hansard_retriever.py'

# === STAGING DEPLOYMENT TARGETS ===
.PHONY: sl dsl dslf

# Deploy to local staging environment
sl: ## Deploy to staging on localhost
	@echo "Deploying to local staging environment..."
	@chmod +x deploy/staging/staging_localhost.sh
	@./deploy/staging/staging_localhost.sh

# Basic cleanup of local staging deployment (without removing code)
dsl: ## Basic cleanup of local staging deployment
	@echo "Performing basic cleanup of local staging deployment..."
	@sudo systemctl stop gunicorn || true
	@sudo systemctl disable gunicorn || true
	@sudo rm -f /etc/systemd/system/gunicorn.service || true
	@sudo rm -f /etc/nginx/sites-enabled/atlas || true
	@sudo rm -f /etc/nginx/sites-available/atlas || true
	@sudo systemctl restart nginx || true
	@echo "✅ Basic cleanup completed (code at /opt/atlas is preserved)"

# Full cleanup of local staging deployment (including code removal)
dslf: ## Full cleanup of local staging deployment
	@echo "Performing full cleanup of local staging deployment..."
	@sudo systemctl stop gunicorn || true
	@sudo systemctl disable gunicorn || true
	@sudo rm -f /etc/systemd/system/gunicorn.service || true
	@sudo rm -f /etc/nginx/sites-enabled/atlas || true
	@sudo rm -f /etc/nginx/sites-available/atlas || true
	@sudo systemctl restart nginx || true
	@echo "Clearing npm cache..."
	@cd frontend && npm cache clean --force || true
	@echo "Removing node_modules and package-lock.json from frontend..."
	@rm -rf frontend/node_modules frontend/package-lock.json frontend/.vite || true
	@echo "Removing frontend/dist directory..."
	@rm -rf frontend/dist || true
	@echo "Removing any generated environment files..."
	@rm -f frontend/.env || true
	@sudo rm -rf /opt/atlas || true
	@echo "Checking for any Vite cache directories..."
	@rm -rf $$HOME/.vite || true
	@rm -rf $$HOME/.cache/vite || true
	@echo "✅ Full cleanup completed (including removal of /opt/atlas and npm/node caches)"