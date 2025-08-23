# Phoenix Telemetry Backups

ATLAS automatically backs up Phoenix telemetry data to preserve spans, annotations, and datasets for analysis and compliance purposes.

## Overview

The backup system exports complete Phoenix project data to dated folders, creating a historical archive of telemetry information. Backups include spans with merged annotations and datasets in both Parquet and CSV formats.

## Configuration

Backup settings are configured in your environment file (`.env.production` for production):

```bash
# Required: Projects to backup (comma-separated)
PHOENIX_PROJECT_BACKUPS=ATLAS-Hansard-Prod,Darwin-Prod

# Required: Base backup directory
PHOENIX_BACKUP_PATH="/path/to/your/backup/directory"

# Required: Phoenix API authentication
PHOENIX_CLIENT_HEADERS="api_key=your_phoenix_api_key"
PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com"

# Optional: Control what gets exported
PHOENIX_EXPORT_ANNOTATIONS=true  # Include span annotations (default: true)
PHOENIX_EXPORT_DATASETS=true     # Include datasets (default: true)  
PHOENIX_EXPORT_CSV=true          # Export CSV in addition to Parquet (default: true)
```

## Backup Structure

Backups are organized by date with the following structure:

```
backup_directory/
└── phoenix/
    └── YYYY/
        └── MM/
            └── DD/
                ├── Project-Name-1/
                │   ├── spans.parquet      # Spans with merged annotations
                │   ├── spans.csv          # Same data in CSV format
                │   ├── datasets.parquet   # Project datasets
                │   └── datasets.csv       # Same data in CSV format
                └── Project-Name-2/
                    ├── spans.parquet
                    ├── spans.csv
                    └── ...
```

## Manual Backup

Run a manual backup:

```bash
# Backup all configured projects
make backup-prod
```

The script will:
1. Load configuration from `config/.env.production`
2. Connect to Phoenix using your API key
3. Export all spans with merged annotations
4. Export datasets separately
5. Save to dated folders under your backup path

## Automated Backups

### Cron Setup

For automated daily backups, set up a cron job:

```bash
# Edit your crontab
crontab -e

# Add this line to run backups daily at 1:20 AM
20 1 * * * cd /path/to/aiinfra-atlas && /usr/bin/make backup-prod >> /path/to/backup.log 2>&1
```

**Important**: Replace `/path/to/aiinfra-atlas` with your actual project directory path.

### Cron Environment

Cron runs with minimal environment variables. Ensure your cron command:
- Changes to the correct project directory (`cd /path/to/project`)
- Uses absolute paths (`/usr/bin/make`)
- Redirects output to a log file for debugging

## Data Formats

**Parquet Files:**
- Efficient binary format
- Preserves data types
- Smaller file sizes
- Recommended for analysis

**CSV Files:**
- Human-readable text format
- Compatible with spreadsheet software
- Larger file sizes
- Good for manual inspection

## Troubleshooting

**Backup fails with authentication error:**
- Verify `PHOENIX_CLIENT_HEADERS` contains correct API key
- Check `PHOENIX_COLLECTOR_ENDPOINT` points to correct Phoenix instance
- Ensure API key has proper project access permissions

**Cron backup not running:**
- Check cron is running: `systemctl status cron`
- Verify cron job syntax: `crontab -l`
- Check log file for error messages
- Test manual backup first: `make backup-prod`

**No data in backups:**
- Confirm project names in `PHOENIX_PROJECT_BACKUPS` match Phoenix exactly
- Check if projects contain data in Phoenix UI
- Verify date ranges and time zones

**Permission errors:**
- Ensure backup directory is writable
- Check file system permissions
- Verify disk space availability

## Backup Script Details

The backup system uses `utils/scripts/phoenix_backup_prod.py`, which:

1. **Loads Environment**: Reads configuration from `config/.env.production`
2. **Authenticates**: Creates Phoenix client with API key from `PHOENIX_CLIENT_HEADERS`
3. **Discovers Projects**: Uses projects listed in `PHOENIX_PROJECT_BACKUPS`
4. **Exports Data**: Downloads complete spans dataframes for each project
5. **Merges Annotations**: Combines span annotations with spans on matching IDs
6. **Saves Files**: Writes both Parquet and CSV formats to dated directories

The script handles errors gracefully, continuing with other projects if one fails, and provides detailed logging for troubleshooting.