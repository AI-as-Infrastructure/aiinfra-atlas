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
            
        # Use the same project as telemetry
        self.project_name = os.getenv("PHOENIX_PROJECT_NAME", "atlas-telemetry")

    def _get_phoenix_endpoint(self) -> str:
        """Get configured Phoenix endpoint (strict, no fallback)."""
        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "").strip()
        if not endpoint:
            raise ValueError("PHOENIX_COLLECTOR_ENDPOINT is not configured")

        if "app.phoenix.arize.com" in endpoint and "/s/" not in endpoint:
            raise ValueError(
                "PHOENIX_COLLECTOR_ENDPOINT must include '/s/<space-id>' when using Phoenix cloud"
            )

        return endpoint.rstrip("/")
    
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
            
        Raises:
            ValueError: When no Phoenix data is available for inter-rating
        """
        
        if not self.has_phoenix_client:
            raise ValueError(
                f"Phoenix client not available. Cannot fetch inter-rater sessions for project '{self.project_name}'. "
                f"Please check Phoenix configuration and ensure the client is properly installed."
            )
        
        try:
            real_sessions = await self._query_phoenix_with_client(exclude_user_id, limit, days_back)
            if real_sessions:
                logger.info(f"Retrieved {len(real_sessions)} sessions from Phoenix project '{self.project_name}'")
                return real_sessions
            else:
                # No sessions found - return empty list instead of raising error
                logger.info(f"No sessions with feedback found in Phoenix project '{self.project_name}' for the last {days_back} days")
                return []
        except ValueError:
            # Re-raise ValueError with our custom message
            raise
        except Exception as e:
            raise ValueError(
                f"Failed to query Phoenix project '{self.project_name}': {str(e)}. "
                f"Please check Phoenix connection, API credentials, and project access."
            )
    
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
        
        logger.info(f"Querying Phoenix for project '{self.project_name}' (last {days_back} days)")
        
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
            
            # Filter for generation response spans (these are the ones with user feedback)
            generation_response_spans = []
            
            for _, row in spans_df.iterrows():
                # Look specifically for com.atlas.rag.generation.response spans
                span_name = row.get('name', '')
                span_kind = row.get('attributes.openinference.span.kind')
                
                logger.debug(f"Checking span: name='{span_name}', kind='{span_kind}'")
                
                if span_name != 'com.atlas.rag.generation.response' or span_kind != 'LLM':
                    continue
                    
                # Must have some output (can be short metadata like "Generated response (244 words, 11.01s)")
                output_value = row.get('attributes.output.value')
                output_len = len(str(output_value)) if output_value else 0
                logger.debug(f"Output length: {output_len}")
                
                if not output_value or output_len < 10:
                    logger.debug(f"Skipping span - insufficient output: {output_len} chars")
                    continue
                    
                generation_response_spans.append(row)
                logger.debug(f"Added generation response span: {row.get('context.span_id', 'unknown')}")
            
            logger.info(f"Found {len(generation_response_spans)} generation response spans")
            
            # Filter generation response spans to only include those with user feedback annotations
            feedback_spans = []
            
            for row in generation_response_spans:
                span_id = row.get('context.span_id')
                if not span_id:
                    continue
                
                # Extract attributes for session data
                attributes = {}
                for col in spans_df.columns:
                    if col.startswith('attributes.'):
                        key = col.replace('attributes.', '')
                        attributes[key] = row[col]
                
                # Get original feedback from annotations
                original_feedback = await self._get_span_feedback_annotations(span_id)
                
                # Skip spans without any user feedback annotations
                if not original_feedback or len(original_feedback) == 0:
                    logger.debug(f"Skipping span {span_id[:8]}... - no user feedback annotations found")
                    continue
                
                # Look for citations in related reference spans
                session_id = attributes.get('session.id', f"session_{span_id[:8]}")
                qa_id = attributes.get('qa_id', f"qa_{span_id[:8]}")
                citations = await self._get_citations_for_session(session_id, qa_id, spans_df)
                
                # Extract session data
                session_data = {
                    "session_id": session_id,
                    "qa_id": qa_id,
                    "span_id": span_id,
                    "timestamp": row.get('start_time', datetime.now()).isoformat(),
                    "question": attributes.get('input.value', 'Question not available'),
                    "answer": attributes.get('output', 'Answer not available'),  # Use 'output' not 'output.value'
                    "original_feedback": original_feedback,
                    "citations": citations,
                    "inter_rater_count": 0,  # Will be calculated separately
                    "project_name": self.project_name,
                    "original_user_id": original_feedback.get('user_id', 'unknown')
                }
                
                feedback_spans.append(session_data)
            
            # Exclude sessions created by requesting user if we have a user_id captured
            if exclude_user_id:
                try:
                    original_count = len(feedback_spans)
                    # Filter out sessions created by the requesting user
                    filtered_spans = []
                    excluded_count = 0
                    missing_user_id_count = 0
                    
                    for session in feedback_spans:
                        original_user_id = session.get("original_user_id")
                        if not original_user_id:
                            missing_user_id_count += 1
                            logger.warning(f"Session {session.get('span_id', 'unknown')[:8]}... has no original_user_id - cannot exclude properly")
                            filtered_spans.append(session)  # Include it since we can't exclude it
                        elif original_user_id == exclude_user_id:
                            excluded_count += 1
                            logger.debug(f"Excluding session {session.get('span_id', 'unknown')[:8]}... created by requesting user")
                        else:
                            filtered_spans.append(session)
                    
                    feedback_spans = filtered_spans
                    logger.info(f"User exclusion results: {original_count} total → {len(feedback_spans)} available, {excluded_count} excluded (own), {missing_user_id_count} missing user_id")
                    
                    if missing_user_id_count > 0:
                        logger.warning(f"INTER-RATER ISSUE: {missing_user_id_count} sessions have no user_id - user may see their own ratings!")
                        
                except Exception as e:
                    logger.error(f"Error during user exclusion filtering: {e}")
                    pass

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
            if (attr_key in attributes and 
                attributes[attr_key] is not None and 
                str(attributes[attr_key]).strip() != ''):
                feedback[feedback_key] = attributes[attr_key]
        
        return feedback
    
    def _extract_citations_from_attributes(self, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract citations from span attributes."""
        import json
        
        citations = []
        
        # First, try to get citations from the 'citations' attribute (JSON string)
        citations_json = attributes.get('citations')
        if citations_json and str(citations_json).strip() != '':
            try:
                citations_data = json.loads(str(citations_json))
                if isinstance(citations_data, list):
                    citations = citations_data
                    logger.debug(f"Extracted {len(citations)} citations from JSON")
                    return citations
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse citations JSON: {e}")
        
        # Try to get from 'all_citations' if 'citations' didn't work
        all_citations_json = attributes.get('all_citations')
        if all_citations_json and str(all_citations_json).strip() != '':
            try:
                citations_data = json.loads(str(all_citations_json))
                if isinstance(citations_data, list):
                    citations = citations_data
                    logger.debug(f"Extracted {len(citations)} citations from all_citations JSON")
                    return citations
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to parse all_citations JSON: {e}")
        
        # Fallback: look for individual citation attributes (citation_0_title, citation_0_source, etc.)
        citation_indices = set()
        for key in attributes.keys():
            if key.startswith('citation_') and '_' in key[9:]:  # citation_X_field format
                try:
                    idx = int(key.split('_')[1])
                    citation_indices.add(idx)
                except (ValueError, IndexError):
                    continue
        
        # Build citations from individual attributes
        for idx in sorted(citation_indices):
            citation = {}
            title = attributes.get(f'citation_{idx}_title')
            source = attributes.get(f'citation_{idx}_source')
            date = attributes.get(f'citation_{idx}_date')
            
            if title:
                citation['title'] = str(title)
            if source:
                citation['source'] = str(source)
            if date:
                citation['date'] = str(date)
            
            if citation:  # Only add if we have at least one field
                citations.append(citation)
        
        logger.debug(f"Extracted {len(citations)} citations from individual attributes")
        return citations
    
    async def _get_citations_for_session(self, session_id: str, qa_id: str, spans_df) -> List[Dict[str, Any]]:
        """
        Find citations for a session by looking for com.atlas.rag.references spans.
        """
        citations = []
        
        # Look for reference spans with matching session and qa_id
        for _, row in spans_df.iterrows():
            span_name = row.get('name', '')
            if span_name != 'com.atlas.rag.references':
                continue
            
            # Check if this reference span belongs to our session/qa
            span_session_id = row.get('attributes.session.id')
            span_qa_id = row.get('attributes.qa_id')
            
            if span_session_id == session_id and span_qa_id == qa_id:
                # Extract attributes for this reference span
                ref_attributes = {}
                for col in spans_df.columns:
                    if col.startswith('attributes.'):
                        key = col.replace('attributes.', '')
                        ref_attributes[key] = row[col]
                
                # Extract citations from this reference span
                ref_citations = self._extract_citations_from_attributes(ref_attributes)
                citations.extend(ref_citations)
                logger.debug(f"Found {len(ref_citations)} citations in reference span for session {session_id}")
                break  # Usually only one reference span per session/qa
        
        return citations
    
    async def _check_span_has_user_feedback(self, span_id: str) -> bool:
        """
        Check if a span has user feedback annotations (not inter-rater feedback).
        """
        try:
            import httpx
            
            phoenix_endpoint = self._get_phoenix_endpoint()
            # Use correct v11.13.2 API format with project in path
            annotations_endpoint = f"{phoenix_endpoint}/v1/projects/{self.project_name}/span_annotations"
            
            headers = self._get_phoenix_headers()
            
            # Use span_ids parameter (not span_id) as per v11.13.2 API
            params = {
                "span_ids": span_id,
                "limit": 100
            }
            
            response = httpx.get(
                annotations_endpoint,
                headers=headers,
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 200:
                annotations = response.json()
                
                # Look for user feedback annotations (not inter-rater) (Phoenix v11.13.2 uses 'data' not 'annotations')
                for annotation in annotations.get('data', []):
                    metadata = annotation.get('metadata', {})
                    # Skip inter-rater feedback
                    if metadata.get('is_inter_rater', False):
                        continue
                        
                    # Check for any user feedback annotation (not just "user feedback" name)
                    annotation_name = annotation.get('name', '')
                    if annotation_name in ['Relevance Rating', 'Clarity', 'Factual Accuracy', 'Analysis Quality', 'Additional Comments', 'Query Difficulty']:
                        return True
                        
                return False
            else:
                logger.warning(f"Failed to query annotations for span {span_id[:8]}...: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking span feedback: {e}")
            return False
    
    async def _get_span_feedback_annotations(self, span_id: str) -> dict:
        """
        Get the original user feedback from span annotations.
        """
        try:
            import httpx
            
            phoenix_endpoint = self._get_phoenix_endpoint()
            # Use correct v11.13.2 API format with project in path
            annotations_endpoint = f"{phoenix_endpoint}/v1/projects/{self.project_name}/span_annotations"
            
            headers = self._get_phoenix_headers()
            
            # Use span_ids parameter (not span_id) as per v11.13.2 API
            params = {
                "span_ids": span_id,
                "limit": 100
            }
            
            response = httpx.get(
                annotations_endpoint,
                headers=headers,
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 200:
                annotations = response.json()
                feedback = {}
                
                # Extract feedback from annotations (Phoenix v11.13.2 uses 'data' not 'annotations')
                for annotation in annotations.get('data', []):
                    metadata = annotation.get('metadata', {})
                    result = annotation.get('result', {})
                    
                    # Only get original user feedback (not inter-rater)
                    # Skip inter-rater feedback based on metadata
                    if metadata.get('is_inter_rater', False):
                        continue
                    
                    # Map Phoenix annotation names to feedback fields
                    annotation_name = annotation.get('name', '')
                    label = result.get('label', '')
                    score = result.get('score')
                    explanation = result.get('explanation', '')
                    
                    # Map annotation types to our feedback structure
                    if annotation_name == 'Relevance Rating' or label == 'relevance':
                        feedback['relevance'] = score
                    elif annotation_name == 'Clarity' or label == 'clarity':
                        feedback['clarity'] = score
                    elif annotation_name == 'Factual Accuracy' or label == 'factual_accuracy':
                        feedback['factual_accuracy'] = score
                    elif annotation_name == 'Analysis Quality' or label == 'analysis_quality':
                        feedback['analysis_quality'] = score
                    elif annotation_name == 'Additional Comments' or label == 'additional_feedback':
                        feedback['feedback_text'] = explanation
                    elif annotation_name == 'Query Difficulty' or label == 'query_difficulty':
                        feedback['query_difficulty'] = score
                        
                    # Get QA ID and other metadata
                    if metadata.get('qa_id'):
                        feedback['qa_id'] = metadata['qa_id']
                    if metadata.get('feedback_type'):
                        feedback['feedback_type'] = metadata['feedback_type']
                    # Capture original rater anon user id
                    if metadata.get('user_id'):
                        feedback['user_id'] = metadata['user_id']
                        logger.debug(f"Found user_id in annotation metadata: {metadata['user_id'][:12]}...")
                    else:
                        logger.debug(f"No user_id in annotation metadata for span {span_id[:8]}... - metadata keys: {list(metadata.keys())}")
                
                # Log final feedback extraction result for debugging
                user_id_present = 'user_id' in feedback
                logger.debug(f"Extracted feedback for span {span_id[:8]}...: user_id_present={user_id_present}, feedback_keys={list(feedback.keys())}")
                
                return feedback
            else:
                logger.warning(f"Failed to get feedback annotations for span {span_id[:8]}...: {response.status_code}")
                logger.warning(f"Response: {response.text[:200]}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting span feedback annotations: {e}")
            return {}
    
    
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
        """Get headers for Phoenix API calls using Bearer authentication (spaces format)."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        # Use PHOENIX_API_KEY with Bearer authentication for spaces architecture
        phoenix_api_key = os.getenv('PHOENIX_API_KEY')
        if phoenix_api_key:
            headers['Authorization'] = f'Bearer {phoenix_api_key}'
            return headers

        logger.warning("PHOENIX_API_KEY not configured - inter-rater API calls will fail")
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
        try:
            # Query Phoenix annotations API for existing inter-rater feedback by this user
            import httpx
            
            phoenix_endpoint = self._get_phoenix_endpoint()
            # Use correct v11.13.2 API format with project in path
            annotations_endpoint = f"{phoenix_endpoint}/v1/projects/{self.project_name}/span_annotations"
            
            headers = self._get_phoenix_headers()
            
            # Use span_ids parameter (not span_id) as per v11.13.2 API
            params = {
                "span_ids": span_id,
                "limit": 100
            }
            
            # Query annotations for this span
            response = httpx.get(
                annotations_endpoint,
                headers=headers,
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 200:
                annotations = response.json()
                
                # Debug logging to see what we're getting from Phoenix
                sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
                sanitized_span_id = span_id[:8] + "..." if len(span_id) > 8 else span_id
                logger.debug(f"Checking user {sanitized_user_id} for span {sanitized_span_id} - found {len(annotations.get('data', []))} annotations")
                
                # Check if any annotations have inter-rater metadata for this user (Phoenix v11.13.2 uses 'data' not 'annotations')
                for annotation in annotations.get('data', []):
                    metadata = annotation.get('metadata', {})
                    
                    if (metadata.get('is_inter_rater') and 
                        metadata.get('rater_id') == user_id):
                        logger.debug(f"Found existing inter-rater feedback for user {sanitized_user_id} on span {sanitized_span_id}")
                        return True
                        
                return False
            else:
                sanitized_span_id = span_id[:8] + "..." if len(span_id) > 8 else span_id
                logger.warning(f"Failed to query annotations for span {sanitized_span_id}: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking if user already rated: {e}")
            return False

    async def get_inter_rater_count(self, span_id: str) -> int:
        """
        Get the number of inter-rater feedback entries for a span.
        Uses async httpx to avoid blocking the event loop.

        Args:
            span_id: The original span ID

        Returns:
            Number of inter-rater feedback entries
        """
        try:
            # Query Phoenix annotations API for inter-rater feedback count
            import httpx

            phoenix_endpoint = self._get_phoenix_endpoint()
            # Use correct v11.13.2 API format with project in path
            annotations_endpoint = f"{phoenix_endpoint}/v1/projects/{self.project_name}/span_annotations"

            headers = self._get_phoenix_headers()

            # Use span_ids parameter (not span_id) as per v11.13.2 API
            params = {
                "span_ids": span_id,
                "limit": 100
            }

            # Use async httpx client to avoid blocking event loop
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    annotations_endpoint,
                    headers=headers,
                    params=params,
                    timeout=10.0
                )

            if response.status_code == 200:
                annotations = response.json()

                # Debug logging to see what we're getting from Phoenix
                sanitized_span_id = span_id[:8] + "..." if len(span_id) > 8 else span_id
                logger.debug(f"Getting inter-rater count for span {sanitized_span_id} - found {len(annotations.get('data', []))} annotations")

                # Count unique inter-rater users (each user can only rate once) (Phoenix v11.13.2 uses 'data' not 'annotations')
                inter_rater_users = set()
                for annotation in annotations.get('data', []):
                    metadata = annotation.get('metadata', {})

                    if metadata.get('is_inter_rater') and metadata.get('rater_id'):
                        inter_rater_users.add(metadata['rater_id'])

                count = len(inter_rater_users)
                sanitized_span_id = span_id[:8] + "..." if len(span_id) > 8 else span_id
                logger.info(f"Found {count} inter-rater users for span {sanitized_span_id}")
                return count
            else:
                sanitized_span_id = span_id[:8] + "..." if len(span_id) > 8 else span_id
                logger.warning(f"Failed to query annotations for span {sanitized_span_id}: {response.status_code}")
                return 0

        except Exception as e:
            logger.error(f"Error getting inter-rater count: {e}")
            return 0

# Global instance
phoenix_client = PhoenixAPIClient()
