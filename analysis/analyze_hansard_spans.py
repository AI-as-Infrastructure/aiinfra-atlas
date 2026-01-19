#!/usr/bin/env python3
"""
Hansard Parliamentary Data Spans Analysis

This script analyzes Phoenix telemetry spans from the Hansard parliamentary corpus
to examine user interactions, feedback patterns, and system performance metrics.
The analysis focuses on question-answer quality, user feedback, and retrieval effectiveness.
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from datetime import datetime
import os
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path=Path(__file__).parent.parent / "config" / ".env.development")

# Configuration from environment variables
ANALYSIS_BASE_DIR = os.getenv("ANALYSIS_BASE_DIR", str(Path(__file__).parent.parent / "data_backup" / "phoenix"))
ANALYSIS_OUTPUT_DIR = os.getenv("ANALYSIS_OUTPUT_DIR", str(Path(__file__).parent / "output"))
ANALYSIS_TITLE_PREFIX = os.getenv("ANALYSIS_TITLE_PREFIX", "Parliamentary Data")

def find_latest_spans_path(project_name: str,
                           base_dir: Path = None) -> Path | None:
    """Return the newest spans file path (parquet preferred, csv fallback) for a project."""
    if base_dir is None:
        base_dir = Path(ANALYSIS_BASE_DIR)
    if not base_dir.exists():
        return None
    parquet_candidates = list(base_dir.rglob(f"{project_name}/spans.parquet"))
    csv_candidates = list(base_dir.rglob(f"{project_name}/spans.csv"))
    candidates = parquet_candidates + csv_candidates
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest

def load_spans_dataframe(spans_path: Path) -> pd.DataFrame:
    """Load spans from parquet or csv based on file suffix."""
    if spans_path.suffix == ".parquet":
        return pd.read_parquet(spans_path)
    if spans_path.suffix == ".csv":
        return pd.read_csv(spans_path)
    raise ValueError(f"Unsupported spans file type: {spans_path}")

def create_visualizations(df, feedback_data, output_dir):
    """Create comprehensive visualizations for the Hansard analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("viridis")
    
    # Create a figures directory
    figures_dir = os.path.join(output_dir, f"figures_{timestamp}")
    os.makedirs(figures_dir, exist_ok=True)
    
    # 1. Feedback Scores Distribution
    if feedback_data:
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'{ANALYSIS_TITLE_PREFIX}: User Feedback Analysis', fontsize=16, fontweight='bold')
        
        feedback_metrics = ['Analysis Quality', 'Clarity', 'Corpus Fidelity', 
                           'Factual Accuracy', 'Relevance Rating', 'Query Difficulty']
        
        for i, metric in enumerate(feedback_metrics):
            row, col = i // 3, i % 3
            ax = axes[row, col]
            
            if metric in feedback_data:
                scores = list(feedback_data[metric]['score_distribution'].keys())
                counts = list(feedback_data[metric]['score_distribution'].values())
                
                bars = ax.bar(scores, counts, alpha=0.7, color=sns.color_palette("viridis", len(scores)))
                ax.set_title(f'{metric}\n(Avg: {feedback_data[metric]["average_score"]:.1f})', fontweight='bold')
                ax.set_xlabel('Score (1-5)')
                ax.set_ylabel('Count')
                ax.set_ylim(0, max(counts) * 1.2 if counts else 1)
                
                # Add value labels on bars
                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                           f'{int(count)}', ha='center', va='bottom')
            else:
                ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', 
                       transform=ax.transAxes, fontsize=12, alpha=0.5)
                ax.set_title(metric, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(figures_dir, 'feedback_scores_distribution.png'), 
                    dpi=300, bbox_inches='tight')
        plt.close()
    
    # 2. Response Time Analysis
    response_time_col = None
    for col in ['attributes.telemetry.span.duration', 'attributes.generation_time_seconds', 'attributes.processing_time_seconds']:
        if col in df.columns:
            response_time_col = col
            break
    
    if response_time_col:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        fig.suptitle(f'{ANALYSIS_TITLE_PREFIX} System Performance Analysis', fontsize=16, fontweight='bold')
        
        response_times = df[response_time_col].dropna()
        
        # Histogram
        ax1.hist(response_times, bins=20, alpha=0.7, edgecolor='black', color='skyblue')
        ax1.set_title('Response Time Distribution', fontweight='bold')
        ax1.set_xlabel('Response Time (seconds)')
        ax1.set_ylabel('Frequency')
        ax1.axvline(response_times.mean(), color='red', linestyle='--', 
                   label=f'Mean: {response_times.mean():.2f}s')
        ax1.legend()
        
        # Box plot
        ax2.boxplot(response_times, vert=True, patch_artist=True, 
                   boxprops=dict(facecolor='lightblue', alpha=0.7))
        ax2.set_title('Response Time Box Plot', fontweight='bold')
        ax2.set_ylabel('Response Time (seconds)')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(os.path.join(figures_dir, 'response_time_analysis.png'), 
                    dpi=300, bbox_inches='tight')
        plt.close()
    
    # 3. Question-Answer Patterns
    input_col = None
    output_col = None
    for col in df.columns:
        if 'input' in col.lower() and 'value' in col.lower():
            input_col = col
        if 'output' in col.lower() and 'value' in col.lower():
            output_col = col
    
    if input_col and output_col:
        questions = df[input_col].dropna()
        responses = df[output_col].dropna()
        
        question_lengths = questions.str.len()
        response_lengths = responses.str.len()
        
        fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
        fig.suptitle(f'{ANALYSIS_TITLE_PREFIX} Question-Answer Pattern Analysis', fontsize=16, fontweight='bold')
        
        # Question length distribution
        ax1.hist(question_lengths, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
        ax1.set_title('Question Length Distribution', fontweight='bold')
        ax1.set_xlabel('Question Length (characters)')
        ax1.set_ylabel('Frequency')
        ax1.axvline(question_lengths.mean(), color='red', linestyle='--', 
                   label=f'Mean: {question_lengths.mean():.0f}')
        ax1.legend()
        
        # Response length distribution
        ax2.hist(response_lengths, bins=20, alpha=0.7, color='coral', edgecolor='black')
        ax2.set_title('Response Length Distribution', fontweight='bold')
        ax2.set_xlabel('Response Length (characters)')
        ax2.set_ylabel('Frequency')
        ax2.axvline(response_lengths.mean(), color='red', linestyle='--', 
                   label=f'Mean: {response_lengths.mean():.0f}')
        ax2.legend()
        
        # Correlation scatter plot
        common_indices = question_lengths.index.intersection(response_lengths.index)
        if len(common_indices) > 0:
            q_len = question_lengths.loc[common_indices]
            r_len = response_lengths.loc[common_indices]
            ax3.scatter(q_len, r_len, alpha=0.6, color='purple')
            ax3.set_title('Question vs Response Length', fontweight='bold')
            ax3.set_xlabel('Question Length (characters)')
            ax3.set_ylabel('Response Length (characters)')
            
            # Add correlation coefficient
            corr = np.corrcoef(q_len, r_len)[0, 1] if len(q_len) > 1 else 0
            ax3.text(0.05, 0.95, f'Correlation: {corr:.3f}', 
                    transform=ax3.transAxes, bbox=dict(boxstyle="round", facecolor='white', alpha=0.8))
        else:
            ax3.text(0.5, 0.5, 'Insufficient Data for Correlation', ha='center', va='center', 
                    transform=ax3.transAxes, fontsize=12, alpha=0.5)
            ax3.set_title('Question vs Response Length', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(os.path.join(figures_dir, 'qa_patterns.png'), 
                    dpi=300, bbox_inches='tight')
        plt.close()
    
    # 4. Comprehensive Hansard Dashboard
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)
    fig.suptitle(f'{ANALYSIS_TITLE_PREFIX}: Comprehensive Analysis Dashboard',
                 fontsize=18, fontweight='bold')
    
    # Overall feedback summary (top left)
    ax1 = fig.add_subplot(gs[0, :2])
    if feedback_data:
        metrics = list(feedback_data.keys())
        avg_scores = [feedback_data[m]['average_score'] for m in metrics]
        colors = sns.color_palette("RdYlGn", len(metrics))
        bars = ax1.barh(metrics, avg_scores, color=colors)
        ax1.set_title('Average Feedback Scores by Metric', fontweight='bold')
        ax1.set_xlabel('Average Score (1-5)')
        ax1.set_xlim(0, 5)
        
        # Add score labels
        for i, (bar, score) in enumerate(zip(bars, avg_scores)):
            ax1.text(score + 0.1, bar.get_y() + bar.get_height()/2, 
                    f'{score:.2f}', va='center', fontweight='bold')
    else:
        ax1.text(0.5, 0.5, 'Limited Feedback Data Available', ha='center', va='center', 
                transform=ax1.transAxes, fontsize=12, alpha=0.5)
        ax1.set_title('Average Feedback Scores by Metric', fontweight='bold')
    
    # System performance summary (top right)
    ax2 = fig.add_subplot(gs[0, 2:])
    
    # Find available response time column
    response_time_col = None
    for col in ['attributes.telemetry.span.duration', 'attributes.generation_time_seconds', 'attributes.processing_time_seconds']:
        if col in df.columns:
            response_time_col = col
            break
    
    if response_time_col:
        response_times = df[response_time_col].dropna()
        performance_metrics = ['Min', 'Mean', 'Median', 'Max']
        performance_values = [response_times.min(), response_times.mean(), 
                            response_times.median(), response_times.max()]
        
        bars = ax2.bar(performance_metrics, performance_values, 
                      color=['green', 'blue', 'orange', 'red'], alpha=0.7)
        ax2.set_title('Response Time Performance', fontweight='bold')
        ax2.set_ylabel('Time (seconds)')
        
        # Add value labels
        for bar, value in zip(bars, performance_values):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                    f'{value:.1f}s', ha='center', va='bottom', fontweight='bold')
    else:
        ax2.text(0.5, 0.5, 'No Performance Data Available', ha='center', va='center', 
                transform=ax2.transAxes, fontsize=12, alpha=0.5)
        ax2.set_title('Response Time Performance', fontweight='bold')
    
    # Data volume summary (bottom)
    ax3 = fig.add_subplot(gs[1:, :])
    
    # Create summary statistics table
    date_range = 'N/A'
    if 'created_at' in df.columns:
        try:
            valid_dates = pd.to_datetime(df['created_at'], errors='coerce').dropna()
            if len(valid_dates) > 0:
                date_range = f"{valid_dates.min()} to {valid_dates.max()}"
        except:
            date_range = 'N/A'
    
    # Calculate average response time from data if available
    avg_response_time = 'N/A'
    if response_time_col:
        response_times = df[response_time_col].dropna()
        if len(response_times) > 0:
            avg_response_time = f"{response_times.mean():.1f}s"
    
    summary_data = {
        'Total Records': len(df),
        'Unique Q&A Sessions': df['attributes.qa_id'].nunique() if 'attributes.qa_id' in df.columns else 0,
        'Feedback Annotations': len(df['annotation_name'].dropna()) if 'annotation_name' in df.columns else 0,
        'Average Response Time': avg_response_time,
        'Date Range': date_range
    }
    
    # Convert to display format
    table_data = [[k, str(v)] for k, v in summary_data.items()]
    
    ax3.axis('tight')
    ax3.axis('off')
    table = ax3.table(cellText=table_data, 
                     colLabels=['Metric', 'Value'],
                     cellLoc='left',
                     loc='center',
                     colWidths=[0.3, 0.7])
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1.2, 2)
    
    # Style the table
    for i in range(len(table_data)):
        table[(i+1, 0)].set_facecolor('#f0f0f0')
        table[(i+1, 1)].set_facecolor('#ffffff')
    
    table[(0, 0)].set_facecolor('#2E8B57')
    table[(0, 1)].set_facecolor('#2E8B57')
    table[(0, 0)].set_text_props(weight='bold', color='white')
    table[(0, 1)].set_text_props(weight='bold', color='white')
    
    ax3.set_title('Hansard Analysis Summary', fontweight='bold', pad=20)
    
    plt.savefig(os.path.join(figures_dir, 'comprehensive_dashboard.png'), 
                dpi=300, bbox_inches='tight')
    plt.close()
    
    return figures_dir

