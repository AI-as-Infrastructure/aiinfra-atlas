# System Health Monitoring

ATLAS includes a comprehensive health monitoring system to help administrators track system health, diagnose issues, and ensure optimal performance in production environments.

## Overview

The health check system monitors:
- **System Resources**: Disk space, memory usage, CPU load
- **Services**: nginx, gunicorn, Redis, LLM workers
- **Application Health**: Configuration files, vector store, Python environment
- **Network**: DNS resolution, port availability
- **Logs**: Recent errors and critical issues
- **Redis**: Connection, memory usage, client connections

## Quick Start

### Basic Health Check
```bash
# Run standard health check
make health

# Or directly:
./utils/scripts/health_check.sh
```

### Detailed Information
```bash
# Verbose output with detailed metrics
make health-verbose

# JSON output for monitoring systems
make health-json

# Show only critical issues
make health-critical
```

## Command Line Options

| Option | Short | Description |
|--------|-------|-------------|
| `--verbose` | `-v` | Show detailed output including metrics and timestamps |
| `--json` | `-j` | Output results in JSON format for monitoring integration |
| `--critical-only` | `-c` | Display only critical issues, hide warnings and info |
| `--help` | `-h` | Show usage information |

## Output Examples

### Standard Output
```bash
$ make health

🏥 Running system health check...

=== Permission Check ===
ℹ Running with appropriate permissions (atlas_deploy/sudo group)

=== Disk Space ===
✅ Root filesystem usage OK: 65%
✅ Application filesystem usage OK: 45%
✅ No large log files detected

=== Memory Usage ===
✅ Memory usage OK: 72% (1.2GB available)

=== System Services ===
✅ nginx is running
✅ gunicorn is running
✅ redis-server is running
⚠️ llm-worker is not running

=== Redis Health ===
✅ Redis connection OK

=== Network Connectivity ===
✅ DNS resolution working
✅ Web server ports are listening

=== System Load ===
✅ System load OK: 0.85 (21% of 4 cores)

=== Application Health ===
✅ Application directory exists: /opt/atlas
✅ Python virtual environment exists
✅ Production configuration exists
✅ Main application file exists
✅ Vector store directory exists

=== Health Check Summary ===
Timestamp: Thu Nov 14 16:45:23 UTC 2025
Hostname: atlas-prod

WARNINGS:
  ⚠️ llm-worker is not running

⚠️ SYSTEM OK WITH WARNINGS

Run with --verbose for detailed output
Run with --json for machine-readable output
Run with --critical-only to see only critical issues
```

### JSON Output
```bash
$ make health-json
{
  "timestamp": "2025-11-14T16:45:23+00:00",
  "hostname": "atlas-prod",
  "status": "OK",
  "critical_issues": [],
  "warnings": ["llm-worker is not running"],
  "info": ["Running with appropriate permissions (atlas_deploy/sudo group)"]
}
```

## Monitoring Integration

### Exit Codes
- **0**: System healthy (may have warnings)
- **1**: Critical issues detected

### Automated Monitoring
The JSON output and exit codes make the health check ideal for integration with monitoring systems:

```bash
#!/bin/bash
# Example monitoring script

# Run health check and capture output
health_output=$(./utils/scripts/health_check.sh --json)
health_status=$?

if [[ $health_status -eq 1 ]]; then
    # Critical issues detected - send alert
    echo "$health_output" | jq '.critical_issues[]' | \
        xargs -I {} echo "CRITICAL: {}" | \
        mail -s "ATLAS System Critical" admin@example.com
fi
```

### Cron Job Setup
```bash
# Add to crontab for regular health checks
# Check every 15 minutes, log critical issues
*/15 * * * * /opt/atlas/utils/scripts/health_check.sh --critical-only >> /var/log/atlas-health.log 2>&1

# Daily comprehensive report
0 8 * * * /opt/atlas/utils/scripts/health_check.sh --verbose | mail -s "Daily ATLAS Health Report" admin@example.com
```

## Health Check Categories

### System Resources

**Disk Space**
- Root filesystem usage (critical >90%, warning >80%)
- Application directory usage
- Large log file detection (>100MB)

**Memory**
- RAM usage percentage
- Available memory in MB
- Total, used, and available memory statistics

**CPU Load**
- 1-minute load average
- Load percentage relative to CPU cores
- Historical load averages (5min, 15min) in verbose mode

