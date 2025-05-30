# === PRODUCTION DEPLOYMENT TARGETS ===
# These targets deploy to production AWS environment using CloudFormation

.PHONY: prod-server dprod-server prod clean-prod-app

# Deploy to production environment using CloudFormation
prod-server: ## Deploy to production AWS environment
	@echo "Deploying to production environment using CloudFormation..."
	@echo "Checking AWS SSO login status..."
	@/usr/local/bin/aws sts get-caller-identity --profile ANU-Account-Admin-825765404490 > /dev/null 2>&1 || { \
		echo "AWS SSO session not active or expired. Please login first:" && \
		echo "/usr/local/bin/aws sso login --profile ANU-Account-Admin-825765404490" && \
		exit 1; \
	}
	@echo "Creating/updating CloudFormation stack..."
	@/usr/local/bin/aws cloudformation deploy \
		--stack-name atlas-production \
		--template-file deploy/production/atlas-prod-server.yaml \
		--parameter-overrides \
			KeyName=atlas-prod-key-west1 \
			DomainName=atlas-hansard.org \
		--capabilities CAPABILITY_IAM \
		--profile ANU-Account-Admin-825765404490 \
		--region us-west-1
	@echo "Deployment initiated. Checking stack status..."
	@/usr/local/bin/aws cloudformation describe-stacks \
		--stack-name atlas-production \
		--query "Stacks[0].StackStatus" \
		--output text \
		--profile ANU-Account-Admin-825765404490 \
		--region us-west-1
	@echo "\nTo monitor deployment progress, run:"
	@echo "/usr/local/bin/aws cloudformation describe-stacks --stack-name atlas-production --profile ANU-Account-Admin-825765404490 --region us-west-1"
	@echo "\nOnce deployment is complete, you can get the instance details with:"
	@echo "/usr/local/bin/aws cloudformation describe-stacks --stack-name atlas-production --query 'Stacks[0].Outputs' --profile ANU-Account-Admin-825765404490 --region us-west-1"

# Delete the production CloudFormation stack
dprod-server: ## Delete the production environment
	@echo "WARNING: This will delete the entire production environment!"
	@echo "Are you sure you want to continue? (y/n)"
	@bash -c 'read -p "" confirm && [[ "$$confirm" == [yY] || "$$confirm" == [yY][eE][sS] ]] || exit 1'
	@echo "Deleting production CloudFormation stack..."
	@/usr/local/bin/aws cloudformation delete-stack \
		--stack-name atlas-production \
		--profile ANU-Account-Admin-825765404490 \
		--region us-west-1
	@echo "Deletion initiated. To check status:"
	@echo "/usr/local/bin/aws cloudformation describe-stacks --stack-name atlas-production --profile ANU-Account-Admin-825765404490 --region us-west-1"

# Deploy application code to the production server
prod: ## Deploy application code to the production server
	@echo "Deploying application code to production server..."
	@echo "Checking AWS SSO login status..."
	@/usr/local/bin/aws sts get-caller-identity --profile ANU-Account-Admin-825765404490 > /dev/null 2>&1 || { \
		echo "AWS SSO session not active or expired. Please login first:" && \
		echo "/usr/local/bin/aws sso login --profile ANU-Account-Admin-825765404490" && \
		exit 1; \
	}
	@echo "Getting EC2 instance public IP..."
	@PROD_IP=$$(aws cloudformation describe-stacks --stack-name atlas-production --query "Stacks[0].Outputs[?OutputKey=='PublicIP'].OutputValue" --output text --profile ANU-Account-Admin-825765404490 --region us-west-1) && \
	if [ -z "$$PROD_IP" ]; then \
		echo "Error: Could not get production server IP. Make sure the CloudFormation stack is deployed."; \
		echo "Run 'make prod-server' first to deploy the infrastructure."; \
		exit 1; \
	else \
		echo "Found production server at $$PROD_IP"; \
		./deploy/production/production.sh $$PROD_IP atlas_deploy; \
	fi