def save_analysis_results(results, output_dir, figures_dir=None):
    """Save analysis results to files in a readable format."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Debug output
    print(f"DEBUG: save_analysis_results output_dir = {output_dir}")
    print(f"DEBUG: save_analysis_results figures_dir = {figures_dir}")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save summary report
    summary_file = os.path.join(output_dir, f"hansard_analysis_summary_{timestamp}.md")
    with open(summary_file, 'w') as f:
        f.write("# Hansard Parliamentary Data Analysis Summary\n\n")
        f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        if figures_dir:
            f.write("## Visualizations\n\n")
            f.write("The following visualizations have been generated:\n\n")
            f.write("- **Feedback Scores Distribution**: Individual metric analysis with score distributions\n")
            f.write("- **Response Time Analysis**: System performance histograms and box plots\n")
            f.write("- **Question-Answer Patterns**: Length distributions and correlation analysis\n")
            f.write("- **Comprehensive Dashboard**: Combined overview of all metrics\n\n")
            f.write(f"All visualizations are saved in: `{figures_dir}`\n\n")
        
        for section, content in results.items():
            f.write(f"## {section}\n\n")
            f.write(f"{content}\n\n")
    
    # Save detailed JSON data
    json_file = os.path.join(output_dir, f"hansard_analysis_data_{timestamp}.json")
    with open(json_file, 'w') as f:
        # Convert pandas objects to serializable format
        serializable_results = {}
        for key, value in results.items():
            if isinstance(value, pd.Series):
                serializable_results[key] = value.to_dict()
            elif isinstance(value, pd.DataFrame):
                serializable_results[key] = value.to_dict(orient='records')
            else:
                serializable_results[key] = str(value)
        
        json.dump(serializable_results, f, indent=2, default=str)
    
    print(f"\n📊 Analysis results saved:")
    print(f"   Summary: {summary_file}")
    print(f"   Data: {json_file}")
    if figures_dir:
        print(f"   Visualizations: {figures_dir}")
    
    return summary_file, json_file, figures_dir

def generate_system_config_info():
    """Generate system configuration information from Phoenix telemetry data."""
    # Debug output
    print(f"DEBUG: generate_system_config_info base_dir = {ANALYSIS_BASE_DIR}")

    try:
        # Load the spans data to extract configuration from com.atlas.rag.pipeline spans
        latest_path = find_latest_spans_path("Hansard-Prod")
        print(f"DEBUG: generate_system_config_info latest_path = {latest_path}")
        if latest_path is None:
            raise FileNotFoundError("No Hansard-Prod spans backup found")
        df = load_spans_dataframe(latest_path)
        
        # Find the pipeline spans that contain configuration
        pipeline_spans = df[df['name'] == 'com.atlas.rag.pipeline']
        
        if len(pipeline_spans) > 0:
            # Get the first pipeline span and extract attributes
            first_pipeline = pipeline_spans.iloc[0]
            
            # Extract configuration from attributes
            system_config = {}
            
            # Map attribute columns to config values
            attr_mappings = {
                'attributes.atlas_version': 'ATLAS_VERSION',
                'attributes.ATLAS_VERSION': 'ATLAS_VERSION',
                'attributes.composite_target': 'composite_target',
                'attributes.target_id': 'target_id',
                'attributes.llm_provider': 'llm_provider',
                'attributes.llm_model': 'llm_model',
                'attributes.embedding_model': 'embedding_model',
                'attributes.algorithm': 'algorithm',
                'attributes.search_type': 'search_type',
                'attributes.search_k': 'search_k',
                'attributes.search_score_threshold': 'search_score_threshold',
                'attributes.chunk_size': 'chunk_size',
                'attributes.chunk_overlap': 'chunk_overlap',
                'attributes.pooling': 'pooling',
                'attributes.citation_limit': 'citation_limit',
                'attributes.LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS': 'LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS',
                'attributes.LARGE_RETRIEVAL_SIZE_ALL_CORPUS': 'LARGE_RETRIEVAL_SIZE_ALL_CORPUS',
            }
            
            # Extract available configuration values
            for attr_col, config_key in attr_mappings.items():
                if attr_col in first_pipeline.index and pd.notna(first_pipeline[attr_col]):
                    system_config[config_key] = first_pipeline[attr_col]
            
            # If we didn't get some values, try alternative column names or derive them
            if 'ATLAS_VERSION' not in system_config:
                system_config['ATLAS_VERSION'] = "1.0.0"  # Default
            
            if 'composite_target' not in system_config and 'target_id' in system_config:
                system_config['composite_target'] = f"{system_config['target_id']}_unknown"
            
            return system_config
        else:
            print("Warning: No com.atlas.rag.pipeline spans found for configuration extraction")
            return {
                "ATLAS_VERSION": "Unknown - No pipeline spans",
                "composite_target": "Unknown - No pipeline spans",
                "note": "Configuration could not be extracted from Phoenix telemetry data"
            }
        
    except Exception as e:
        print(f"Warning: Could not extract configuration from telemetry data: {e}")
        return {
            "ATLAS_VERSION": "Unknown",
            "composite_target": "Unknown",
            "note": f"Configuration extraction failed: {str(e)}"
        }

def save_readme_output(results, output_dir, figures_dir):
    """Save README format output with system configuration only."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Get system configuration
    system_config = generate_system_config_info()
    
    readme_content = f"""# Hansard Analysis System Configuration

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}  
**Analysis ID**: hansard_analysis_{timestamp}

## System Configuration

```yaml
ATLAS Version: {system_config.get('ATLAS_VERSION', 'Unknown')}
Composite Target: {system_config.get('composite_target', 'Unknown')}
Target ID: {system_config.get('target_id', 'Unknown')}

# LLM Configuration
LLM Provider: {system_config.get('llm_provider', 'Unknown')}
LLM Model: {system_config.get('llm_model', 'Unknown')}

# Vector Store & Embedding
Embedding Model: {system_config.get('embedding_model', 'Unknown')}
Algorithm: {system_config.get('algorithm', 'Unknown')}
Search Type: {system_config.get('search_type', 'Unknown')}
Search K: {system_config.get('search_k', 'Unknown')}
Score Threshold: {system_config.get('search_score_threshold', 'Unknown')}

# Text Processing
Chunk Size: {system_config.get('chunk_size', 'Unknown')}
Chunk Overlap: {system_config.get('chunk_overlap', 'Unknown')}
Pooling Strategy: {system_config.get('pooling', 'Unknown')}

# Retrieval Configuration
Citation Limit: {system_config.get('citation_limit', 'Unknown')}
Single Corpus Retrieval Size: {system_config.get('LARGE_RETRIEVAL_SIZE_SINGLE_CORPUS', 'Unknown')}
All Corpus Retrieval Size: {system_config.get('LARGE_RETRIEVAL_SIZE_ALL_CORPUS', 'Unknown')}
```

---

*System configuration captured from the ATLAS instance that generated the analyzed data.*
"""

    # Save README file
    readme_file = os.path.join(output_dir, f"hansard_analysis_readme_{timestamp}.md")
    with open(readme_file, 'w') as f:
        f.write(readme_content)
    
    print(f"README saved to: {readme_file}")
    return readme_file

