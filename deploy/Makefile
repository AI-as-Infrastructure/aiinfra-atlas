# Deployment Makefile
# Contains targets for development, staging, and production deployment

# Variables
AWS_PROFILE ?= default
AWS_REGION ?= ap-southeast-2
STACK_NAME ?= atlas-prod
DOMAIN_NAME ?= atlas.aiinfra.org

# Development Targets
.PHONY: b f d dev
b: ## Start backend development server
	@./deploy/dev/scripts/start_backend.sh

f: ## Start frontend development server
	@./deploy/dev/scripts/start_frontend.sh

d: ## Destroy development environment
	@./deploy/dev/scripts/clean_dev.sh

dev: ## Start development environment
	@echo "🚀 Starting development environment..."
	@bash deploy/dev/dev.sh

# Production Deployment Targets
.PHONY: p dp up
p: ## Deploy to production
	@./deploy/production/scripts/deploy_prod.sh

dp: ## Delete production environment
	@./deploy/production/scripts/clean_prod.sh

up: ## Upgrade production with minimal downtime
	@./deploy/production/scripts/upgrade_prod.sh

# Staging Deployment Targets
.PHONY: sl sr dsl dsr usl usr
sl: ## Deploy to local staging environment
	@echo "Deploying to local staging environment..."
	@bash deploy/staging/staging_localhost.sh

sr: ## Deploy to remote staging environment
	@echo "Deploying to remote staging environment..."
	@bash deploy/staging/staging_remote.sh

dsl: ## Delete local staging environment
	@echo "Deleting local staging environment..."
	@bash deploy/staging/staging_localhost.sh clean

dsr: ## Delete remote staging environment
	@echo "Deleting remote staging environment..."
	@bash deploy/staging/staging_remote.sh clean

usl: ## Upgrade local staging with minimal downtime
	@echo "Upgrading local staging environment..."
	@bash deploy/staging/scripts/upgrade_staging.sh

usr: ## Upgrade remote staging with minimal downtime
	@echo "Upgrading remote staging environment..."
	@bash deploy/staging/scripts/upgrade_staging.sh

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