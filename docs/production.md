# ATLAS Deployment Guide

This guide covers deploying ATLAS to production and staging environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Production Deployment](#production-deployment)
- [Staging Deployment](#staging-deployment)
- [Environment Configuration](#environment-configuration)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Ubuntu 20.04+ or compatible Linux distribution
- Minimum 8GB RAM, 4 CPU cores recommended
- 20GB+ available disk space
- Domain name with DNS configured
- SSL certificate support (Let's Encrypt)

### Required Software

The deployment script automatically installs:
- Python 3.10
- Node.js 22.14.0
- Nginx
- Redis
- Git LFS
- Build tools

### Access Requirements

- SSH access to the target server
- Sudo privileges on the target server
- Domain DNS pointing to the server IP

## Production Deployment

### 1. Environment Configuration

Create your production environment file:

```bash
cp config/.env.template config/.env.production
```

Edit `config/.env.production` with your production settings:

```bash
# Core Configuration
ENVIRONMENT=production
VITE_LOG_LEVEL=error
BACKEND_LOG_LEVEL=error

# Frontend Configuration
VITE_SITE_TITLE="Your Site Title"
VITE_API_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com

# Security
REDIS_PASSWORD=your-secure-redis-password

# LLM API Keys (set at least one)
ANTHROPIC_API_KEY=your-anthropic-key
OPENAI_API_KEY=your-openai-key
GOOGLE_API_KEY=your-google-key

# Optional: AWS Bedrock Configuration
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret

# Optional: Observability (Arize Phoenix)
PHOENIX_CLIENT_HEADERS="api_key=your-phoenix-key"
PHOENIX_PROJECT_NAME=your-project-name

# Optional: Authentication (AWS Cognito)
VITE_USE_COGNITO_AUTH=true
VITE_COGNITO_REGION=your-region
VITE_COGNITO_USERPOOL_ID=your-pool-id
VITE_COGNITO_CLIENT_ID=your-client-id
```

### 2. Deploy to Server

**Step 1: Clone repository to production location**

SSH into your server and clone directly to `/opt/atlas`:

```bash
ssh user@your-server.com
sudo git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas.git /opt/atlas
sudo chown -R $(whoami):$(whoami) /opt/atlas
cd /opt/atlas
git lfs pull
```

**Step 2: Copy environment configuration**

From your local machine, copy the production environment file:

```bash
scp config/.env.production user@your-server.com:/opt/atlas/config/.env.production
```

**Step 3: Run deployment**

SSH back into the server and run the deployment:

```bash
ssh user@your-server.com
cd /opt/atlas
make p
```

The deployment script will:
- Install all system dependencies
- Set up Python 3.10 virtual environment
- Install Node.js 22.14.0 via nvm
- Configure Redis with authentication
- Build the frontend application
- Set up Let's Encrypt SSL certificates
- Configure Nginx reverse proxy
- Create and start systemd services
- Configure automatic service startup

### 3. Verify Deployment

After deployment completes, verify the services:

```bash
# Check service status
sudo systemctl status gunicorn llm-worker nginx redis-server

# Check application logs
sudo tail -f /var/log/atlas/gunicorn-access.log
sudo tail -f /var/log/atlas/gunicorn-error.log

# Test the application
curl -I https://your-domain.com
```

Your application should now be available at `https://your-domain.com`.

## Staging Deployment

For staging deployments, use the staging scripts:

```bash
# Local staging (for development)
make sl

# Remote staging server
cp config/.env.template config/.env.staging
# Edit config/.env.staging with staging settings
make sr
```

Staging deployments use self-signed certificates and are optimized for testing.

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `VITE_API_URL` | Frontend API URL | `https://your-domain.com` |
| `REDIS_PASSWORD` | Redis authentication password | `secure-random-password` |

### LLM Configuration

Set at least one LLM provider:

```bash
# Anthropic Claude (recommended)
ANTHROPIC_API_KEY=sk-ant-api03-...

# OpenAI GPT
OPENAI_API_KEY=sk-proj-...

# Google Gemini
GOOGLE_API_KEY=AIzaSy...
```

### Optional Features

**AWS Bedrock Integration:**
```bash
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
```

**Observability (Arize Phoenix):**
```bash
PHOENIX_CLIENT_HEADERS="api_key=your-key"
PHOENIX_PROJECT_NAME=your-project
PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com"
```

**Authentication (AWS Cognito):**
```bash
VITE_USE_COGNITO_AUTH=true
VITE_COGNITO_REGION=us-west-1
VITE_COGNITO_USERPOOL_ID=us-west-1_...
VITE_COGNITO_CLIENT_ID=...
```

## Maintenance

### Updating the Application

To update to the latest version:

```bash
cd /opt/atlas
git pull origin main
git lfs pull
make p
```

### Managing Services

```bash
# Start/stop services
sudo systemctl start gunicorn llm-worker
sudo systemctl stop gunicorn llm-worker

# View logs
sudo journalctl -u gunicorn -f
sudo journalctl -u llm-worker -f

# Restart services
sudo systemctl restart gunicorn llm-worker nginx
```

### SSL Certificate Renewal

Let's Encrypt certificates are automatically renewed. To manually renew:

```bash
sudo certbot renew
sudo systemctl reload nginx
```

### Cleaning Up

To completely remove the production deployment:

```bash
cd /opt/atlas
make dp
```

This will stop all services, remove files, and clean up configurations.

## Troubleshooting

### Common Issues

**1. Node.js Version Mismatch**
```bash
# The deployment script handles this automatically
# If you see version errors, ensure nvm is properly configured
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 22.14.0
```

**2. Permission Errors**
```bash
# Ensure proper ownership
sudo chown -R $(whoami):$(whoami) /opt/atlas
```

**3. SSL Certificate Issues**
```bash
# Manually run certbot if automatic setup fails
sudo certbot --nginx -d your-domain.com
```

**4. Service Startup Issues**
```bash
# Check service logs
sudo journalctl -u gunicorn --no-pager
sudo journalctl -u llm-worker --no-pager

# Verify environment file
cat /opt/atlas/config/.env.production
```

### Log Locations

- **Application logs:** `/var/log/atlas/`
- **Nginx logs:** `/var/log/nginx/`
- **System logs:** `sudo journalctl -u servicename`

### Performance Monitoring

The application includes built-in telemetry when configured with Arize Phoenix. Monitor:
- Response times
- Error rates
- LLM token usage
- User interaction patterns

### Security Considerations

- Keep API keys secure and rotate regularly
- Monitor access logs for unusual activity
- Keep the system updated with security patches
- Use strong passwords for Redis and other services
- Consider implementing rate limiting for public deployments

## Support

For deployment issues:
1. Check the logs first
2. Verify environment configuration
3. Ensure all required services are running
4. Check DNS and SSL certificate status

For application-specific issues, refer to the main README and application documentation.