def analyze_hansard_spans():
    """
    Analyze Hansard parliamentary spans data for user feedback and interaction patterns.
    """
    
    # Define file paths
    latest_path = find_latest_spans_path("Hansard-Prod")
    output_dir = ANALYSIS_OUTPUT_DIR

    # Debug output
    print(f"DEBUG: base_dir = {ANALYSIS_BASE_DIR}")
    print(f"DEBUG: output_dir = {output_dir}")
    print(f"DEBUG: latest_path = {latest_path}")
    
    print("="*80)
    print("HANSARD PARLIAMENTARY DATA SPANS ANALYSIS")
    print("="*80)
    print("Analyzing Phoenix telemetry data from Hansard parliamentary corpus backups")
    
    # Load Hansard spans
    try:
        if latest_path is None:
            raise FileNotFoundError("No Hansard-Prod spans backup found")
        hansard_spans = load_spans_dataframe(latest_path)
        print(f"\n✓ Hansard-Prod spans loaded: {len(hansard_spans)} records")
        
        if 'start_time' in hansard_spans.columns:
            date_range = f"{hansard_spans['start_time'].min()} to {hansard_spans['start_time'].max()}"
            print(f"Date range: {date_range}")
        
        results = {}
        results['Dataset Info'] = f"Records: {len(hansard_spans)}\nDate Range: {date_range if 'date_range' in locals() else 'Unknown'}"
        
    except Exception as e:
        print(f"✗ Error loading Hansard spans: {e}")
        return
    
    print("\n" + "="*80)
    print("USER FEEDBACK AND INTERACTION ANALYSIS")
    print("="*80)
    
    # Analyze user feedback patterns
    feedback_analysis = analyze_user_feedback(hansard_spans)
    results.update(feedback_analysis)
    
    # Analyze Q&A patterns
    qa_analysis = analyze_qa_patterns(hansard_spans)
    results.update(qa_analysis)
    
    # Analyze system performance
    performance_analysis = analyze_system_performance(hansard_spans)
    results.update(performance_analysis)
    
    # Generate visualizations
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)
    figures_dir = create_visualizations(hansard_spans, feedback_analysis.get('quality_metrics', {}), output_dir)
    
    # Save results
    save_analysis_results(results, output_dir, figures_dir)
    
    # Generate README output
    save_readme_output(results, output_dir, figures_dir)
    
    return results

