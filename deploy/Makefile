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
.PHONY: p dp
p: ## Deploy to production
	@./deploy/production/scripts/deploy_prod.sh

dp: ## Delete production environment
	@./deploy/production/scripts/clean_prod.sh

# Staging Deployment Targets
.PHONY: s ds
s: ## Deploy to staging
	@./deploy/staging/scripts/deploy_staging.sh

ds: ## Delete staging environment
	@./deploy/staging/scripts/clean_staging.sh

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