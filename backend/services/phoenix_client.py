"""
Phoenix API client for querying spans with feedback for inter-rater reliability.

This client handles:
1. Querying Phoenix for existing spans with feedback using the Python client
2. Extracting session data for inter-rating  
3. Providing fallback mock data for development

The client uses the Phoenix Python client (same as reports/phoenix_export.py) with graceful fallback to mock data.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import os
from phoenix import Client

logger = logging.getLogger(__name__)

class PhoenixAPIClient:
    """Client for querying Phoenix API for inter-rater functionality."""
    
    def __init__(self):
        # Use Phoenix Python client (same as your reports/phoenix_export.py)
        try:
            from phoenix import Client
            self.client = Client()
            self.has_phoenix_client = True
            logger.info("Phoenix client initialized successfully")
        except ImportError as e:
            logger.warning(f"Phoenix client not available: {e}")
            self.client = None
            self.has_phoenix_client = False
        except Exception as e:
            logger.error(f"Failed to initialize Phoenix client: {e}")
            self.client = None
            self.has_phoenix_client = False
            
        self.project_name = os.getenv("INTER_RATER_PROJECT", "atlas-hansard")
    
    async def query_spans_with_feedback(
        self, 
        exclude_user_id: str = None,
        limit: int = 10,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Query Phoenix for spans that have original feedback and are eligible for inter-rating.
        
        Args:
            exclude_user_id: User ID to exclude (don't show user their own sessions)
            limit: Maximum number of sessions to return
            days_back: How many days back to look for sessions
            
        Returns:
            List of session data suitable for inter-rating
        """
        
        # Try real Phoenix query first, fall back to mock if unavailable
        if self.has_phoenix_client:
            try:
                real_sessions = await self._query_phoenix_with_client(exclude_user_id, limit, days_back)
                if real_sessions:
                    logger.info(f"Retrieved {len(real_sessions)} sessions from Phoenix")
                    return real_sessions
            except Exception as e:
                logger.warning(f"Phoenix query failed, using mock data: {e}")
        
        # Fall back to mock data for development/testing
        logger.info("Using mock data for inter-rater sessions")
        return await self._get_mock_sessions(exclude_user_id, limit)
    
    async def _query_phoenix_with_client(
        self, 
        exclude_user_id: str = None,
        limit: int = 10,
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Real Phoenix client query for spans with feedback (based on your phoenix_export.py).
        """
        from datetime import datetime, timedelta
        import pandas as pd
        
        if not self.client:
            raise ValueError("Phoenix client not initialized")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        logger.info(f"Querying Phoenix for project '{self.project_name}' from {start_date} to {end_date}")
        
        try:
            # Use the same method as your phoenix_export.py
            spans_df = self.client.get_spans_dataframe(
                project_name=self.project_name,
                start_time=start_date,
                end_time=end_date
            )
            
            if spans_df.empty:
                logger.info("No spans found in Phoenix for the specified criteria")
                return []
            
            logger.info(f"Found {len(spans_df)} total spans in Phoenix")
            
            # Filter for spans with feedback (based on your export patterns)
            feedback_spans = []
            
            for _, row in spans_df.iterrows():
                # Extract attributes (following your phoenix_export.py pattern)
                attributes = {}
                
                # Phoenix stores attributes in different column formats
                for col in spans_df.columns:
                    if col.startswith('attributes.') or col.startswith('feedback.'):
                        key = col.replace('attributes.', '').replace('feedback.', 'feedback.')
                        attributes[key] = row[col]
                
                # Check if this span has feedback
                has_feedback = any(
                    key.startswith('feedback') or 
                    key in ['relevance', 'clarity', 'factual_accuracy', 'source_quality']
                    for key in attributes.keys()
                    if pd.notna(attributes.get(key))
                )
                
                if not has_feedback:
                    continue
                
                # Check if this span is from the excluded user
                span_user_id = attributes.get('user_id') or attributes.get('rater_id')
                if exclude_user_id and span_user_id == exclude_user_id:
                    continue
                
                # Extract session data
                session_data = {
                    "session_id": attributes.get('session_id', f"session_{row.get('span_id', 'unknown')[:8]}"),
                    "qa_id": attributes.get('qa_id', f"qa_{row.get('span_id', 'unknown')[:8]}"),
                    "span_id": row.get('span_id', row.get('context.span_id')),
                    "timestamp": row.get('start_time', datetime.now()).isoformat(),
                    "question": attributes.get('input.value', attributes.get('question', 'Question not available')),
                    "answer": attributes.get('output.value', attributes.get('answer', 'Answer not available')),
                    "original_feedback": self._extract_feedback_from_attributes(attributes),
                    "citations": self._extract_citations_from_attributes(attributes),
                    "inter_rater_count": 0,  # Will be calculated separately
                    "project_name": self.project_name,
                    "original_user_id": span_user_id
                }
                
                feedback_spans.append(session_data)
            
            # Sort by timestamp (most recent first) and limit
            feedback_spans.sort(key=lambda x: x['timestamp'], reverse=True)
            result = feedback_spans[:limit]
            
            logger.info(f"Filtered to {len(result)} spans with feedback for inter-rating")
            return result
            
        except Exception as e:
            logger.error(f"Error querying Phoenix with client: {e}")
            raise
    
    def _extract_feedback_from_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Extract feedback data from Phoenix span attributes (based on your telemetry patterns)."""
        import pandas as pd
        
        feedback = {}
        
        # Map Phoenix attribute names to feedback fields
        feedback_mapping = {
            'relevance': 'relevance',
            'clarity': 'clarity', 
            'factual_accuracy': 'factual_accuracy',
            'source_quality': 'source_quality',
            'feedback.text': 'feedback_text',
            'feedback.comment': 'feedback_text',
            'user_category': 'user_category',
            'feedback.type': 'feedback_type'
        }
        
        for attr_key, feedback_key in feedback_mapping.items():
            if attr_key in attributes and pd.notna(attributes[attr_key]):
                feedback[feedback_key] = attributes[attr_key]
        
        return feedback
    
    def _extract_citations_from_attributes(self, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract citations from span attributes."""
        import pandas as pd
        
        citations = []
        
        # Look for citation-related attributes
        for key, value in attributes.items():
            if key.startswith('citation') and pd.notna(value):
                citations.append({
                    "source": str(value),
                    "relevance": "medium"  # Default relevance
                })
        
        return citations
    
    async def _get_mock_sessions(
        self, 
        exclude_user_id: str = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        
        mock_sessions = [
            {
                "session_id": "session_001",
                "qa_id": "qa_001", 
                "span_id": "abcd1234efgh5678",
                "timestamp": "2024-01-15T10:30:00Z",
                "question": "What were the main provisions of the Parliamentary Reform Act of 1832?",
                "answer": "The Parliamentary Reform Act of 1832, also known as the Great Reform Act, was a significant piece of legislation that reshaped the British electoral system. The main provisions included: redistributing parliamentary seats from 'rotten boroughs' to growing industrial towns, extending voting rights to middle-class property owners in boroughs, and establishing more uniform electoral qualifications across England and Wales.",
                "original_feedback": {
                    "relevance": 4,
                    "clarity": 5,
                    "factual_accuracy": 4,
                    "source_quality": 4,
                    "user_category": "Digital HASS Researcher",
                    "feedback_text": "Good comprehensive answer with accurate historical detail."
                },
                "citations": [
                    {"source": "Hansard 1832-03-15", "relevance": "high"},
                    {"source": "Hansard 1832-03-22", "relevance": "medium"}
                ],
                "inter_rater_count": 1,
                "project_name": self.project_name,
                "original_user_id": "user_123"
            },
            {
                "session_id": "session_002",
                "qa_id": "qa_002",
                "span_id": "efgh5678ijkl9012", 
                "timestamp": "2024-01-16T14:15:00Z",
                "question": "How did the voting patterns change after the 1867 Reform Act?",
                "answer": "The 1867 Reform Act significantly expanded the electorate by extending voting rights to working-class men in boroughs. This led to notable changes in voting patterns: increased political participation from the working classes, strengthening of the Liberal Party in urban areas, and the emergence of more organized political campaigning to appeal to the expanded voter base.",
                "original_feedback": {
                    "relevance": 3,
                    "clarity": 4,
                    "factual_accuracy": 3,
                    "source_quality": 3,
                    "user_category": "Hansard Expert",
                    "feedback_text": "Could use more specific examples from the parliamentary debates."
                },
                "citations": [
                    {"source": "Hansard 1867-08-12", "relevance": "high"},
                    {"source": "Hansard 1867-09-05", "relevance": "high"}
                ],
                "inter_rater_count": 0,
                "project_name": self.project_name,
                "original_user_id": "user_456"
            }
        ]
        
        # Filter out sessions from the excluded user
        if exclude_user_id:
            mock_sessions = [
                session for session in mock_sessions 
                if session.get("original_user_id") != exclude_user_id
            ]
        
        return mock_sessions[:limit]
    
    async def get_span_details(self, span_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific span using Phoenix Python client.
        
        Args:
            span_id: The span ID to query
            
        Returns:
            Span details or None if not found
        """
        if not self.has_phoenix_client:
            return None
            
        try:
            # Query for specific span using Python client
            spans_df = self.client.get_spans_dataframe(
                project_name=self.project_name,
                filter_condition=f"span_id == '{span_id}'"
            )
            
            if spans_df.empty:
                return None
                
            # Return first matching span as dict
            return spans_df.iloc[0].to_dict()
            
        except Exception as e:
            logger.error(f"Error querying span details: {e}")
            return None

    def _get_phoenix_headers(self):
        """Get authentication headers for Phoenix API calls."""
        client_headers = os.getenv('PHOENIX_CLIENT_HEADERS')
        headers = {"Content-Type": "application/json"}
        
        phoenix_api_key = os.getenv('PHOENIX_API_KEY')
        if phoenix_api_key:
            if phoenix_api_key.startswith('api_key='):
                phoenix_api_key = phoenix_api_key[8:]
            headers['api_key'] = phoenix_api_key
            return headers
        
        if client_headers:
            try:
                if client_headers.startswith('api_key='):
                    api_key_value = client_headers[8:]
                    headers['api_key'] = api_key_value
                    return headers
                elif ':' in client_headers and not client_headers.startswith('{'):
                    headers['api_key'] = client_headers
                    return headers
                else:
                    import json
                    headers_dict = json.loads(client_headers)
                    if 'api_key' in headers_dict:
                        headers['api_key'] = headers_dict['api_key']
                        return headers
            except Exception:
                headers['api_key'] = client_headers
                return headers
        
        return headers

    def _format_span_id(self, span_id: str) -> str:
        """Format span_id as 16-character lowercase hex for Phoenix API."""
        try:
            span_id_int = int(span_id) if isinstance(span_id, str) else span_id
            return format(span_id_int, '016x')
        except (ValueError, TypeError):
            return str(span_id)

    async def check_user_already_rated(self, span_id: str, user_id: str) -> bool:
        """
        Check if a user has already provided inter-rater feedback for a span.
        
        Args:
            span_id: The original span ID
            user_id: The user ID to check
            
        Returns:
            True if user has already rated this span
        """
        if not self.has_phoenix_client:
            return False
            
        try:
            # Query Phoenix annotations API for existing inter-rater feedback by this user
            import httpx
            
            phoenix_endpoint = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com')
            annotations_endpoint = f"{phoenix_endpoint}/v1/span_annotations"
            
            headers = self._get_phoenix_headers()
            formatted_span_id = self._format_span_id(span_id)
            
            # Query annotations for this span
            response = httpx.get(
                f"{annotations_endpoint}?span_id={formatted_span_id}",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                annotations = response.json()
                
                # Check if any annotations have inter-rater metadata for this user
                for annotation in annotations.get('data', []):
                    metadata = annotation.get('metadata', {})
                    if (metadata.get('is_inter_rater') and 
                        metadata.get('rater_id') == user_id):
                        logger.debug(f"Found existing inter-rater feedback for user {user_id} on span {span_id}")
                        return True
                        
                return False
            else:
                logger.warning(f"Failed to query annotations for span {span_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking if user already rated: {e}")
            return False

    async def get_inter_rater_count(self, span_id: str) -> int:
        """
        Get the number of inter-rater feedback entries for a span.
        
        Args:
            span_id: The original span ID
            
        Returns:
            Number of inter-rater feedback entries
        """
        if not self.has_phoenix_client:
            return 1 if span_id == "abcd1234efgh5678" else 0
            
        try:
            # Query Phoenix annotations API for inter-rater feedback count
            import httpx
            
            phoenix_endpoint = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com')
            annotations_endpoint = f"{phoenix_endpoint}/v1/span_annotations"
            
            headers = self._get_phoenix_headers()
            formatted_span_id = self._format_span_id(span_id)
            
            # Query annotations for this span
            response = httpx.get(
                f"{annotations_endpoint}?span_id={formatted_span_id}",
                headers=headers,
                timeout=10.0
            )
            
            if response.status_code == 200:
                annotations = response.json()
                
                # Count unique inter-rater users (each user can only rate once)
                inter_rater_users = set()
                for annotation in annotations.get('data', []):
                    metadata = annotation.get('metadata', {})
                    if metadata.get('is_inter_rater') and metadata.get('rater_id'):
                        inter_rater_users.add(metadata['rater_id'])
                
                count = len(inter_rater_users)
                logger.debug(f"Found {count} inter-rater users for span {span_id}")
                return count
            else:
                logger.warning(f"Failed to query annotations for span {span_id}: {response.status_code}")
                return 0
                
        except Exception as e:
            logger.error(f"Error getting inter-rater count: {e}")
            return 0

# Global instance
phoenix_client = PhoenixAPIClient()
