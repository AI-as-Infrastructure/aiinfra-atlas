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

d: ## Destroy development environment (removes ALL venvs and node_modules)
	@./deploy/dev/scripts/clean_dev.sh

# Production Deployment Targets  
.PHONY: p dp sp
p: ## Deploy to production (run locally on server)
	@if [ ! -f "config/.env.production" ]; then \
		echo "ERROR: config/.env.production file not found!"; \
		echo "Please create it from config/.env.development and modify as needed."; \
		exit 1; \
	fi
	@bash deploy/production/production.sh

dp: ## Delete production environment (preserves SSL certificates)
	@./deploy/production/scripts/clean_prod.sh


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

lts: ## Run unified load test against staging (30 users, 20 min) with warmup/warmdown
	@echo "🧪 Running unified load test against STAGING environment..."
	@echo "📊 30 users with realistic ramp up (2.5 spawn rate)"
	@if [ ! -f "config/.env.staging" ]; then \
		echo "❌ ERROR: config/.env.staging file not found!"; \
		exit 1; \
	fi
	$(call setup_load_test)
	@bash -c "cd load_tests && source ../config/.env.staging && LOAD_TEST_CONFIG=staging ../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=30 --spawn-rate=2.5 --run-time=20m --headless"

ltp: ## Run unified load test against production (30 users, 20 min) with warmup/warmdown - REQUIRES AUTH OFF
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

# Corpus Wizard Commands
corpus-wizard-cpu: ## Setup corpus wizard with CPU-only PyTorch (smaller ~200MB download)
	@chmod +x utils/scripts/corpus_wizard_setup_cpu.sh 2>/dev/null || true
	@./utils/scripts/corpus_wizard_setup_cpu.sh

corpus-wizard-gpu: ## Setup corpus wizard with GPU/CUDA PyTorch (larger ~2GB download, for NVIDIA GPUs)
	@chmod +x utils/scripts/corpus_wizard_setup_gpu.sh 2>/dev/null || true
	@./utils/scripts/corpus_wizard_setup_gpu.sh

corpus-clean: ## Clean up corpus wizard environment (preserves configs and backups)
	@chmod +x utils/scripts/corpus_wizard_clean.sh 2>/dev/null || true
	@./utils/scripts/corpus_wizard_clean.sh

corpus-build: ## Build a corpus from configuration file (uses corpus environment)
	@if [ -z "$(CONFIG)" ]; then \
		echo "❌ Usage: make corpus-build CONFIG=<config-file>"; \
		echo "Example: make corpus-build CONFIG=corpus_configs/darwin_correspondence.yaml"; \
		exit 1; \
	fi
	@echo "🔨 Building corpus from configuration: $(CONFIG)"
	@if [ -d ".venv_corpus" ]; then \
		source .venv_corpus/bin/activate && python create/create_corpus_store.py --config "$(CONFIG)"; \
	elif [ -d ".venv" ]; then \
		source .venv/bin/activate && python create/create_corpus_store.py --config "$(CONFIG)"; \
	else \
		echo "❌ No virtual environment found. Run 'make corpus-wizard' first."; \
		exit 1; \
	fi

corpus-backup: ## Backup current corpus configuration and vector store
	@echo "📦 Backing up current corpus..."
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	backup_dir="corpus_backups/backup_$$timestamp"; \
	mkdir -p "$$backup_dir"; \
	if [ -d "backend/targets" ]; then \
		cp -r backend/targets "$$backup_dir/targets"; \
		echo "✅ Backed up to $$backup_dir"; \
	else \
		echo "⚠️  No corpus to backup"; \
	fi

corpus-restore: ## Restore corpus from most recent backup
	@echo "🔄 Restoring corpus from backup..."
	@latest_backup=$$(ls -t corpus_backups | head -1); \
	if [ -n "$$latest_backup" ]; then \
		echo "Restoring from corpus_backups/$$latest_backup"; \
		rm -rf backend/targets; \
		cp -r "corpus_backups/$$latest_backup/targets" backend/targets; \
		echo "✅ Corpus restored from $$latest_backup"; \
	else \
		echo "❌ No backup found to restore"; \
	fi

corpus-list: ## List available corpus configurations
	@echo "📚 Available corpus configurations:"
	@if [ -d "corpus_configs" ]; then \
		ls -1 corpus_configs/*.yaml 2>/dev/null | sed 's|corpus_configs/||; s|\.yaml||' || echo "No configurations found"; \
	else \
		echo "No corpus_configs directory found"; \
	fi

corpus-swap: ## Swap to a different corpus using configuration file
	@if [ -z "$(CORPUS)" ]; then \
		echo "❌ Usage: make corpus-swap CORPUS=<config-name>"; \
		echo "Available configurations:"; \
		ls -1 corpus_configs/*.yaml 2>/dev/null | sed 's|corpus_configs/||; s|\.yaml||' || echo "No configurations found"; \
		exit 1; \
	fi
	@if [ ! -d ".venv_corpus" ] && [ ! -d ".venv" ]; then \
		echo "⚠️  No virtual environment found. Setting up corpus environment..."; \
		./utils/scripts/corpus_wizard_setup.sh; \
	fi
	@./utils/scripts/swap_corpus.sh $(CORPUS)

# Quick corpus swap commands
use-hansard: ## Quick swap to Hansard corpus (auto-setup if needed)
	@if [ ! -d ".venv_corpus" ] && [ ! -d ".venv" ]; then \
		echo "⚠️  Setting up corpus environment..."; \
		./utils/scripts/corpus_wizard_setup.sh; \
	fi
	@./utils/scripts/swap_corpus.sh hansard_1901

use-darwin: ## Quick swap to Darwin corpus (auto-setup if needed)
	@if [ ! -d ".venv_corpus" ] && [ ! -d ".venv" ]; then \
		echo "⚠️  Setting up corpus environment..."; \
		./utils/scripts/corpus_wizard_setup.sh; \
	fi
	@./utils/scripts/swap_corpus.sh darwin_correspondence

