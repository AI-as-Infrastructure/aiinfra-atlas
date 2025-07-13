# Staging Environment

This document describes the local staging environment for development and testing.

## Overview

ATLAS provides a local staging environment that allows developers to test the full application stack on their local machine. This includes:

- Complete application deployment with Nginx, Gunicorn, and Redis
- Self-signed SSL certificates for HTTPS testing
- Production-like configuration for realistic testing
- Isolated environment that doesn't interfere with development

## Local Staging

### Purpose

The local staging environment is designed for:
- Testing application functionality before deployment
- Validating configuration changes
- Development testing with production-like setup
- Training and demonstration purposes

### Configuration

- **Location**: Runs on your local machine at `https://localhost`
- **Services**: Nginx (reverse proxy), Gunicorn (backend), Redis (caching)
- **SSL**: Self-signed certificates (you'll need to accept in browser)
- **Environment**: Uses `config/.env.staging` configuration

### Deployment Process

1. **Create staging configuration**:
```bash
cp config/.env.template config/.env.staging
```

2. **Edit the staging environment file** with appropriate settings:
```bash
# Basic configuration
ENVIRONMENT=staging
VITE_API_URL=https://localhost
VITE_LOG_LEVEL=debug
BACKEND_LOG_LEVEL=debug

# Set at least one LLM API key
ANTHROPIC_API_KEY=your-key-here
# ... other configuration
```

3. **Deploy to local staging**:
```bash
make s
```

4. **Access the application**:
   - Open https://localhost in your browser
   - Accept the self-signed certificate warning
   - Application should be fully functional

5. **Clean up when done**:
```bash
make ds
```

## Remote Staging

For remote staging deployments (staging server, team testing, etc.), follow the [Production Deployment Guide](production.md) but use staging-appropriate configuration:

- Use a staging domain and environment file
- Consider using staging-specific API keys and services
- Follow the same deployment process as production
- Use appropriate security measures for your staging environment

## Service Management

The local staging environment creates the following services:

- **Gunicorn**: Backend API service running on port 8000
- **Nginx**: Frontend and reverse proxy on ports 80/443
- **Redis**: Caching and session management
- **LLM Worker**: Background worker for async processing

### Managing Services

```bash
# Check service status
sudo systemctl status gunicorn llm-worker nginx redis-server

# View logs
sudo journalctl -u gunicorn -f
sudo journalctl -u llm-worker -f

# Restart services if needed
sudo systemctl restart gunicorn llm-worker nginx
```

## Environment Configuration

Key staging environment variables:

```bash
# Core settings
ENVIRONMENT=staging
VITE_API_URL=https://localhost
VITE_LOG_LEVEL=debug
BACKEND_LOG_LEVEL=debug

# Database and caching
REDIS_PASSWORD=your-staging-password

# LLM providers (set at least one)
ANTHROPIC_API_KEY=your-staging-key
OPENAI_API_KEY=your-staging-key

# Optional features
TELEMETRY_ENABLED=true
VITE_USE_COGNITO_AUTH=false
```

## Cleanup Process

The cleanup process (`make ds`) thoroughly removes:

- All application files from `/opt/atlas`
- Service configurations from systemd
- Nginx site configurations
- Log files
- SSL certificates (self-signed)

## Best Practices

1. **Always clean up after testing**:
   ```bash
   make ds
   ```

2. **Use staging for**:
   - Testing new features before production
   - Validating configuration changes
   - Training and demonstrations
   - Development testing with production-like setup
   - Load testing and performance validation

3. **Environment isolation**:
   - Use different API keys for staging vs production
   - Use staging-specific external services where possible
   - Test with realistic data volumes

## Troubleshooting

### Common Issues

**1. Port conflicts**:
```bash
# Check what's using ports 80, 443, 8000
sudo netstat -tlnp | grep -E ':(80|443|8000)'

# Stop conflicting services
sudo systemctl stop apache2  # If Apache is running
```

**2. SSL certificate warnings**:
- This is expected with self-signed certificates
- Click "Advanced" → "Proceed to localhost (unsafe)" in your browser
- For automated testing, use `curl -k` to skip certificate verification

**3. Service startup issues**:
```bash
# Check specific service logs
sudo journalctl -u gunicorn --no-pager
sudo journalctl -u nginx --no-pager

# Verify configuration
sudo nginx -t
```

**4. Permission errors**:
```bash
# Ensure proper ownership
sudo chown -R $(whoami):$(whoami) /opt/atlas
```

### Log Locations

- **Application logs**: `/var/log/atlas/`
- **Nginx logs**: `/var/log/nginx/`
- **System logs**: `sudo journalctl -u <service-name>`

## Load Testing

The staging environment is ideal for load testing because:

### Advantages for Load Testing

- **Authentication can be disabled**: Set `VITE_USE_COGNITO_AUTH=false` to bypass login requirements
- **Flexible deployment**: Deploy on VMs or machines with different specifications to test performance
- **Production-like setup**: Tests the full application stack (Nginx, Gunicorn, Redis, LLM workers)
- **Isolated environment**: Load testing won't affect production users or data

### Load Testing Setup

For load testing, configure your staging environment:

```bash
# Disable authentication for load testing
VITE_USE_COGNITO_AUTH=false

# Optimize for concurrent users
GUNICORN_WORKERS=8
LLM_MAX_CONCURRENT=20
RATE_LIMIT_PER_MINUTE=240

# Reduce logging overhead during load testing
VITE_LOG_LEVEL=error
BACKEND_LOG_LEVEL=error
```

### Running Load Tests

```bash
# Deploy staging environment
make s

# Run load test (see load testing docs for full details)
make lts
```

### Hardware Testing

Test different machine specifications by deploying staging on various systems:

- **8 vCPU, 16GB RAM**: Recommended production specification
- **4 vCPU, 8GB RAM**: Minimum viable configuration  
- **16 vCPU, 32GB RAM**: High-performance configuration

Monitor CPU, memory, and response times during load testing to optimize for your target hardware.

For comprehensive load testing documentation, see the [Load Testing Framework](load_testing.md) guide.

## Additional Resources

For additional troubleshooting, refer to the [Production Deployment Guide](production.md) troubleshooting section. 