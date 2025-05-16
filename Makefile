.PHONY: dev staging prod setup-env frontend frontend-restart destroy-dev

# ATLAS Development Workflow
#
# Main targets:
#   make dev          - Start the complete development environment (backend + frontend)
#   make frontend     - Start only the Frontend development server
#
# Utility targets:
#   make frontend-restart - Restart only the frontend development server
#   make destroy-dev      - Remove all development containers and dependencies

# Set up environment based on ENVIRONMENT in .env
setup-env:
	chmod +x ./config/setup_env.sh
	./config/setup_env.sh

# Development environment (starts backend only)
dev:
	@echo "Setting ENVIRONMENT=dev in .env file..."
	@case "$$(uname)" in \
		Darwin) sed -i '' 's/^ENVIRONMENT=.*/ENVIRONMENT=dev/' ./config/.env || echo "ENVIRONMENT=dev" >> ./config/.env ;; \
		*) sed -i 's/^ENVIRONMENT=.*/ENVIRONMENT=dev/' ./config/.env || echo "ENVIRONMENT=dev" >> ./config/.env ;; \
	esac
	make setup-env
	./frontend/generate-logout.sh .env
	@echo "\n🚀 Starting Backend server (Flask, Redis, Nginx)..."
	./deploy/dev/dev.sh
	@echo "\n✅ Backend started successfully!"
	@echo "   Backend API: https://localhost:5001"
	@echo "   To start the frontend, open a new terminal and run: make frontend"


# Starts ONLY the Frontend development server (use 'make dev' for complete environment).
frontend:
	@echo "Starting Frontend development server (backend not included)..."
	# Use our custom script that ensures environment variables are properly set up
	# Disable auto-opening the browser by setting BROWSER=none
	cd frontend && BROWSER=none ./start-with-env.sh &
	# Wait a few seconds for the server to boot up
	sleep 5
	# Open the secure URL (adjust the command for your OS)
	if command -v xdg-open >/dev/null; then \
		xdg-open https://localhost; \
	elif command -v open >/dev/null; then \
		open https://localhost; \
	else \
		echo "Please open https://localhost in your browser."; \
	fi

# Restarts ONLY the Frontend development server (useful during frontend-only development).
frontend-restart:
	@echo "Stopping any process running on port 3001 (Frontend dev server)..."
	@lsof -ti :3001 | xargs -r kill -9 || true
	@echo "Building Frontend application..."
	cd frontend && ./build-with-env.sh
	@echo "Starting Frontend development server..."
	# Use our custom script that ensures environment variables are properly set up
	# Disable auto-opening the browser by setting BROWSER=none
	cd frontend && BROWSER=none ./start-with-env.sh &
	@echo "Frontend server restarted successfully!"

# Destroys the environment by removing all containers and local dependencies.
destroy-dev:
	@echo "Stopping Redis container..."
	@docker rm -f redis-dev || true
	@echo "Stopping Nginx container..."
	@docker rm -f nginx-dev || true
	@echo "Stopping any process running on port 3001 (Frontend dev server)..."
	@lsof -ti :3001 | xargs -r kill -9 || true
	@echo "Stopping any process running on port 5001 (Backend server)..."
	@lsof -ti :5001 | xargs -r kill -9 || true
	@echo "Removing virtual environment and Node modules..."
	@rm -rf .venv
	@rm -rf frontend/node_modules
	@rm -rf frontend/package-lock.json
	@rm -rf frontend/public/logout.html
	@echo "Cleaning up .span_cache directory..."
	@rm -rf .span_cache/* || true
	@echo "Removing Hugging Face cache..."
	@rm -rf ~/.cache/huggingface/* || true

# Ansible targets
.PHONY: staging destroy-staging

# Dependencies management
.PHONY: lock

# Generates a locked requirements file with exact versions
# NOTE: This creates a machine-specific lock file that works for your local dev environment
# and staging Docker deployment. Other developers may need to generate their own lock file.
lock:
	@echo "CAUTION: This will generate a machine-specific requirements.lock file"
	@echo "This is intended for YOUR development and staging environments only"
	@echo "Generating requirements.lock file with Python $${PYTHON_VERSION}..."
	./deploy/dev/generate-lockfile.sh
	@echo "Lock file generated successfully for your specific environment."

# Helps other developers check their Python environment
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
