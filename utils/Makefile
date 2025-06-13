# Utilities Makefile
# Contains utility targets for project management

# Variables
VENV_DIR := .venv
PYTHON_VERSION := $(shell python3 --version 2>&1 | awk '{print $$2}')

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