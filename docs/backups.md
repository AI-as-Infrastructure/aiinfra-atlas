# Phoenix Telemetry Backups

ATLAS automatically backs up Phoenix telemetry data to preserve spans with merged annotations for analysis and compliance purposes. These backups serve as the data source for comprehensive analysis workflows including visualization generation and performance monitoring.

## Overview

The backup system exports complete Phoenix project data to dated folders, creating a historical archive of telemetry information. All user feedback annotations (including ratings, explanations, and notes) are merged directly into the spans export for immediate analysis. This integrated approach enables seamless transitions from data collection to insights generation.

## Backup and Analysis Workflow

### Complete Data-to-Insights Pipeline

```bash
# 1. Collect fresh telemetry data
make backup-prod

# 2. Generate comprehensive analysis with visualizations  
make hansard-analysis       # Parliamentary analysis

# 3. Review results in analysis/output/
```

### Automated Scheduling
The backup system supports automated workflows:
```bash
# Weekly comprehensive analysis (recommended)
0 2 * * 1 cd /path/to/atlas && make backup-prod && make hansard-analysis

# Daily data collection only
0 1 * * * cd /path/to/atlas && make backup-prod
```

## Configuration

Backup settings are configured in your environment file (`.env.production` for production):

```bash
# Required: Projects to backup (comma-separated)
PHOENIX_PROJECT_BACKUPS=ATLAS-Prod

# Required: Base backup directory
PHOENIX_BACKUP_DIR=./backend/telemetry/backup

# Required: Phoenix Spaces Configuration
# Created by AIINFRA (https://aiinfra.anu.edu.au) - configure for your own Phoenix space
PHOENIX_SPACE_ID=aiinfra
PHOENIX_API_KEY="your_phoenix_api_key"
PHOENIX_CLIENT_HEADERS="Authorization=Bearer your_phoenix_api_key"
PHOENIX_COLLECTOR_ENDPOINT="https://app.phoenix.arize.com/s/aiinfra"

# Optional: Control what gets exported
PHOENIX_EXPORT_ANNOTATIONS=true  # Include span annotations (default: true)
PHOENIX_EXPORT_DATASETS=true     # Include datasets (default: true)
PHOENIX_EXPORT_CSV=true          # Export CSV in addition to Parquet (default: true)
```

**Note**: Configure `PHOENIX_SPACE_ID` and `PHOENIX_PROJECT_BACKUPS` to match your Phoenix space and project names.

## Data Structure and Analysis Integration

### Backup Directory Structure

Backups are organized by date for easy historical analysis:

```
backend/telemetry/backup/
└── phoenix/
    └── YYYY/
        └── MM/
            └── DD/
                ├── Hansard-Prod/              # Parliamentary data
                │   ├── spans.parquet          # Analysis-ready data
                │   └── spans.csv              # Human-readable format
```

### Data Schema for Analysis

Each spans file includes merged annotation data optimized for analysis:
- **annotation_name**: Feedback type ("Query Difficulty", "Analysis Quality", "Relevance Rating")
- **result.score**: Numeric rating (1-5 scale)
- **result.label**: Categorical assessment
- **result.explanation**: Detailed user feedback text
- **attributes.qa_id**: Session identifier for tracking
- **attributes.input.value**: Original user question
- **attributes.output.value**: System response
- **created_at**: Timestamp for trend analysis

Spans with multiple annotations appear as multiple rows (one per annotation), enabling easy filtering and analysis of specific feedback types.

## Analysis Integration

### From Backup to Insights

The backup system is designed to feed directly into ATLAS analysis workflows:

1. **Data Collection**: `make backup-prod` downloads latest telemetry
2. **Analysis Generation**: `make hansard-analysis` processes backup data  
3. **Visualization Creation**: Automatic generation of charts and dashboards
4. **Report Generation**: Markdown and JSON outputs for reporting

### Analysis Outputs

Each analysis run produces:
```
analysis/output/
├── hansard_analysis_summary_YYYYMMDD_HHMMSS.md     # Executive summary
├── hansard_analysis_data_YYYYMMDD_HHMMSS.json      # Raw metrics
└── figures_YYYYMMDD_HHMMSS/                        # Professional visualizations
    ├── feedback_scores_distribution.png
    ├── response_time_analysis.png
    ├── qa_patterns.png
    ├── feedback_trends.png
    └── comprehensive_dashboard.png
```

### Performance Metrics Tracked

- **User Feedback**: Quality ratings across 7 dimensions
- **System Performance**: Response times, error rates, throughput
- **Content Analysis**: Question types, parliamentary vs general queries
- **User Behavior**: Expertise levels, interaction patterns

## Manual Operations

### Run Manual Backup

```bash
# Backup all configured projects
make backup-prod
```

The script will:
1. Load configuration from `config/.env.production`
2. Connect to Phoenix using your API key
3. Export all spans for each project  
4. Fetch and merge all user feedback annotations into spans
5. Save combined data to dated folders under your backup path
6. Generate both Parquet (analysis-optimized) and CSV (human-readable) formats

### Trigger Analysis After Backup

```bash
# Complete workflow: backup and analyze
make backup-prod && make hansard-analysis

# Check specific analysis results
ls analysis/output/hansard_analysis_*
```

## Automated Backup and Analysis

### Cron Setup Options

**Option 1: Daily backups only**
```bash
# Edit your crontab
crontab -e

# Add this line to run backups daily at 1:20 AM
20 1 * * * cd /path/to/atlas && /usr/bin/make backup-prod >> /path/to/backup.log 2>&1
```

