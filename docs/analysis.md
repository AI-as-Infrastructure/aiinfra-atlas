# Phoenix Backup Data Analysis

This document describes the analysis framework for Phoenix telemetry backup data, focused on the Hansard parliamentary correspondence corpus.

## Overview

The analysis framework processes Phoenix spans.parquet backup files to extract and analyze user feedback, question-answer patterns, and system performance metrics. This provides insights into user interactions, system performance, and data quality for the ATLAS system.

## Analysis Workflow

### 1. Data Backup and Collection

```bash
# Collect fresh Phoenix telemetry data
make backup-prod
```

This downloads the latest spans and annotations from the production environment.

### 2. Analysis Execution

```bash
# Analyze parliamentary data with visualizations
make hansard-analysis
```

### 3. Results and Visualizations

The analysis generates comprehensive outputs including:
- **Markdown summaries**: Human-readable analysis reports
- **JSON data**: Machine-readable metrics for further processing
- **Visualization suite**: Professional charts and dashboards

## Data Sources and Coverage

### Hansard Parliamentary Data
```
backend/telemetry/backup/phoenix/2025/10/31/Hansard-Prod/spans.parquet
```
- **Focus**: Parliamentary correspondence analysis
- **Typical volume**: ~1000+ records per backup
- **Analysis script**: `analysis/analyze_hansard_spans.py`

## Analysis Capabilities

### User Feedback Analysis
- **Analysis Quality** ratings (1-5 scale)
- **Clarity** of responses
- **Corpus Fidelity** (how well responses match the corpus)
- **Factual Accuracy** assessments
- **Bias detection** (Fault ratings)
- **Query Difficulty** evaluations
- **Relevance** ratings
- **User comments** and expertise levels

### Question-Answer Pattern Analysis
- Question types and complexity distribution
- Response length and structure patterns
- Correlation analysis between question and response characteristics
- Performance correlation with question characteristics

### System Performance Metrics
- Response times and latency analysis
- Success rates across different query types
- User satisfaction patterns
- Error rate monitoring

### Visualization Suite

Each analysis generates professional visualizations:

1. **Feedback Scores Distribution**: Bar charts showing score distributions for each feedback metric
2. **Response Time Analysis**: Histograms and box plots of system performance
3. **Question-Answer Patterns**: Length distributions and correlation analysis
4. **Comprehensive Dashboard**: Combined overview with key metrics and summary tables

## Usage

### Quick Start
```bash
# Complete analysis workflow
make backup-prod           # Collect fresh data
make hansard-analysis       # Analyze parliamentary data
```

### Individual Commands
```bash
# Hansard parliamentary analysis
cd /home/jamessmithies/projects/aiinfra-atlas
python analysis/analyze_hansard_spans.py
```

## Output Structure

Results are saved to the `analysis/output/` directory with timestamp-based naming:

### Hansard Analysis Output
```
analysis/output/
├── hansard_analysis_summary_YYYYMMDD_HHMMSS.md     # Human-readable report
├── hansard_analysis_data_YYYYMMDD_HHMMSS.json      # Machine-readable data
└── figures_YYYYMMDD_HHMMSS/                        # Visualization directory
    ├── feedback_scores_distribution.png
    ├── response_time_analysis.png
    ├── qa_patterns.png
    └── comprehensive_dashboard.png
```

### Report Contents

**Markdown Summary Reports:**
- Executive summary with key metrics
- Visualization directory references
- Detailed statistical breakdowns
- Trend analysis and insights
- Performance benchmarks

**JSON Data Files:**
- Raw statistics for further processing
- Structured data for visualization tools
- Machine-readable metrics for monitoring systems
- Historical data for trend analysis

**Visualization Files:**
- High-resolution PNG files (300 DPI)
- Professional styling appropriate for reports
- Color-coded metrics for easy interpretation
- Interactive dashboard-style layouts

## Sample Analysis Results

### Typical Hansard Analysis Metrics
- **Volume**: ~1000+ interaction records
- **Q&A Sessions**: ~140 unique sessions
- **Performance**: Variable response times based on query complexity
- **User Feedback**: Limited but high-quality ratings when available
- **Question Patterns**: Diverse question lengths and response correlations

## Feedback Dimensions Reference

| Dimension | Description | Scale | Notes |
|-----------|-------------|-------|-------|
| Analysis Quality | Overall quality of AI analysis | 1-5 | Core metric for content quality |
| Clarity | How clear and understandable the response | 1-5 | User experience indicator |
| Corpus Fidelity | Response alignment with source corpus | 1-5 | Accuracy to historical sources |
| Factual Accuracy | Accuracy of factual claims | 1-5 | Verification against known facts |
| Fault: Bias | Detection of bias (lower is better) | 1-5 | Bias monitoring and detection |
| Query Difficulty | User-assessed question complexity | 1-5 | Context for interpretation |
| Relevance Rating | Response relevance to the query | 1-5 | Search effectiveness measure |

## Data Privacy and Security

The analysis framework is designed for the Hansard parliamentary corpus. Analysis results are suitable for public documentation and contain no sensitive information.

## Monitoring and Automation

### Recommended Schedule
```bash
# Weekly comprehensive analysis
make backup-prod && make hansard-analysis

# Daily monitoring (automated)
make backup-prod  # Can be scheduled via cron
```

### Integration Points
- **Continuous Monitoring**: JSON outputs suitable for monitoring dashboards
- **Historical Tracking**: Timestamped results enable trend analysis
- **Performance Baselines**: Regular analysis establishes performance benchmarks
- **Quality Assurance**: Feedback analysis identifies areas for improvement

## Prerequisites and Dependencies

- **Python Environment**: Virtual environment with pandas, matplotlib, seaborn
- **Data Access**: Phoenix backup data in `backend/telemetry/backup/phoenix/` directory
- **Disk Space**: ~50MB per analysis run (including visualizations)
- **Processing Time**: ~30 seconds for typical analysis run

## Troubleshooting

### Common Issues

**No backup data available:**
```bash
make backup-prod  # Refresh data from Phoenix
```

**Missing visualization libraries:**
```bash
source .venv/bin/activate
pip install matplotlib seaborn
```

**Empty analysis results:**
- Check backup data exists in `backend/telemetry/backup/phoenix/YYYY/MM/DD/`
- Verify Phoenix telemetry is capturing data
- Review backup configuration in `config/.env.production`

For technical implementation details, see the source code in:
- `analysis/analyze_hansard_spans.py`