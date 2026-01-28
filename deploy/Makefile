# Deployment Makefile
# Contains targets for development, staging, and production deployment

# Variables
AWS_PROFILE ?= default
AWS_REGION ?= ap-southeast-2
STACK_NAME ?= atlas-prod
DOMAIN_NAME ?= atlas.aiinfra.org

# Development Targets
.PHONY: b f d stop-wizard
b: ## Start backend development server
	@./deploy/dev/scripts/start_backend.sh

f: ## Start frontend development server
	@./deploy/dev/scripts/start_frontend.sh

d: ## Destroy development environment (removes ALL venvs and node_modules)
	@./deploy/dev/scripts/clean_dev.sh

stop-wizard: ## Stop wizard/development servers gracefully (backend and frontend)
	@./deploy/dev/scripts/stop_wizard.sh

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
	@bash -c "cd tests/load_tests && source ../../config/.env.staging && LOAD_TEST_CONFIG=staging ../../.venv/bin/locust -f locustfile.py --host=\$$VITE_API_URL --users=30 --spawn-rate=2.5 --run-time=20m --headless"

ltp: ## Run unified load test against production (30 users, 20 min) with warmup/warmdown - REQUIRES AUTH OFF
	@echo "🚨 Running unified load test against PRODUCTION environment..."
	@echo "⚠️  Ensure VITE_USE_COGNITO_AUTH=false on production server!"
	@echo "📊 30 users with realistic ramp up (2.5 spawn rate)"
	@if [ ! -f "config/.env.production" ]; then \
		echo "❌ ERROR: config/.env.production file not found!"; \
		exit 1; \
	fi
	$(call setup_load_test)
	@bash -c "cd tests/load_tests && source ../../config/.env.production && LOAD_TEST_CONFIG=production ../../.venv/bin/locust -f locustfile.py --host=https://atlas-hansard.org --users=30 --spawn-rate=2.5 --run-time=20m --headless"

clean-tests: ## Clean load test artifacts and old reports
	@echo "🧹 Cleaning load test artifacts..."
	@find tests/load_tests -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find tests/load_tests -name "*.pyc" -delete 2>/dev/null || true
	@echo "🗑️  Removing reports older than 7 days..."
	@find tests/load_tests/reports -name "*.json" -mtime +7 -delete 2>/dev/null || true
	@find tests/load_tests/reports -name "*.md" -mtime +7 -delete 2>/dev/null || true
	@find tests/load_tests/reports -name "*.txt" -mtime +7 -delete 2>/dev/null || true
	@echo "✅ Load test cleanup complete"

# Utility Targets
.PHONY: l c pm
l: ## Generate requirements.lock file
	@./utils/scripts/generate_lock.sh

c: ## Check Python environment
	@./utils/scripts/check_env.sh

pm: ## Prepare embedding model
	@echo "Preparing embedding model..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@bash -c "source .venv/bin/activate && python utils/scripts/prepare_model.py"

# Corpus Wizard Commands
# Note: The corpus wizard uses the main .venv environment
# GPU support is automatically detected and configured when running 'make b'
# To use the corpus wizard:
# 1. Run 'make b' to start the backend (GPU will be auto-detected and configured)
# 2. Run 'make f' to start the frontend (in new terminal)
# 3. Navigate to http://localhost:5173/corpus-wizard

corpus-backup: ## Backup current corpus configuration and vector store
	@echo "📦 Backing up current corpus..."
	@timestamp=$$(date +%Y%m%d_%H%M%S); \
	backup_dir="corpus_backups/backup_$$timestamp"; \
	mkdir -p "$$backup_dir"; \
	backed_up=false; \
	if [ -d "backend/corpus" ]; then \
		cp -r backend/corpus "$$backup_dir/corpus"; \
		backed_up=true; \
	fi; \
	if [ -d "backend/targets" ]; then \
		cp -r backend/targets "$$backup_dir/targets"; \
		backed_up=true; \
	fi; \
	if [ -f "config/corpus.yaml" ]; then \
		cp config/corpus.yaml "$$backup_dir/corpus.yaml"; \
		backed_up=true; \
	fi; \
	if [ "$$backed_up" = true ]; then \
		echo "✅ Backed up to $$backup_dir"; \
	else \
		echo "⚠️  No corpus to backup"; \
	fi

corpus-restore: ## Restore corpus from most recent backup
	@echo "🔄 Restoring corpus from backup..."
	@latest_backup=$$(ls -t corpus_backups | head -1); \
	if [ -n "$$latest_backup" ]; then \
		echo "Restoring from corpus_backups/$$latest_backup"; \
		if [ -d "corpus_backups/$$latest_backup/corpus" ]; then \
			rm -rf backend/corpus; \
			cp -r "corpus_backups/$$latest_backup/corpus" backend/corpus; \
		fi; \
		if [ -d "corpus_backups/$$latest_backup/targets" ]; then \
			rm -rf backend/targets; \
			cp -r "corpus_backups/$$latest_backup/targets" backend/targets; \
		fi; \
		if [ -f "corpus_backups/$$latest_backup/corpus.yaml" ]; then \
			cp "corpus_backups/$$latest_backup/corpus.yaml" config/corpus.yaml; \
		fi; \
		echo "✅ Corpus restored from $$latest_backup"; \
	else \
		echo "❌ No backup found to restore"; \
	fi

corpus-list: ## List available corpus configurations
	@echo "📚 Available corpus configurations:"
	@if [ -d "backend/corpus/tmp" ] && [ -f "backend/corpus/tmp/corpus_config.yaml" ]; then \
		echo "✅ Active corpus in backend/corpus/tmp (use wizard to activate)"; \
	fi
	@if [ -d "backend/corpus" ] && [ -f "backend/corpus/manifest.json" ]; then \
		echo "✅ Deployed corpus in backend/corpus"; \
	fi
	@if [ -f "config/corpus.yaml" ]; then \
		echo "✅ Corpus configuration in config/corpus.yaml"; \
	fi
	@if ls corpus_backups/*/corpus.yaml 1>/dev/null 2>&1 || ls corpus_backups/*/corpus_config.yaml 1>/dev/null 2>&1; then \
		echo "📦 Backed up corpora:"; \
		ls -t corpus_backups | head -5; \
	else \
		echo "⚠️  No corpus configurations found. Use the Corpus Wizard to create one."; \
	fi

# Note: corpus-swap has been removed. Use the Corpus Wizard UI to manage corpora.

# Note: Quick corpus swap commands have been removed.
# There are no pre-built corpora. Use the Corpus Wizard to create your first corpus.

