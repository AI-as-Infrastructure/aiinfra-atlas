# Staging Environments

This document describes the staging environments and deployment processes for the Atlas application.

## Overview

We maintain two staging environments:

1. **Local Staging** (`make sl`): Runs on your local machine
2. **Remote Staging** (`make sr`): Runs on a dedicated staging server

## Remote Staging (Recommended)

The remote staging environment is the primary staging environment and should be used for most testing and validation.

### Configuration

- Server: Dedicated staging server at `192.168.20.17`
- User: `atlas_deploy` with passwordless sudo access
- Domain: Configured in `config/.env.staging`

### Required Setup

The `atlas_deploy` user requires passwordless sudo access for automated deployment and cleanup. This is safe given:
- Staging server is on local network only
- No sensitive production data
- Production uses AWS SSO instead

⚠️ **Security Warning**: Passwordless sudo should NEVER be configured on:
- Public-facing servers
- Servers accessible from the internet
- Servers containing sensitive data
- Production environments

To configure passwordless sudo:
```bash
# SSH into staging server
ssh atlas_deploy@192.168.20.17

# Configure passwordless sudo
echo "atlas_deploy ALL=(ALL) NOPASSWD: ALL" | sudo tee /etc/sudoers.d/atlas_deploy
sudo chmod 440 /etc/sudoers.d/atlas_deploy
```

### Deployment Process

1. Build and deploy:
```bash
make sr
```

2. Clean up environment:
```bash
make dsr
```

### Key Features

- Mirrors production environment more closely
- Tests deployment process
- Validates server configuration
- Tests domain and SSL setup

## Local Staging (Development)

The local staging environment is useful for quick testing during development but has limitations.

### Configuration

- Runs on your local machine
- Uses local ports and services
- No domain or SSL configuration

### Deployment Process

1. Build and deploy:
```bash
make sl
```

2. Clean up environment:
```bash
make dsl
```

### Limitations

- Doesn't test server configuration
- No domain/SSL testing
- May have different behavior than production
- Services might conflict with local development

## Environment Files

- `config/.env.staging`: Used for both local and remote staging
- Environment variables are automatically adjusted based on deployment target

## Service Management

Both environments use the same service configuration:

- Gunicorn: Backend API service
- Nginx: Frontend and reverse proxy
- Redis: Caching and session management

## Cleanup Process

The cleanup process is thorough and removes:

- All application files
- Service configurations
- Log files
- Systemd service files

## Best Practices

1. Use remote staging for:
   - Pre-production testing
   - Team-wide validation
   - Deployment process testing
   - Domain/SSL testing

2. Use local staging for:
   - Quick development testing
   - Isolated feature testing
   - When remote staging is unavailable

3. Always clean up environments after testing:
   - `make dsl` for local staging
   - `make dsr` for remote staging

## Troubleshooting

### Common Issues

1. Port conflicts in local staging:
   - Check if ports 80, 443, 8000 are available
   - Stop any conflicting services

2. Remote staging access:
   - Ensure SSH access to staging server
   - Verify `atlas_deploy` user permissions
   - Check environment file configuration
   - If sudo commands fail, verify passwordless sudo is configured

3. Service issues:
   - Check service logs: `journalctl -u <service>`
   - Verify service status: `systemctl status <service>`
   - Check Nginx configuration: `nginx -t` 