# Deployment Makefile
# Contains targets for development, staging, and production deployment

# Variables
AWS_PROFILE ?= default
AWS_REGION ?= ap-southeast-2
STACK_NAME ?= atlas-prod
DOMAIN_NAME ?= atlas.aiinfra.org

# Development Targets
.PHONY: b f d rater-check rater-load
b: ## Start backend development server
	@./deploy/dev/scripts/start_backend.sh

f: ## Start frontend development server
	@./deploy/dev/scripts/start_frontend.sh

d: ## Destroy development environment
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


# Cloudflare Tunnel Deployment Targets
.PHONY: cf scf dcf
cf: ## Deploy behind Cloudflare Zero Trust Tunnel
	@if [ ! -f "config/.env.production" ]; then \
		echo "ERROR: config/.env.production not found!"; \
		echo "Set CLOUDFLARE_TUNNEL_TOKEN, CLOUDFLARE_TUNNEL_NAME, and AUTH_METHOD=cloudflare in it."; \
		exit 1; \
	fi
	@bash deploy/cloudflare/cloudflare.sh

scf: ## Stop Cloudflare tunnel deployment gracefully
	@echo "WARNING: This will stop the Cloudflare tunnel deployment!"
	@read -p "Are you sure you want to continue? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "Stopping Cloudflare tunnel deployment..."
	@bash deploy/cloudflare/scripts/stop_cloudflare.sh

dcf: ## Delete Cloudflare tunnel deployment (preserves UFW and tunnel in dashboard)
	@bash deploy/cloudflare/scripts/clean_cloudflare.sh

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
	@echo "⚠️  Ensure AUTH_METHOD=none on production server!"
	@echo "📊 30 users with realistic ramp up (2.5 spawn rate)"
	@if [ ! -f "config/.env.production" ]; then \
		echo "❌ ERROR: config/.env.production file not found!"; \
		exit 1; \
	fi
	$(call setup_load_test)
	@bash -c "cd load_tests && source ../config/.env.production && if [ -z \"\$$VITE_API_URL\" ]; then echo '❌ ERROR: VITE_API_URL not set in config/.env.production'; exit 1; fi && LOAD_TEST_CONFIG=production ../.venv/bin/locust -f locustfile.py --host=\"\$$VITE_API_URL\" --users=30 --spawn-rate=2.5 --run-time=20m --headless"

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

# Inter-rater seeding
.PHONY: seed seed-dry seed-reset
SEED_ARGS ?=
# Pick the first env file that exists: explicit ENV_FILE > .env.development > .env.production
define resolve_seed_env
	if [ -n "$$ENV_FILE" ]; then \
		if [ ! -f "$$ENV_FILE" ]; then echo "ERROR: ENV_FILE=$$ENV_FILE not found"; exit 1; fi; \
	elif [ -f config/.env.development ]; then ENV_FILE=config/.env.development; \
	elif [ -f config/.env.production ]; then ENV_FILE=config/.env.production; \
	else echo "ERROR: no env file found (looked for config/.env.development, config/.env.production)"; exit 1; fi; \
	echo "Using $$ENV_FILE"; \
	set -a; . "$$ENV_FILE"; set +a
endef

seed: ## Seed inter-rater sessions from data/seed_questions.json (server must be running on localhost:8000)
	@if [ ! -d ".venv" ]; then echo "ERROR: .venv not found — run setup first"; exit 1; fi
	@$(resolve_seed_env); \
		.venv/bin/python utils/scripts/seed_questions.py $(SEED_ARGS)

seed-dry: ## Dry-run seed: validate JSON and print sizing check
	@if [ ! -d ".venv" ]; then echo "ERROR: .venv not found — run setup first"; exit 1; fi
	@$(resolve_seed_env); \
		.venv/bin/python utils/scripts/seed_questions.py --dry-run $(SEED_ARGS)

seed-reset: ## Delete INTER_RATER_PROJECT from Phoenix to reset to baseline (then run `make seed`)
	@if [ ! -d ".venv" ]; then echo "ERROR: .venv not found — run setup first"; exit 1; fi
	@$(resolve_seed_env); \
		.venv/bin/python utils/scripts/seed_reset.py $(SEED_ARGS)

rater-check: ## Read-only pre-flight for inter-rating: pool saturation, cohort slots, annotation shapes, latest ratings
	@if [ ! -d ".venv" ]; then echo "ERROR: .venv not found — run setup first"; exit 1; fi
	@$(resolve_seed_env); \
		rc=0; \
		echo ""; echo "=== pool and cohort pre-flight ==="; \
		.venv/bin/python utils/scripts/inter_rater_preflight.py || rc=1; \
		echo ""; echo "=== annotation shapes and recent ratings ==="; \
		.venv/bin/python utils/scripts/inter_rater_annotation_check.py || rc=1; \
		echo ""; \
		if [ $$rc -ne 0 ]; then echo "One or more checks FAILED (see above)."; fi; \
		exit $$rc

rater-load: ## Run the inter-rater load test (production env and isolated pytest deps by default)
	@if [ ! -d ".venv" ]; then echo "ERROR: .venv not found — run setup first"; exit 1; fi
	@DEPS_DIR="$${RATER_LOAD_DEPS_DIR:-.rater-load-deps}"; \
		PYTHONPATH="$$DEPS_DIR$${PYTHONPATH:+:$$PYTHONPATH}"; \
		if [ ! -d "$$DEPS_DIR/pytest" ] || [ ! -d "$$DEPS_DIR/pytest_asyncio" ]; then \
			echo "Installing isolated rater-load test dependencies in $$DEPS_DIR"; \
			mkdir -p "$$DEPS_DIR"; \
			.venv/bin/python -m pip install --disable-pip-version-check --upgrade \
				--target "$$DEPS_DIR" pytest==8.3.5 pytest-asyncio==0.25.2 || exit 1; \
		fi; \
		ENV_FILE="$${ENV_FILE:-config/.env.production}"; \
		if [ ! -f "$$ENV_FILE" ]; then \
			echo "ERROR: ENV_FILE=$$ENV_FILE not found"; \
			exit 1; \
		fi; \
		echo "Using $$ENV_FILE"; \
		set -a; . "$$ENV_FILE" || { STATUS=$$?; set +a; exit $$STATUS; }; set +a; \
		SCRATCH=$$(.venv/bin/python utils/scripts/scratch_redis_url.py) || exit 1; \
		echo "Scratch Redis: $${SCRATCH%%//*}//…/$${SCRATCH##*/}  (app keyspace untouched)"; \
		PYTHONPATH="$$PYTHONPATH" RATER_LOAD=1 REDIS_URL="$$SCRATCH" \
			.venv/bin/python -m pytest \
			tests/backend/services/test_inter_rater_concurrency.py -v
