# Main Makefile
include deploy/Makefile
include deploy/help.mk
include utils/help.mk

# Common variables
VENV_DIR := .venv
FRONTEND_DIR := frontend
BACKEND_DIR := backend

# Phoenix data export target
.PHONY: export
export: venv ## Export unified Phoenix session report (default: last 7 days)
	$(VENV_DIR)/bin/python reports/phoenix_export.py

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