def analyze_user_feedback(df):
    """Analyze user feedback patterns and ratings."""
    print("\n--- User Feedback Analysis ---")
    
    results = {}
    
    # Analyze annotation-based feedback
    if 'annotation_name' in df.columns:
        annotations = df['annotation_name'].value_counts().dropna()
        print(f"Annotation types found: {len(annotations)}")
        
        if len(annotations) > 0:
            results['feedback_types'] = annotations.to_dict()
            print("Feedback annotation types:")
            for annotation, count in annotations.items():
                print(f"  - {annotation}: {count} instances")
        
        # Analyze feedback quality metrics
        quality_metrics = ['Analysis Quality', 'Clarity', 'Corpus Fidelity', 
                          'Factual Accuracy', 'Relevance Rating', 'Query Difficulty']
        
        quality_results = {}
        for metric in quality_metrics:
            metric_data = df[df['annotation_name'] == metric]
            if len(metric_data) > 0:
                scores = metric_data['result.score'].dropna()
                if len(scores) > 0:
                    quality_results[metric] = {
                        'count': len(scores),
                        'average_score': scores.mean(),
                        'score_distribution': scores.value_counts().to_dict()
                    }
                    print(f"\n{metric}:")
                    print(f"  Average score: {scores.mean():.2f}")
                    print(f"  Score distribution: {scores.value_counts().to_dict()}")
        
        results['quality_metrics'] = quality_results
    
    # Analyze user expertise levels
    if 'User Expertise' in df['annotation_name'].values or 'User Type' in df['annotation_name'].values:
        expertise_col = 'User Expertise' if 'User Expertise' in df['annotation_name'].values else 'User Type'
        expertise_data = df[df['annotation_name'] == expertise_col]
        if len(expertise_data) > 0:
            expertise_levels = expertise_data['result.explanation'].value_counts()
            results['user_expertise'] = expertise_levels.to_dict()
            print(f"\nUser expertise levels:")
            for level, count in expertise_levels.items():
                print(f"  - {level}: {count} users")
    
    return results

