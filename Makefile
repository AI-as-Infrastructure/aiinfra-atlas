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

# Analysis targets
.PHONY: hansard-analysis
hansard-analysis: venv ## Run Hansard parliamentary data analysis with visualizations
	@echo "🔍 Running Hansard analysis..."
	$(VENV_DIR)/bin/python analysis/analyze_hansard_spans.py
	@echo "✅ Hansard analysis complete. Check analysis/output/ for results."

.PHONY: darwin-analysis
darwin-analysis: venv ## Run Darwin correspondence data analysis with visualizations (internal)
	@echo "🔬 Running Darwin analysis..."
	$(VENV_DIR)/bin/python analysis/analyze_darwin_spans.py
	@echo "✅ Darwin analysis complete. Check analysis/output/ for results."

# Virtual environment setup
.PHONY: venv
venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate: config/requirements.lock
	@if [ ! -d "$(VENV_DIR)" ]; then \
		python3 -m venv $(VENV_DIR); \
	fi
	@if [ ! -f "config/requirements.lock" ]; then echo "❌ Missing config/requirements.lock. Run 'make l' first."; exit 1; fi
	$(VENV_DIR)/bin/pip install -r config/requirements.lock
	@touch $(VENV_DIR)/bin/activate

# Help target
.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)