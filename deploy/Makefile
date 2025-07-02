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
.PHONY: p dp up
p: ## Deploy to production
	@if [ ! -f "config/.env.production" ]; then \
		echo "ERROR: config/.env.production file not found!"; \
		echo "Please create it from config/.env.development and modify as needed."; \
		exit 1; \
	fi
	@cp config/.env.production /tmp/.env.production
	@bash deploy/production/production.sh
	@rm -f /tmp/.env.production

dp: ## Delete production environment
	@./deploy/production/scripts/clean_prod.sh

up: ## Upgrade production with minimal downtime
	@if [ ! -f "config/.env.production" ]; then \
		echo "ERROR: config/.env.production file not found!"; \
		echo "Please create it from config/.env.development and modify as needed."; \
		exit 1; \
	fi
	@cp config/.env.production /tmp/.env.production
	@bash deploy/production/scripts/upgrade_prod.sh
	@rm -f /tmp/.env.production

# Staging Deployment Targets
.PHONY: sl sr dsl dsr usl usr
sl: ## Deploy to local staging environment
	@echo "Deploying to local staging environment..."
	@bash deploy/staging/staging_localhost.sh

sr: ## Deploy to remote staging environment
	@echo "Deploying to remote staging environment..."
	@if [ ! -f "config/.env.staging" ]; then \
		echo "ERROR: config/.env.staging file not found!"; \
		echo "Please create it from config/.env.development and modify as needed."; \
		exit 1; \
	fi
	@cp config/.env.staging /tmp/.env.staging
	@export STAGING_USER=atlas_deploy && bash deploy/staging/staging_remote.sh
	@rm -f /tmp/.env.staging

dsl: ## Delete local staging environment
	@echo "Deleting local staging environment..."
	@bash deploy/staging/scripts/clean_staging_localhost.sh

dsr: ## Delete remote staging environment
	@echo "Deleting remote staging environment..."
	@cp config/.env.staging /tmp/.env.staging
	@bash deploy/staging/scripts/clean_staging_remote.sh
	@rm -f /tmp/.env.staging

usl: ## Upgrade local staging with minimal downtime
	@echo "Upgrading local staging environment..."
	@bash deploy/staging/scripts/upgrade_localhost.sh

usr: ## Upgrade remote staging with minimal downtime
	@echo "Upgrading remote staging environment..."
	@bash deploy/staging/scripts/upgrade_remote.sh

# Load Testing Targets
.PHONY: lts ltp ltq ltweb ltasync
lts: ## Run load test against staging environment
	@echo "🧪 Running load test against staging environment..."
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing dependencies..."; \
		.venv/bin/pip install -r config/requirements.txt; \
	fi
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=30 --spawn-rate=2 --run-time=15m --headless"

ltp: ## Run load test against production environment
	@echo "🚨 Running load test against production environment..."
	@if [ ! -f "config/.env.production" ]; then \
		echo "❌ ERROR: config/.env.production file not found!"; \
		exit 1; \
	fi
	@echo "⚠️  WARNING: Testing against production environment!"
	@read -p "Are you sure you want to continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing dependencies..."; \
		.venv/bin/pip install -r config/requirements.txt; \
	fi
	@bash -c "cd load_tests && source ../config/.env.production && LOAD_TEST_CONFIG=production ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=20 --spawn-rate=1 --run-time=10m --headless"

ltq: ## Quick smoke test against staging (5 users, 3 minutes)
	@echo "💨 Running quick smoke test against staging..."
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing dependencies..."; \
		.venv/bin/pip install -r config/requirements.txt; \
	fi
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=1 --spawn-rate=1 --run-time=3m --headless"

ltweb: ## Interactive load test with web UI (staging)
	@echo "🌐 Starting interactive load test with web UI against staging..."
	@echo "📊 Open http://localhost:8089 to control the test"
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing dependencies..."; \
		.venv/bin/pip install -r config/requirements.txt; \
	fi
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL"

ltasync: ## Test async processing and Redis queue (staging)
	@echo "🔄 Running async processing load test against staging..."
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing dependencies..."; \
		.venv/bin/pip install -r config/requirements.txt; \
	fi
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --tags=async --users=15 --spawn-rate=1 --run-time=10m --headless"

# Utility Targets
.PHONY: l c vs r xs
l: ## Generate requirements.lock file
	@./utils/scripts/generate_lock.sh

c: ## Check Python environment
	@./utils/scripts/check_env.sh

vs: ## Create vector store
	@./utils/scripts/create_store.sh

r: ## Generate retriever
	@./utils/scripts/create_retriever.sh

xs: ## Create XML vector store
	@./utils/scripts/create_xml_store.sh 