# Clean up application files from production server (leaves server infrastructure intact)
clean-prod-app: ## Destroy app and clean all files including /opt/atlas (leaves server intact)
	@echo "WARNING: This will destroy the application and clean all files including /opt/atlas!"
	@echo "The server infrastructure will remain intact for rebuilding."
	@echo "Are you sure you want to continue? (y/n)"
	@bash -c 'read -p "" confirm && [[ "$$confirm" == [yY] || "$$confirm" == [yY][eE][sS] ]] || exit 1'
	@echo "Checking AWS SSO login status..."
	@/usr/local/bin/aws sts get-caller-identity --profile ANU-Account-Admin-825765404490 > /dev/null 2>&1 || { \
		echo "AWS SSO session not active or expired. Please login first:" && \
		echo "/usr/local/bin/aws sso login --profile ANU-Account-Admin-825765404490" && \
		exit 1; \
	}
	@echo "Getting EC2 instance public IP..."
	@PROD_IP=$$(aws cloudformation describe-stacks --stack-name atlas-production --query "Stacks[0].Outputs[?OutputKey=='PublicIP'].OutputValue" --output text --profile ANU-Account-Admin-825765404490 --region us-west-1) && \
	if [ -z "$$PROD_IP" ]; then \
		echo "Error: Could not get production server IP. Make sure the CloudFormation stack is deployed."; \
		echo "Run 'make prod-server' first to deploy the infrastructure."; \
		exit 1; \
	else \
		echo "Cleaning application from production server at $$PROD_IP"; \
		SSH_KEY="$$HOME/atlas-prod-key-west1.pem"; \
		ssh -i $$SSH_KEY -o StrictHostKeyChecking=no atlas_deploy@$$PROD_IP \
		'set -e && \
		echo "🧹 Starting application cleanup..." && \
		echo "Stopping and disabling gunicorn service..." && \
		sudo systemctl stop gunicorn 2>/dev/null || echo "Gunicorn service not running" && \
		sudo systemctl disable gunicorn 2>/dev/null || echo "Gunicorn service not enabled" && \
		echo "Removing systemd service file..." && \
		sudo rm -f /etc/systemd/system/gunicorn.service && \
		sudo systemctl daemon-reload && \
		echo "Removing nginx site configuration..." && \
		sudo rm -f /etc/nginx/sites-available/atlas && \
		sudo rm -f /etc/nginx/sites-enabled/atlas && \
		echo "Restoring default nginx site..." && \
		sudo ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default 2>/dev/null || true && \
		sudo nginx -t && sudo systemctl reload nginx || echo "Nginx reload failed - check configuration" && \
		echo "Removing application directory /opt/atlas..." && \
		sudo rm -rf /opt/atlas && \
		echo "Removing application log files..." && \
		sudo rm -rf /var/log/atlas && \
		echo "Resetting Redis configuration (if present)..." && \
		if [ -f /etc/redis/redis.conf ]; then \
			sudo sed -i "/^requirepass/d" /etc/redis/redis.conf && \
			sudo systemctl restart redis-server 2>/dev/null || echo "Redis service not available"; \
		elif [ -f /etc/redis.conf ]; then \
			sudo sed -i "/^requirepass/d" /etc/redis.conf && \
			sudo systemctl restart redis 2>/dev/null || echo "Redis service not available"; \
		else \
			echo "Redis configuration file not found - skipping Redis reset"; \
		fi && \
		echo "Cleaning up temporary files..." && \
		sudo rm -f /tmp/.env.production /tmp/gunicorn.service /tmp/nginx.conf && \
		echo "✅ Application cleanup completed successfully!" && \
		echo "✅ Server infrastructure remains intact" && \
		echo "✅ You can now rebuild with make prod"'; \
	fi
###############################################################################
# ATLAS Makefile
#
# This Makefile provides commands for development, building, and deployment of ATLAS.
###############################################################################

#------------------------------------------------------------------------------
# Development Environment Commands
#------------------------------------------------------------------------------

# Start the backend development environment (FastAPI server)
# This includes database setup, environment initialization, and running the API server
.PHONY: db
db:
	bash deploy/dev/dev.sh

# Start the frontend development server (Vue.js)
# This runs the Vue development server on port 5173 and opens it in a browser
.PHONY: df
df:
	@echo "Starting ATLAS frontend development server..."
	cd frontend && \
		export NVM_DIR="$$HOME/.nvm"; \
		if [ ! -s "$$NVM_DIR/nvm.sh" ]; then \
			echo "Error: nvm is not installed. Please install nvm (https://github.com/nvm-sh/nvm) and run 'nvm install' in the frontend directory."; \
			exit 1; \
		fi; \
		. "$$NVM_DIR/nvm.sh"; \
		nvm use; \
		([ -d node_modules ] || npm install) && npm run dev

# Destroy the development environment
# This stops all running servers, removes containers, and cleans up dependencies
.PHONY: dd
dd:
	@echo "Stopping any process running on port 8000 (FastAPI server)..."
	@lsof -ti :8000 | xargs -r kill -9 || true
	@echo "Removing virtual environment..."
	@rm -rf .venv
	@echo "Removing node_modules and package-lock.json from project root and frontend/ ..."
	@rm -rf node_modules package-lock.json
	@rm -rf frontend/node_modules frontend/package-lock.json
	@rm -rf frontend/dist
	@echo "Removed frontend/dist directory"
	@echo "FastAPI dev environment destroyed."

#------------------------------------------------------------------------------
# Build and Deployment Commands
#------------------------------------------------------------------------------

# Build frontend for staging environment
.PHONY: build-staging
build-staging:
	@echo "Building ATLAS frontend for staging environment..."
	cd vue && npm run build:staging

# Build frontend for production environment
.PHONY: build-production
build-production:
	@echo "Building ATLAS frontend for production environment..."
	cd vue && npm run build:production

#------------------------------------------------------------------------------
# Dependencies Management
#------------------------------------------------------------------------------

