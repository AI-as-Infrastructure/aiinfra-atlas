# ATLAS Deployment Guide

This guide covers deploying ATLAS to production and staging environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Corpus Setup](#corpus-setup)
- [Production Deployment](#production-deployment)
- [Staging Deployment](#staging-deployment)
- [SSL Configuration](#ssl-configuration)
- [Systemd Services](#systemd-services)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- Linux server (Ubuntu 22.04+ recommended)
- Python 3.10
- Node.js 22.14.0
- Redis server
- nginx (for reverse proxy and SSL)
- Domain name with DNS configured

### Environment Setup

```bash
# Clone repository
git clone https://github.com/AI-as-Infrastructure/aiinfra-atlas.git /opt/atlas
cd /opt/atlas

# Copy and configure production environment
cp config/.env.template config/.env.production
# Edit config/.env.production with production values
```

## Corpus Setup

Before deploying, you must build a corpus via the wizard:

### Development Machine (Recommended)

1. Build the corpus locally using the wizard:
   ```bash
   make b  # Start backend
   make f  # Start frontend
   # Open http://localhost:5173, run Corpus Wizard, enter Deploy Mode
   ```
2. Copy the built corpus to the production server:
   ```bash
   scp -r backend/corpus/ user@production:/opt/atlas/backend/corpus/
   scp backend/targets/*.txt user@production:/opt/atlas/backend/targets/
   ```

### Production Server (Alternative)

Run the wizard directly on the production server in configure mode, then enter deploy mode before switching to production deployment.

### Deployment Checklist

Before proceeding with deployment:
- [ ] Corpus built via wizard (or copied from development)
- [ ] `backend/corpus/manifest.json` exists
- [ ] `backend/corpus/corpus_active.json` exists (or will be created by deploy mode)
- [ ] `backend/corpus/chroma_db/` populated
- [ ] Test target file exists in `backend/targets/`
- [ ] `config/.env.production` configured with API keys, Redis, telemetry
- [ ] `TEST_TARGET` set in `.env.production`

## Production Deployment

### Quick Deploy

```bash
make p  # Full production deployment
```

This command:
1. Sets up the Python virtual environment
2. Installs dependencies from `pyproject.toml`
3. Builds the frontend for production
4. Configures gunicorn with production settings
5. Sets up systemd services
6. Configures nginx

### Manual Deployment Steps

```bash
# 1. Create virtual environment
python3.10 -m venv .venv
source .venv/bin/activate
uv pip install -e ".[cpu]"  # or [gpu] for GPU support

# 2. Build frontend
cd frontend
npm install
npm run build
cd ..

# 3. Configure nginx
sudo cp deploy/production/nginx.conf /etc/nginx/sites-available/atlas
sudo ln -sf /etc/nginx/sites-available/atlas /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 4. Configure systemd services
sudo cp deploy/production/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable atlas-backend atlas-worker
sudo systemctl start atlas-backend atlas-worker
```

## Staging Deployment

### Local Staging

```bash
make sl  # Deploy to local staging
```

### Remote Staging

```bash
make sr  # Deploy to remote staging server
```

Staging uses `config/.env.staging` with separate telemetry project names and relaxed authentication.

## SSL Configuration

### Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d atlas.example.com

# Auto-renewal is configured automatically
```

### Manual SSL

Place certificates in `deploy/certs/` and update nginx configuration.

## Systemd Services

### Backend Service

The backend runs via gunicorn with settings from `.env.production`:

```ini
[Unit]
Description=ATLAS Backend
After=network.target redis.service

[Service]
Type=notify
User=atlas
Group=atlas
WorkingDirectory=/opt/atlas
ExecStart=/opt/atlas/.venv/bin/gunicorn backend.main:app
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

### Service Management

```bash
# Status
sudo systemctl status atlas-backend

# Restart
sudo systemctl restart atlas-backend

# Logs
sudo journalctl -u atlas-backend -f
```

## Maintenance

### Health Checks

```bash
make health          # Basic health check
make health-verbose  # Detailed output
make health-json     # Machine-readable output
```

See [Health Monitoring](health_monitoring.md) for full details.

### Telemetry Backups

```bash
make backup-prod  # Backup Phoenix telemetry data
```

See [Backups](backups.md) for scheduling and configuration.

### Corpus Updates

To update the corpus in production:
1. Build a new corpus on a development machine via the wizard
2. Stop the production backend: `sudo systemctl stop atlas-backend`
3. Copy the new corpus: `scp -r backend/corpus/ user@production:/opt/atlas/backend/corpus/`
4. Restart: `sudo systemctl start atlas-backend`

Alternatively, use the configuration export/import API (see [Configuration Guide](configuration.md)).

### Log Rotation

Application logs should be rotated to prevent disk space issues:

```bash
# /etc/logrotate.d/atlas
/var/log/atlas/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
}
```

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check `.env.production` is configured
- Verify `backend/corpus/corpus_active.json` exists
- Check Redis is running: `systemctl status redis-server`
- Review logs: `journalctl -u atlas-backend -n 50`

**Corpus not loading:**
- Verify `backend/corpus/manifest.json` exists
- Check `corpus_active.json` has valid paths
- Ensure retriever adapter exists in `backend/corpus/`

**502 Bad Gateway:**
- Backend not running or crashing on startup
- Check gunicorn logs: `journalctl -u atlas-backend`
- Verify nginx proxy settings

**Authentication issues:**
- Verify Cognito configuration in `.env.production`
- Check `VITE_USE_COGNITO_AUTH=true`
- Test with authentication disabled first

**Memory issues:**
- Adjust `GUNICORN_WORKERS` and `GUNICORN_MAX_WORKER_MEMORY_MB`
- Monitor with `make health-verbose`

## Related Documentation

- [Configuration Guide](configuration.md) - Environment files and configuration
- [Health Monitoring](health_monitoring.md) - System health checks
- [Staging Environment](staging.md) - Staging deployment
- [Development Guide](development.md) - Development setup
- [Backups](backups.md) - Telemetry data backups
