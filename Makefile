# Main Makefile
include deploy/Makefile
include deploy/help.mk
include utils/help.mk

# Common variables
VENV_DIR := .venv
FRONTEND_DIR := frontend
BACKEND_DIR := backend

# Pass-through environment variables for backup scripts (defaults live in the script)
export PHOENIX_BACKUP_ROOT
export PHOENIX_ENV_FILE

# Phoenix production backups (uses config/.env.production)
.PHONY: backup-prod
backup-prod: venv ## Backup full prod project contents (env loaded from config/.env.production)
	PHOENIX_ENV_FILE=config/.env.production \
	$(VENV_DIR)/bin/python utils/scripts/phoenix_backup_prod.py

# System health check
.PHONY: health
health: ## Run comprehensive system health check
	@echo "🏥 Running system health check..."
	@utils/scripts/health_check.sh

.PHONY: health-verbose
health-verbose: ## Run detailed system health check with verbose output
	@echo "🏥 Running detailed system health check..."
	@utils/scripts/health_check.sh --verbose

.PHONY: health-json
health-json: ## Run system health check with JSON output for monitoring
	@utils/scripts/health_check.sh --json

.PHONY: health-critical
health-critical: ## Run system health check showing only critical issues
	@echo "🚨 Checking for critical system issues..."
	@utils/scripts/health_check.sh --critical-only

# Analysis targets
.PHONY: hansard-analysis
hansard-analysis: venv ## Run Hansard parliamentary data analysis with visualizations
	@echo "🔍 Running Hansard analysis..."
	$(VENV_DIR)/bin/python analysis/analyze_hansard_spans.py
	@echo "✅ Hansard analysis complete. Check analysis/output/ for results."

# Virtual environment setup
.PHONY: venv
venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate: config/requirements.lock
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "📦 Creating virtual environment..."; \
		python3 -m venv $(VENV_DIR) 2>/dev/null || { \
			echo "❌ Failed to create virtual environment."; \
			echo ""; \
			echo "If you see an error about 'ensurepip', install the venv package:"; \
			echo "  Ubuntu/Debian: sudo apt-get install python3-venv"; \
			echo "  or for specific Python version: sudo apt-get install python3.12-venv"; \
			echo ""; \
			echo "Then run this command again."; \
			exit 1; \
		}; \
	fi
	@if [ ! -f "config/requirements.lock" ]; then echo "❌ Missing config/requirements.lock. Run 'make l' first."; exit 1; fi
	@if [ -f "$(VENV_DIR)/bin/pip" ]; then \
		$(VENV_DIR)/bin/pip install -r config/requirements.lock; \
	else \
		echo "❌ Virtual environment not properly created. Please install python3-venv package."; \
		exit 1; \
	fi
	@touch $(VENV_DIR)/bin/activate

# Help target
.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)