**Option 2: Weekly backup with analysis** (Recommended)
```bash
# Weekly comprehensive analysis (Mondays at 2:00 AM)
0 2 * * 1 cd /path/to/atlas && /usr/bin/make backup-prod && /usr/bin/make hansard-analysis >> /path/to/analysis.log 2>&1

# Daily backup only (other days at 1:20 AM)
20 1 * * 2-7 cd /path/to/atlas && /usr/bin/make backup-prod >> /path/to/backup.log 2>&1
```

### Monitoring and Alerting

Set up monitoring for the backup and analysis pipeline:

```bash
# Check backup completion
ls -la backend/telemetry/backup/phoenix/$(date +%Y/%m/%d)/

# Check analysis outputs
ls -la analysis/output/hansard_analysis_$(date +%Y%m%d)*

# Monitor log files for errors
tail -f /path/to/backup.log
tail -f /path/to/analysis.log
```

## Data Formats and Storage

### File Format Optimization

**Parquet Files (Recommended for Analysis):**
- Efficient binary format optimized for analytics
- Preserves data types and schema information  
- Smaller file sizes (~30-50% smaller than CSV)
- Direct compatibility with pandas, Apache Spark
- Column-oriented storage for fast querying

**CSV Files (Human-Readable):**
- Text format compatible with spreadsheet software
- Easy manual inspection and debugging
- Larger file sizes but universally compatible
- Good for data sharing and manual review

### Storage Requirements

**Typical backup sizes:**
- **Hansard-Prod**: ~2-5MB per day (1000+ records)
- **Analysis outputs**: ~20-50MB per run (including visualizations)

**Retention recommendations:**
- **Daily backups**: Keep 30 days for immediate analysis
- **Weekly snapshots**: Keep 1 year for trend analysis  
- **Monthly archives**: Keep indefinitely for historical research

## Integration with ATLAS Architecture

### Data Flow Pipeline

```
Phoenix Telemetry → Backup System → Analysis Engine → Visualizations → Reports
     ↓                   ↓              ↓              ↓            ↓
User Interactions   Parquet Files   Pandas Processing  PNG Charts   MD/JSON
```

### Quality Assurance Integration

The backup and analysis system supports ATLAS quality monitoring:
- **Performance Baselines**: Historical response time tracking
- **User Satisfaction**: Feedback score trends over time
- **Content Quality**: Corpus fidelity and factual accuracy monitoring  
- **System Health**: Error rate and availability metrics

### Research and Compliance

- **Reproducible Research**: Timestamped backups enable result verification
- **Audit Trail**: Complete user interaction history
- **Privacy Compliance**: Automated handling of sensitive data classification
- **Export Capabilities**: Analysis results suitable for academic publication

## Troubleshooting

### Common Issues

**Backup fails with authentication error:**
- Check `PHOENIX_CLIENT_HEADERS` in your `.env.production` file
- Verify API key is current and has required permissions
- Test Phoenix connectivity: `curl -H "api_key=your_key" https://app.phoenix.arize.com/s/aiinfra/v1/traces`
- Ensure the API key has access to the `aiinfra` space (check Phoenix Cloud > Settings > API Keys)

**Backup fails to connect to Phoenix space:**
- Verify `PHOENIX_SPACE_ID=aiinfra` is set in your environment file
- Confirm `PHOENIX_COLLECTOR_ENDPOINT` uses the space-based URL format: `https://app.phoenix.arize.com/s/aiinfra`
- If using a custom space, ensure the space exists and your API key has access
- The backup script constructs the base URL from `PHOENIX_SPACE_ID` -- if missing, it will fail with a clear error

**No data in backup files:**
- Verify project names in `PHOENIX_PROJECT_BACKUPS` match Phoenix exactly
- Check that projects have recent spans in the Phoenix UI at `https://app.phoenix.arize.com/s/aiinfra/projects`
- Review backup logs for filtering or date range issues

**Analysis fails on backup data:**
- Ensure backup completed successfully (check file sizes > 0)
- Verify required columns exist in backup data
- Run analysis with verbose logging: `python analysis/analyze_hansard_spans.py`

**Visualization generation errors:**
- Install required libraries: `pip install matplotlib seaborn`
- Check available disk space for figure generation
- Verify output directory permissions

### Performance Optimization

**Large backup datasets:**
```bash
# Use date filtering for large projects
PHOENIX_START_DATE="2025-10-01" make backup-prod

# Split analysis by date ranges for memory efficiency
python analysis/analyze_hansard_spans.py --date-range "2025-10-01,2025-10-31"
```

**Storage optimization:**
```bash
# Compress old backups
gzip backend/telemetry/backup/phoenix/*/**.csv

# Archive analysis outputs older than 30 days
find analysis/output/ -name "*.png" -mtime +30 -exec tar -czf archived_analysis.tar.gz {} +
```

For additional support, see:
- [Analysis Documentation](analysis.md) - Detailed analysis capabilities
- [Configuration Guide](configuration.md) - Environment setup
- [Production Deployment](production.md) - Production environment considerations
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
2. **Authenticates**: Creates Phoenix client with API key
3. **Discovers Projects**: Uses projects listed in `PHOENIX_PROJECT_BACKUPS`
4. **Exports Spans**: Downloads complete spans dataframes for each project using Phoenix SDK
5. **Fetches Annotations**: Retrieves all user feedback annotations (ratings, explanations, notes)
6. **Merges Data**: Combines annotations into spans using span IDs (creates multiple rows per span if multiple annotations exist)
7. **Saves Files**: Writes both Parquet and CSV formats to dated directories

The script handles errors gracefully, continuing with other projects if one fails, and provides detailed logging for troubleshooting.

**Note**: The merge creates denormalized data where spans with multiple annotations appear as multiple rows. This makes it easy to filter by annotation type (e.g., show only "Relevance Rating" feedback) but means span counts may be higher than the original trace count.