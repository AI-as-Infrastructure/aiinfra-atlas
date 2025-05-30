# === PRODUCTION DEPLOYMENT TARGETS ===
# These targets deploy to production AWS environment using CloudFormation

.PHONY: prod-server dprod-server prod

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
	@read -p "" confirm && [[ $$confirm == [yY] || $$confirm == [yY][eE][sS] ]] || exit 1
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
