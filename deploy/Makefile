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
.PHONY: lts ltfg ltfgs
lts: ## Run realistic load test against staging environment (15 concurrent users, 30 min)
	@echo "🧪 Running realistic load test against staging environment..."
	@echo "📊 Optimized for 8 vCPU, 16GB RAM servers with 15-20 concurrent users"
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
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=15 --spawn-rate=0.2 --run-time=30m --headless"

ltfg: ## Focus group ramp test - 30 users with infrastructure monitoring (20 min)
	@echo "🎯 Running Focus Group Ramp Test (30 users, infrastructure monitoring)..."
	@echo "🖥️  Monitoring memory/CPU usage to determine infrastructure load"
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing dependencies (including psutil for infrastructure monitoring)..."; \
		.venv/bin/pip install -r config/requirements.txt psutil; \
	fi
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=30 --spawn-rate=2.5 --run-time=20m --headless"

ltfgs: ## Focus group sustained test - 30 users sustained load (30 min) 
	@echo "🎯 Running Focus Group Sustained Test (30 users, sustained load)..."
	@echo "🖥️  Monitoring infrastructure under sustained 30-user load"
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	@if [ ! -d ".venv" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@if [ ! -f ".venv/bin/locust" ]; then \
		echo "📥 Installing dependencies (including psutil for infrastructure monitoring)..."; \
		.venv/bin/pip install -r config/requirements.txt psutil; \
	fi
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=30 --spawn-rate=3.0 --run-time=30m --headless"

# Utility Targets
.PHONY: l c vs r xs pm
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

pm: ## Prepare embedding model
	@echo "Preparing embedding model..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@bash -c "source .venv/bin/activate && python create/prepare_model.py"

