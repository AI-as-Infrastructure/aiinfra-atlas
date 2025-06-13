# Development help targets
.PHONY: help-b help-f help-d

help-b:
	@echo "Start backend development server"
	@echo "Usage: make b"
	@echo ""
	@echo "This target starts the backend development server:"
	@echo "1. Sets up the virtual environment"
	@echo "2. Installs dependencies"
	@echo "3. Starts the FastAPI server"
	@echo ""
	@echo "The server will be available at http://localhost:8000"

help-f:
	@echo "Start frontend development server"
	@echo "Usage: make f"
	@echo ""
	@echo "This target starts the frontend development server:"
	@echo "1. Checks for nvm installation"
	@echo "2. Uses the correct Node.js version"
	@echo "3. Installs dependencies if needed"
	@echo "4. Starts the Vue.js development server"
	@echo ""
	@echo "The server will be available at http://localhost:5173"
	@echo ""
	@echo "Required:"
	@echo "- nvm (Node Version Manager) installed"
	@echo "- Appropriate Node.js version installed via nvm"

help-d:
	@echo "Destroy development environment"
	@echo "Usage: make d"
	@echo ""
	@echo "This target cleans up the development environment:"
	@echo "1. Stops the FastAPI server"
	@echo "2. Removes the virtual environment"
	@echo "3. Cleans up node_modules and package-lock.json"
	@echo "4. Removes build artifacts"
	@echo "5. Cleans up telemetry database"
	@echo ""
	@echo "WARNING: This will remove all development dependencies!" 