.PHONY: lock

# Generates a locked requirements file with exact versions
# NOTE: This creates a machine-specific lock file that works for your local dev environment
# and staging Docker deployment. Other developers may need to generate their own lock file.
lock:
	@echo "CAUTION: This will generate a machine-specific requirements.lock file"
	@echo "Generating requirements.lock file with Python $${PYTHON_VERSION}..."
	./config/generate-lockfile.sh
	@echo "Lock file generated successfully for your specific environment."

# Check your Python environment
.PHONY: check-env

check-env:
	@echo "Checking Python environment..."
	@echo "Recommended: Python 3.10.12 (app developed and tested with this version)"
	@echo "Current: $$(python3 --version)"
	@echo ""
	@echo "The app may work with newer Python versions (3.11, 3.12), but for"
	@echo "maximum compatibility and consistency, Python 3.10.12 is recommended."
	@echo ""
	@echo "IMPORTANT: The requirements.lock file was generated on Pop_OS! with NVIDIA GPU support."
	@echo "If you are using a different system (especially without NVIDIA GPU),"
	@echo "the lock file may not work for you due to platform-specific dependencies."
	@echo ""
	@echo "If using a different system or Python version:"
	@echo "1. You may need to generate your own requirements.lock file with 'make lock'"
	@echo "2. Or install directly from requirements.txt if the lock file doesn't work"

#------------------------------------------------------------------------------
# Data Management Commands
#------------------------------------------------------------------------------

# Create the Chroma vector store using the script in create/
.PHONY: store
store:
	@echo "Creating Chroma vector store..."
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
	fi
	@bash -c 'set -e && \
		. .venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r config/requirements.lock && \
		python create/create_hansard_retriever.py'
	@echo "\nChroma vector store created in backend/targets/chroma_db"
	@echo "\nTo distribute this database:"
	@echo "1. Copy the database and statistics file to backend/targets/:"
	@echo "   mkdir -p backend/targets/chroma_db"
	@echo "   cp -r create/output/chroma_db/* backend/targets/chroma_db/"
	@echo "   cp create/output/blert_1000.txt backend/targets/"
	@echo "2. Commit and push with Git LFS"
	@echo "\nNote: The database will be used from the location specified by CHROMA_PERSIST_DIRECTORY in config/.env.development"

# Generate the retriever: ensure venv, install deps, run script
retriever:
	bash -c 'if [ ! -d ".venv" ]; then python3 -m venv .venv; fi && \
		. .venv/bin/activate && \
		pip install --upgrade pip && \
		pip install -r config/requirements.lock && \
		python create/create_hansard_retriever.py'

# === STAGING DEPLOYMENT TARGETS ===
.PHONY: sl dsl dslf

# Deploy to local staging environment
sl: ## Deploy to staging on localhost
	@echo "Deploying to local staging environment..."
	@chmod +x deploy/staging/staging_localhost.sh
	@./deploy/staging/staging_localhost.sh

# Basic cleanup of local staging deployment (without removing code)
dsl: ## Basic cleanup of local staging deployment
	@echo "Performing basic cleanup of local staging deployment..."
	@sudo systemctl stop gunicorn || true
	@sudo systemctl disable gunicorn || true
	@sudo rm -f /etc/systemd/system/gunicorn.service || true
	@sudo rm -f /etc/nginx/sites-enabled/atlas || true
	@sudo rm -f /etc/nginx/sites-available/atlas || true
	@sudo systemctl restart nginx || true
	@echo "Removing log files..."
	@rm -f deploy/staging/logs/*.log || true
	@echo "✅ Basic cleanup completed (code at /opt/atlas is preserved)"

# Full cleanup of local staging deployment (including code removal)
dslf: ## Full cleanup of local staging deployment
	@echo "Performing full cleanup of local staging deployment..."
	@sudo systemctl stop gunicorn || true
	@sudo systemctl disable gunicorn || true
	@sudo rm -f /etc/systemd/system/gunicorn.service || true
	@sudo rm -f /etc/nginx/sites-enabled/atlas || true
	@sudo rm -f /etc/nginx/sites-available/atlas || true
	@sudo systemctl restart nginx || true
	@echo "Removing log files..."
	@rm -f deploy/staging/logs/*.log || true
	@echo "Clearing npm cache..."
	@cd frontend && npm cache clean --force || true
	@echo "Removing node_modules and package-lock.json from frontend..."
	@rm -rf frontend/node_modules frontend/package-lock.json frontend/.vite || true
	@echo "Removing frontend/dist directory..."
	@rm -rf frontend/dist || true
	@echo "Removing any generated environment files..."
	@rm -f frontend/.env || true
	@sudo rm -rf /opt/atlas || true
	@echo "Checking for any Vite cache directories..."
	@rm -rf $$HOME/.vite || true
	@rm -rf $$HOME/.cache/vite || true
	@echo "✅ Full cleanup completed (including removal of /opt/atlas and npm/node caches)"