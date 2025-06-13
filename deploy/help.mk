# Deployment help targets
.PHONY: help-p help-dp help-s help-ds

help-p:
	@echo "Deploy to production"
	@echo "Usage: make p"
	@echo ""
	@echo "This target deploys the application to production:"
	@echo "1. Builds and deploys the frontend"
	@echo "2. Sets up the backend environment"
	@echo "3. Configures and starts production services"
	@echo ""
	@echo "Required:"
	@echo "- AWS credentials configured"
	@echo "- Production environment variables"

help-dp:
	@echo "Delete production environment"
	@echo "Usage: make dp"
	@echo ""
	@echo "This target removes the production deployment:"
	@echo "1. Stops all production services"
	@echo "2. Removes the application files"
	@echo "3. Cleans up systemd services"
	@echo ""
	@echo "WARNING: This will remove all production data!"

help-s:
	@echo "Deploy to staging"
	@echo "Usage: make s"
	@echo ""
	@echo "This target deploys the application to staging:"
	@echo "1. Builds and deploys the frontend"
	@echo "2. Sets up the backend environment"
	@echo "3. Configures and starts staging services"
	@echo ""
	@echo "Required:"
	@echo "- STAGING_IP environment variable"
	@echo "- STAGING_USER environment variable"

help-ds:
	@echo "Delete staging environment"
	@echo "Usage: make ds"
	@echo ""
	@echo "This target removes the staging deployment:"
	@echo "1. Stops all staging services"
	@echo "2. Removes the application files"
	@echo "3. Cleans up systemd services"
	@echo ""
	@echo "WARNING: This will remove all staging data!" 