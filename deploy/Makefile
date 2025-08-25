# Deployment Makefile
# Contains targets for development, staging, and production deployment

# Variables
AWS_PROFILE ?= default
AWS_REGION ?= ap-southeast-2
STACK_NAME ?= atlas-prod
DOMAIN_NAME ?= atlas.aiinfra.org

# Development Targets
.PHONY: b f d
b: ## Start backend development server
	@./deploy/dev/scripts/start_backend.sh

f: ## Start frontend development server
	@./deploy/dev/scripts/start_frontend.sh

d: ## Destroy development environment
	@./deploy/dev/scripts/clean_dev.sh

# Production Deployment Targets
.PHONY: p dp up sp
p: ## Deploy to production (run locally on server)
	@if [ ! -f "config/.env.production" ]; then \
		echo "ERROR: config/.env.production file not found!"; \
		echo "Please create it from config/.env.development and modify as needed."; \
		exit 1; \
	fi
	@bash deploy/production/production.sh

dp: ## Delete production environment
	@./deploy/production/scripts/clean_prod.sh

up: ## Upgrade production with minimal downtime (run on server)
	@echo "🚀 Production upgrade using simple server-side approach"
	@if [ ! -f "config/.env.production" ]; then \
		echo "ERROR: config/.env.production file not found!"; \
		echo "Please ensure you're running this on the production server."; \
		exit 1; \
	fi
	@bash deploy/production/scripts/simple_upgrade.sh

upf: ## Full upgrade production with complete rebuild (run on server)
	@echo "🚀 FULL Production upgrade - complete rebuild"
	@echo "⚠️  Use this when you've changed .env.production or need complete rebuild"
	@if [ ! -f "config/.env.production" ]; then \
		echo "ERROR: config/.env.production file not found!"; \
		echo "Please ensure you're running this on the production server."; \
		exit 1; \
	fi
	@bash deploy/production/scripts/full_upgrade.sh

sp: ## Stop production environment gracefully
	@echo "🚨 WARNING: This will stop the production environment!"
	@read -p "Are you sure you want to continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "🛑 Stopping production environment gracefully..."
	@bash deploy/production/scripts/stop_production.sh

# Staging Deployment Targets
.PHONY: s ds
s: ## Deploy to local staging environment
	@echo "Deploying to local staging environment..."
	@bash deploy/staging/staging_localhost.sh

ds: ## Delete local staging environment  
	@echo "Deleting local staging environment..."
	@bash deploy/staging/scripts/clean_staging_localhost.sh

# Load Testing Targets
.PHONY: lts ltp clean-tests
# Load test setup - shared function
define setup_load_test
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing load test dependencies..."; \
		if [ ! -f "config/requirements.lock" ]; then echo "❌ Missing config/requirements.lock. Run 'make l' first."; exit 1; fi; \
		.venv/bin/pip install -r config/requirements.lock psutil; \
	fi
endef

lts: ## Run unified load test against staging (30 users, 20 min)
	@echo "🧪 Running unified load test against STAGING environment..."
	@echo "📊 30 users with realistic ramp up (2.5 spawn rate)"
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	$(call setup_load_test)
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=30 --spawn-rate=2.5 --run-time=20m --headless"

ltp: ## Run unified load test against production (30 users, 20 min) - REQUIRES AUTH OFF
	@echo "🚨 Running unified load test against PRODUCTION environment..."
	@echo "⚠️  Ensure VITE_USE_COGNITO_AUTH=false on production server!"
	@echo "📊 30 users with realistic ramp up (2.5 spawn rate)"
	@if [ ! -f "config/.env.production" ]; then \
		echo "❌ ERROR: config/.env.production file not found!"; \
		exit 1; \
	fi
	$(call setup_load_test)
	@bash -c "cd load_tests && source ../config/.env.production && LOAD_TEST_CONFIG=production ../.venv/bin/locust -f locustfile.py --host=https://atlas-hansard.org --users=30 --spawn-rate=2.5 --run-time=20m --headless"

clean-tests: ## Clean load test artifacts and old reports
	@echo "🧹 Cleaning load test artifacts..."
	@find load_tests -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find load_tests -name "*.pyc" -delete 2>/dev/null || true
	@echo "🗑️  Removing reports older than 7 days..."
	@find load_tests/reports -name "*.json" -mtime +7 -delete 2>/dev/null || true
	@find load_tests/reports -name "*.md" -mtime +7 -delete 2>/dev/null || true
	@find load_tests/reports -name "*.txt" -mtime +7 -delete 2>/dev/null || true
	@echo "✅ Load test cleanup complete"

# Utility Targets
.PHONY: l c vs vs-cpu vs-gpu r xs xs-cpu xs-gpu pm
l: ## Generate requirements.lock file
	@./utils/scripts/generate_lock.sh

c: ## Check Python environment
	@./utils/scripts/check_env.sh

vs: ## Create vector store
	@./utils/scripts/create_store.sh

vs-cpu: ## Create vector store (CPU-only, isolated venv)
	@./utils/scripts/create_store_cpu.sh

vs-gpu: ## Create vector store (GPU/CUDA, isolated venv)
	@./utils/scripts/create_store_gpu.sh

r: ## Generate retriever
	@./utils/scripts/create_retriever.sh

xs: ## Create XML vector store
	@./utils/scripts/create_xml_store.sh

xs-cpu: ## Create XML vector store (CPU-only, isolated venv)
	@./utils/scripts/create_xml_store_cpu.sh

xs-gpu: ## Create XML vector store (GPU/CUDA, isolated venv)
	@./utils/scripts/create_xml_store_gpu.sh

pm: ## Prepare embedding model
	@echo "Preparing embedding model..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@bash -c "source .venv/bin/activate && python create/prepare_model.py"

