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

This tool has been hardened for protoytpe use with authenticated users and small user groups for limited periods.

**Prerequisites:**
- Configured environment file based on `.env.template`
- Server with SSH access and sudo privileges
- Domain with DNS configured

**Deployment:**
Run the production deployment script on your target server:

```bash
make p
```

For enterprise deployments, we recommend additional security hardening, load testing, and security review.

### Verify Deployment

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

For staging deployments, see the [Staging Environment Guide](staging.md).

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ENVIRONMENT` | Deployment environment | `production` |
| `VITE_API_URL` | Frontend API URL | `https://your-domain.com` |
| `REDIS_PASSWORD` | Redis authentication password | `secure-random-password` |
| `PHOENIX_SPACE_ID` | Phoenix space identifier | `aiinfra` |
| `PHOENIX_COLLECTOR_ENDPOINT` | Phoenix space endpoint | `https://app.phoenix.arize.com/s/aiinfra` |

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
# Phoenix Spaces Configuration
# Configure for your own Phoenix space
PHOENIX_SPACE_ID=aiinfra
PHOENIX_API_KEY=your_phoenix_api_key
PHOENIX_CLIENT_HEADERS="Authorization=Bearer your_phoenix_api_key"
PHOENIX_PROJECT_NAME=ATLAS-Prod
PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"
```
**Note**: Create your own Phoenix space at https://app.phoenix.arize.com and configure these variables with your space ID and API keys. Different environments (Dev/Staging/Prod) should use different `PHOENIX_PROJECT_NAME` values within the same space.

**Production Phoenix Setup Checklist:**
1. Verify `PHOENIX_SPACE_ID=aiinfra` is set in `.env.production`
2. Verify `PHOENIX_COLLECTOR_ENDPOINT` uses the space-based URL: `https://app.phoenix.arize.com/s/aiinfra`
3. Confirm your API key has write access to the `aiinfra` space
4. After deployment, verify traces appear at `https://app.phoenix.arize.com/s/aiinfra/projects`
5. Test backup script connectivity: `make backup-prod`

**Authentication (AWS Cognito):**
```bash
VITE_USE_COGNITO_AUTH=true
VITE_COGNITO_REGION=us-west-1
VITE_COGNITO_USERPOOL_ID=us-west-1_...
VITE_COGNITO_CLIENT_ID=...
```

### Runtime System Configuration Options

ATLAS supports runtime system toggles persisted in `config/system_settings.json`:

- `telemetryEnabled`
- `interRaterEnabled`

Configuration precedence is:

1. Environment variables
2. `config/system_settings.json`
3. Built-in defaults

For production, keep environment overrides explicit for critical controls.

### System Configuration API Endpoint

Authenticated endpoint:

- `POST /api/system/configuration`

Request body:

```json
{
	"telemetryEnabled": true,
	"interRaterEnabled": false
}
```

Related endpoints:

- `GET /api/system/configuration`
- `POST /api/system/configuration/reload`

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