def analyze_qa_patterns(df):
    """Analyze question-answer interaction patterns."""
    print("\n--- Question-Answer Pattern Analysis ---")
    
    results = {}
    
    # Analyze unique Q&A sessions
    if 'attributes.qa_id' in df.columns:
        qa_ids = df['attributes.qa_id'].dropna().unique()
        results['total_qa_sessions'] = len(qa_ids)
        print(f"Unique Q&A sessions: {len(qa_ids)}")
        
        # Analyze questions and responses
        if 'attributes.input.value' in df.columns:
            questions = df['attributes.input.value'].dropna()
            if len(questions) > 0:
                avg_question_length = questions.str.len().mean()
                results['average_question_length'] = avg_question_length
                print(f"Average question length: {avg_question_length:.0f} characters")
        
        if 'attributes.output.value' in df.columns:
            responses = df['attributes.output.value'].dropna()
            if len(responses) > 0:
                avg_response_length = responses.str.len().mean()
                results['average_response_length'] = avg_response_length
                print(f"Average response length: {avg_response_length:.0f} characters")
    
    return results

def analyze_system_performance(df):
    """Analyze system performance metrics."""
    print("\n--- System Performance Analysis ---")
    
    results = {}
    
    # Analyze response times
    if 'attributes.generation_time_seconds' in df.columns:
        response_times = df['attributes.generation_time_seconds'].dropna()
        if len(response_times) > 0:
            results['response_time_stats'] = {
                'average': response_times.mean(),
                'median': response_times.median(),
                'min': response_times.min(),
                'max': response_times.max()
            }
            print(f"Response time statistics:")
            print(f"  Average: {response_times.mean():.2f} seconds")
            print(f"  Median: {response_times.median():.2f} seconds")
            print(f"  Range: {response_times.min():.2f} - {response_times.max():.2f} seconds")
    
    # Analyze retrieval metrics
    retrieval_metrics = {}
    if 'attributes.document_count' in df.columns:
        doc_counts = df['attributes.document_count'].dropna()
        if len(doc_counts) > 0:
            retrieval_metrics['average_documents_retrieved'] = doc_counts.mean()
            print(f"Average documents retrieved: {doc_counts.mean():.1f}")
    
    if 'attributes.citation_count' in df.columns:
        citation_counts = df['attributes.citation_count'].dropna()
        if len(citation_counts) > 0:
            retrieval_metrics['average_citations'] = citation_counts.mean()
            print(f"Average citations per response: {citation_counts.mean():.1f}")
    
    if retrieval_metrics:
        results['retrieval_metrics'] = retrieval_metrics
    
    # Analyze error patterns
    if 'status_code' in df.columns:
        status_codes = df['status_code'].value_counts()
        error_rate = (status_codes.get('ERROR', 0) / len(df)) * 100
        results['error_rate_percentage'] = error_rate
        print(f"Error rate: {error_rate:.2f}%")
    
    return results

if __name__ == "__main__":
    analyze_hansard_spans()