### Services

**Web Server (nginx)**
- Service status and uptime
- Process listening on web ports (80, 443, 8000)

**Application Server (gunicorn)**
- Service status and uptime
- Worker process health

**Background Workers (llm-worker)**
- Service status and uptime
- Worker availability for LLM requests

**Database (Redis)**
- Service status
- Connection test with authentication
- Memory usage and client connections (verbose mode)

### Application Health

**File System**
- Application directory structure
- Python virtual environment
- Configuration files
- Vector store availability

**Configuration**
- Production environment file validation
- Required environment variables
- Redis connection configuration

### Network & Connectivity

**DNS Resolution**
- External DNS query test
- Network connectivity validation

**Port Availability**
- Web server port listening status
- Application port accessibility

### Log Analysis

**System Logs**
- Recent errors in systemd journals
- Service-specific error counts
- Critical log pattern detection

**Application Logs**
- Error patterns in application logs
- Recent exception tracking
- Log file size monitoring

## Troubleshooting

### Common Issues

**Permission Errors**
```bash
# If running as non-privileged user
sudo ./utils/scripts/health_check.sh

# Or add user to appropriate groups
sudo usermod -a -G atlas_deploy $USER
```

**Redis Connection Failed**
- Verify Redis is running: `systemctl status redis-server`
- Check configuration in `/opt/atlas/config/.env.production`
- Test connection manually: `redis-cli -a "your_password" ping`

**Service Not Running**
```bash
# Check service status
systemctl status gunicorn
systemctl status llm-worker

# Restart services if needed
sudo systemctl restart gunicorn llm-worker
```

**High Resource Usage**
- Use `--verbose` flag for detailed resource information
- Check specific processes: `top`, `htop`, `ps aux`
- Review log files for resource-intensive operations

### Debug Mode

For troubleshooting the health check script itself:
```bash
# Run with bash debug mode
bash -x ./utils/scripts/health_check.sh --verbose

# Check script permissions
ls -la ./utils/scripts/health_check.sh

# Verify dependencies
which redis-cli systemctl journalctl
```

## Best Practices

### Regular Monitoring
1. **Automated Checks**: Set up cron jobs for regular monitoring
2. **Alert Thresholds**: Configure alerts for critical issues
3. **Historical Tracking**: Log health check results for trend analysis
4. **Escalation**: Define escalation procedures for critical alerts

### Performance Optimization
1. **Resource Thresholds**: Adjust warning/critical thresholds based on your environment
2. **Service Dependencies**: Ensure all required services are configured
3. **Log Rotation**: Implement log rotation to prevent disk space issues
4. **Capacity Planning**: Monitor trends to plan resource upgrades

### Security Considerations
1. **Credential Protection**: Health check uses production Redis credentials securely
2. **Log Sensitivity**: Be cautious about logging sensitive information
3. **Access Control**: Limit health check script access to appropriate users
4. **Network Security**: Health check performs external DNS queries

## Integration Examples

### Nagios/Icinga
```bash
# /etc/nagios/commands.cfg
define command{
    command_name    check_atlas_health
    command_line    /opt/atlas/utils/scripts/health_check.sh --critical-only
}
```

### Prometheus
```bash
# Export metrics for Prometheus scraping
#!/bin/bash
health_output=$(./utils/scripts/health_check.sh --json)
echo "atlas_health_status $(echo "$health_output" | jq -r '.status == "OK"')"
echo "atlas_critical_issues $(echo "$health_output" | jq -r '.critical_issues | length')"
echo "atlas_warnings $(echo "$health_output" | jq -r '.warnings | length')"
```

### Slack Integration
```bash
#!/bin/bash
# Send health check results to Slack
health_output=$(./utils/scripts/health_check.sh --json)
if [[ $(echo "$health_output" | jq -r '.critical_issues | length') -gt 0 ]]; then
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"ATLAS Critical Issues: $(echo "$health_output" | jq -r '.critical_issues[]')\"}" \
        YOUR_SLACK_WEBHOOK_URL
fi
```

## Related Documentation

- [Production Deployment](production.md) - Production setup and configuration
- [Development](development.md) - Development environment setup
- [Configuration](configuration.md) - Environment and configuration management
- [Load Testing](load_testing.md) - Performance testing and optimization