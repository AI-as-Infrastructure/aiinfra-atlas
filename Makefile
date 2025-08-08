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
export PHOENIX_EXPORT_ANNOTATIONS
export PHOENIX_EXPORT_DATASETS

# Phoenix data export target
.PHONY: export
export: venv ## Export unified Phoenix session report (default: last 7 days)
	$(VENV_DIR)/bin/python reports/phoenix_export.py

# Production-only backups (uses config/.env.production)
.PHONY: backup-prod
backup-prod: venv ## Backup prod projects only (env loaded from config/.env.production)
	PHOENIX_ENV_FILE=config/.env.production \
	PHOENIX_PROJECTS=$$(grep -E '^PHOENIX_PROJECTS=' config/.env.production | sed 's/PHOENIX_PROJECTS=//') \
	PHOENIX_PROJECT_NAME=$$(grep -E '^PHOENIX_PROJECT_NAME=' config/.env.production | sed 's/PHOENIX_PROJECT_NAME=//') \
	$(VENV_DIR)/bin/python utils/scripts/phoenix_backup_prod.py

.PHONY: backup-prod-since
backup-prod-since: venv ## Backup prod since N days ago (usage: make backup-prod-since N=1)
	N?=1; \
	PHOENIX_ENV_FILE=config/.env.production \
	PHOENIX_PROJECTS=$$(grep -E '^PHOENIX_PROJECTS=' config/.env.production | sed 's/PHOENIX_PROJECTS=//') \
	PHOENIX_PROJECT_NAME=$$(grep -E '^PHOENIX_PROJECT_NAME=' config/.env.production | sed 's/PHOENIX_PROJECT_NAME=//') \
	$(VENV_DIR)/bin/python utils/scripts/phoenix_backup_prod.py --since-days $$N

# Virtual environment setup
.PHONY: venv
venv: $(VENV_DIR)/bin/activate

$(VENV_DIR)/bin/activate: config/requirements.txt
	@if [ ! -d "$(VENV_DIR)" ]; then \
		python3 -m venv $(VENV_DIR); \
	fi
	$(VENV_DIR)/bin/pip install -r config/requirements.txt
	@touch $(VENV_DIR)/bin/activate

# Help target
.PHONY: help
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)