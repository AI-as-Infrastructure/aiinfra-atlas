#!/usr/bin/env python3
"""
Phoenix Arize Data Export Script

This script exports telemetry data from Phoenix Arize for analysis and visualization.
Supports configuration by project name and date range filtering.
"""

# Configuration - Update these settings as needed
PHOENIX_PROJECT_NAME = "Hansard-Prod"  # Override with --project flag or set environment variable
DEFAULT_DAYS_BACK = 7                   # Default number of days to export if no date range specified

# Date range configuration - Set these for default date filtering
DEFAULT_START_DATE = None               # Format: "2024-01-01" or None for dynamic range
DEFAULT_END_DATE = None                 # Format: "2024-01-31" or None for today

# Output format configuration
OUTPUT_FORMAT = "csv"                   # Options: "csv", "json", "parquet"
INCLUDE_TIMESTAMP_IN_FILENAME = True    # Add timestamp to output filenames

import os
import json
import csv
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import argparse
from phoenix import Client
from dotenv import load_dotenv


class PhoenixExporter:
    def __init__(self, project_name: Optional[str] = None):
        """Initialize Phoenix client with environment configuration"""
        load_dotenv('config/.env.development')
        
        self.project_name = project_name or PHOENIX_PROJECT_NAME
        self.client = Client()
        self.output_dir = Path(f"reports/output/{self.project_name}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def _save_dataframe(self, df: pd.DataFrame, data_type: str) -> str:
        """Save DataFrame in configured format"""
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S") if INCLUDE_TIMESTAMP_IN_FILENAME else ""
        
        if OUTPUT_FORMAT == "csv":
            filename = f"{data_type}_{timestamp_str}.csv" if timestamp_str else f"{data_type}.csv"
            filepath = self.output_dir / filename
            df.to_csv(filepath, index=False)
        elif OUTPUT_FORMAT == "json":
            filename = f"{data_type}_{timestamp_str}.json" if timestamp_str else f"{data_type}.json"
            filepath = self.output_dir / filename
            df.to_json(filepath, orient="records", indent=2)
        elif OUTPUT_FORMAT == "parquet":
            filename = f"{data_type}_{timestamp_str}.parquet" if timestamp_str else f"{data_type}.parquet"
            filepath = self.output_dir / filename
            df.to_parquet(filepath, index=False)
        else:
            raise ValueError(f"Unsupported output format: {OUTPUT_FORMAT}")
        
        return str(filepath)
    
    def export_traces(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Export traces with optional date filtering"""
        print(f"Exporting traces for project: {self.project_name}")
        
        # Get traces for the project
        traces = self.client.get_traces(project_name=self.project_name)
        
        # Convert to DataFrame for easier manipulation
        traces_df = pd.DataFrame([trace.dict() for trace in traces])
        
        # Apply date filtering if specified
        if start_date or end_date:
            traces_df['timestamp'] = pd.to_datetime(traces_df['timestamp'])
            if start_date:
                traces_df = traces_df[traces_df['timestamp'] >= start_date]
            if end_date:
                traces_df = traces_df[traces_df['timestamp'] <= end_date]
        
        # Save to configured format
        filepath = self._save_dataframe(traces_df, "traces")
        print(f"Traces exported to: {filepath}")
        
        return traces_df
    
    def export_datasets(self) -> pd.DataFrame:
        """Export datasets from Phoenix"""
        print(f"Exporting datasets for project: {self.project_name}")
        
        datasets = self.client.get_datasets()
        datasets_df = pd.DataFrame([dataset.dict() for dataset in datasets])
        
        # Save to configured format
        filepath = self._save_dataframe(datasets_df, "datasets")
        print(f"Datasets exported to: {filepath}")
        
        return datasets_df
    
    def export_sessions(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Export session data with telemetry metadata"""
        print(f"Exporting sessions for project: {self.project_name}")
        
        # Get traces and filter for session-related data
        traces = self.client.get_traces(project_name=self.project_name)
        
        # Extract session information from traces
        sessions_data = []
        for trace in traces:
            trace_dict = trace.dict()
            if 'session_id' in trace_dict.get('attributes', {}):
                sessions_data.append({
                    'session_id': trace_dict['attributes']['session_id'],
                    'timestamp': trace_dict['timestamp'],
                    'trace_id': trace_dict['trace_id'],
                    'span_kind': trace_dict.get('span_kind'),
                    'status': trace_dict.get('status'),
                    'attributes': json.dumps(trace_dict.get('attributes', {}))
                })
        
        sessions_df = pd.DataFrame(sessions_data)
        
        # Apply date filtering if specified
        if start_date or end_date and not sessions_df.empty:
            sessions_df['timestamp'] = pd.to_datetime(sessions_df['timestamp'])
            if start_date:
                sessions_df = sessions_df[sessions_df['timestamp'] >= start_date]
            if end_date:
                sessions_df = sessions_df[sessions_df['timestamp'] <= end_date]
        
        # Save to configured format
        filepath = self._save_dataframe(sessions_df, "sessions")
        print(f"Sessions exported to: {filepath}")
        
        return sessions_df
    
    def export_user_feedback(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Export user feedback data"""
        print(f"Exporting user feedback for project: {self.project_name}")
        
        # Get traces and filter for feedback-related data
        traces = self.client.get_traces(project_name=self.project_name)
        
        # Extract feedback information from traces
        feedback_data = []
        for trace in traces:
            trace_dict = trace.dict()
            attributes = trace_dict.get('attributes', {})
            
            # Look for feedback-related attributes
            if any(key.startswith('feedback') for key in attributes.keys()):
                feedback_data.append({
                    'trace_id': trace_dict['trace_id'],
                    'timestamp': trace_dict['timestamp'],
                    'session_id': attributes.get('session_id'),
                    'feedback_type': attributes.get('feedback.type'),
                    'feedback_value': attributes.get('feedback.value'),
                    'feedback_comment': attributes.get('feedback.comment'),
                    'all_attributes': json.dumps(attributes)
                })
        
        feedback_df = pd.DataFrame(feedback_data)
        
        # Apply date filtering if specified
        if start_date or end_date and not feedback_df.empty:
            feedback_df['timestamp'] = pd.to_datetime(feedback_df['timestamp'])
            if start_date:
                feedback_df = feedback_df[feedback_df['timestamp'] >= start_date]
            if end_date:
                feedback_df = feedback_df[feedback_df['timestamp'] <= end_date]
        
        # Save to configured format
        filepath = self._save_dataframe(feedback_df, "user_feedback")
        print(f"User feedback exported to: {filepath}")
        
        return feedback_df
    
    def export_metadata(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Export metadata and telemetry attributes"""
        print(f"Exporting metadata for project: {self.project_name}")
        
        traces = self.client.get_traces(project_name=self.project_name)
        
        # Extract all metadata/attributes
        metadata_data = []
        for trace in traces:
            trace_dict = trace.dict()
            attributes = trace_dict.get('attributes', {})
            
            metadata_data.append({
                'trace_id': trace_dict['trace_id'],
                'timestamp': trace_dict['timestamp'],
                'span_name': trace_dict.get('span_name'),
                'service_name': attributes.get('service.name'),
                'project_name': attributes.get('project.name'),
                'user_id': attributes.get('user.id'),
                'session_id': attributes.get('session_id'),
                'all_attributes': json.dumps(attributes),
                'resource_attributes': json.dumps(trace_dict.get('resource_attributes', {}))
            })
        
        metadata_df = pd.DataFrame(metadata_data)
        
        # Apply date filtering if specified
        if start_date or end_date and not metadata_df.empty:
            metadata_df['timestamp'] = pd.to_datetime(metadata_df['timestamp'])
            if start_date:
                metadata_df = metadata_df[metadata_df['timestamp'] >= start_date]
            if end_date:
                metadata_df = metadata_df[metadata_df['timestamp'] <= end_date]
        
        # Save to configured format
        filepath = self._save_dataframe(metadata_df, "metadata")
        print(f"Metadata exported to: {filepath}")
        
        return metadata_df
    
    def export_unified_session_report(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Export unified session report using Phoenix client DataFrame methods"""
        print(f"Exporting unified session report for project: {self.project_name}")
        
        try:
            # Use Phoenix client's get_spans_dataframe method for efficient data fetching
            print("Fetching spans DataFrame from Phoenix...")
            spans_df = self.client.get_spans_dataframe(
                project_name=self.project_name,
                start_time=start_date,
                end_time=end_date
            )
            
            if spans_df.empty:
                print("No spans found for the specified criteria")
                return pd.DataFrame()
            
            print(f"Found {len(spans_df)} spans")
            
            # Filter for spans with session_id
            if 'session.id' in spans_df.columns:
                spans_df = spans_df[spans_df['session.id'].notna()]
                print(f"Filtered to {len(spans_df)} spans with session_id")
            
            # Try to fetch annotations using available client methods
            try:
                print("Fetching span annotations...")
                # Check if the client has annotation methods
                if hasattr(self.client, 'get_span_annotations'):
                    annotations = self.client.get_span_annotations(project_name=self.project_name)
                    if annotations:
                        print(f"Found {len(annotations)} annotations")
                        # Convert annotations to DataFrame manually
                        annotations_data = []
                        for annotation in annotations:
                            annotation_dict = annotation.dict() if hasattr(annotation, 'dict') else annotation
                            annotations_data.append(annotation_dict)
                        
                        annotations_df = pd.DataFrame(annotations_data)
                        # Merge with spans
                        unified_df = spans_df.merge(annotations_df, left_on='context.span_id', right_on='span_id', how='left', suffixes=('', '_annotation'))
                    else:
                        print("No annotations found")
                        unified_df = spans_df
                else:
                    print("Client does not support annotation fetching")
                    unified_df = spans_df
            except Exception as e:
                print(f"Could not fetch annotations: {e}")
                unified_df = spans_df
            
            # Standardize column names to match ATLAS telemetry structure
            unified_df = self._standardize_column_names(unified_df)
            
            # Sort by session_id and timestamp for better readability
            if not unified_df.empty:
                sort_columns = []
                if 'session_id' in unified_df.columns:
                    sort_columns.append('session_id')
                if 'start_time' in unified_df.columns:
                    sort_columns.append('start_time')
                elif 'timestamp' in unified_df.columns:
                    sort_columns.append('timestamp')
                
                if sort_columns:
                    unified_df = unified_df.sort_values(sort_columns)
            
            # Save unified report
            filepath = self._save_dataframe(unified_df, "unified_session_report")
            print(f"Unified session report exported to: {filepath}")
            print(f"Report contains {len(unified_df)} rows and {len(unified_df.columns)} columns")
            
            return unified_df
            
        except Exception as e:
            print(f"Error exporting unified session report: {e}")
            return pd.DataFrame()
    
    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Phoenix DataFrame column names to match ATLAS telemetry structure"""
        # Create a mapping of Phoenix column names to ATLAS standard names
        column_mapping = {
            # Core identifiers
            'context.span_id': 'span_id',
            'context.trace_id': 'trace_id',
            'session.id': 'session_id',
            'start_time': 'span_start_time',
            'end_time': 'span_end_time',
            'span_kind': 'span_kind',
            'name': 'span_name',
            'status_code': 'span_status',
            
            # Input/Output
            'input.value': 'input_value',
            'output.value': 'output_value',
            
            # LLM attributes
            'llm.model_name': 'llm_model',
            'llm.input_messages': 'llm_input_messages',
            'llm.output_messages': 'llm_output_messages',
            'llm.token_count.prompt': 'llm_token_count_prompt',
            'llm.token_count.completion': 'llm_token_count_completion',
            'llm.token_count.total': 'llm_token_count_total',
            
            # Retrieval attributes
            'retrieval.documents': 'retrieval_documents',
            'retrieval.query': 'retrieval_query',
            
            # Annotation attributes
            'annotation_name': 'feedback_type',
            'annotation_label': 'feedback_label',
            'annotation_score': 'feedback_score',
            'annotation_explanation': 'feedback_explanation',
            'annotator_kind': 'annotator_kind',
        }
        
        # Apply column mapping
        df = df.rename(columns=column_mapping)
        
        # Extract attributes from nested JSON columns if they exist
        if 'attributes' in df.columns:
            try:
                # Parse attributes JSON and expand common ATLAS attributes
                attributes_df = pd.json_normalize(df['attributes'].apply(lambda x: json.loads(x) if isinstance(x, str) else x))
                
                # Add ATLAS-specific attributes with proper column names
                atlas_attributes = {
                    'qa_id': 'qa_id',
                    'atlas_version': 'atlas_version',
                    'composite_target': 'composite_target',
                    'atlas_target_profile': 'atlas_target_profile',
                    'llm_model': 'llm_model',
                    'llm_provider': 'llm_provider',
                    'embedding_model': 'embedding_model',
                    'retrieval.search_type': 'retrieval_search_type',
                    'retrieval.k': 'retrieval_k',
                    'retrieval.score_threshold': 'retrieval_score_threshold',
                    'retrieval.fetch_k': 'retrieval_fetch_k',
                    'chroma_collection': 'chroma_collection',
                    'algorithm': 'algorithm',
                    'chunk_size': 'chunk_size',
                    'chunk_overlap': 'chunk_overlap',
                    'system_prompt': 'system_prompt',
                    'span.sequence': 'span_sequence',
                    'span.order': 'span_order',
                }
                
                # Add available attributes to the main DataFrame
                for attr_key, col_name in atlas_attributes.items():
                    if attr_key in attributes_df.columns:
                        df[col_name] = attributes_df[attr_key]
                
            except Exception as e:
                print(f"Warning: Could not parse attributes column: {e}")
        
        return df
    
    def export_all(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> Dict[str, pd.DataFrame]:
        """Export all data types"""
        print(f"Starting full export for project: {self.project_name}")
        if start_date:
            print(f"Start date: {start_date}")
        if end_date:
            print(f"End date: {end_date}")
        
        results = {}
        results['traces'] = self.export_traces(start_date, end_date)
        results['datasets'] = self.export_datasets()
        results['sessions'] = self.export_sessions(start_date, end_date)
        results['user_feedback'] = self.export_user_feedback(start_date, end_date)
        results['metadata'] = self.export_metadata(start_date, end_date)
        results['unified_session_report'] = self.export_unified_session_report(start_date, end_date)
        
        print(f"Export completed. Files saved to: {self.output_dir}")
        return results


def main():
    parser = argparse.ArgumentParser(description="Export Phoenix Arize telemetry data")
    parser.add_argument("--project", help="Project name (defaults to PHOENIX_PROJECT_NAME env var)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, help="Number of days back from today")
    parser.add_argument("--export-type", choices=['unified'], 
                       default='unified', help="Type of data to export")
    
    args = parser.parse_args()
    
    # Parse dates - Use defaults if no arguments provided
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    elif DEFAULT_START_DATE:
        start_date = datetime.strptime(DEFAULT_START_DATE, "%Y-%m-%d")
    
    if args.end_date:
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    elif DEFAULT_END_DATE:
        end_date = datetime.strptime(DEFAULT_END_DATE, "%Y-%m-%d")
    
    if args.days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)
    elif not args.start_date and not args.end_date and not DEFAULT_START_DATE and not DEFAULT_END_DATE:
        # Use default days back if no date configuration provided
        end_date = datetime.now()
        start_date = end_date - timedelta(days=DEFAULT_DAYS_BACK)
    
    # Initialize exporter
    exporter = PhoenixExporter(args.project)
    
    # Export unified session report
    exporter.export_unified_session_report(start_date, end_date)


if __name__ == "__main__":
    main()