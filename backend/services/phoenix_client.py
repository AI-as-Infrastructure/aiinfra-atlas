"""
Phoenix API client for querying spans with feedback for inter-rater reliability.

This client handles:
1. Querying Phoenix for existing spans with feedback using the Python client
2. Extracting session data for inter-rating
3. Using the local AnnotationsCache for fast feedback lookups

The client uses the Phoenix Python client for span queries and the
AnnotationsCache for annotation lookups (no per-span HTTP round-trips).
"""

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

        # Align default with telemetry project if env not provided
        self.project_name = os.getenv("INTER_RATER_PROJECT", os.getenv("PHOENIX_PROJECT_NAME", "atlas-telemetry"))

    async def query_spans_with_feedback(
        self,
        exclude_user_id: str = None,
        limit: int = 10,
        days_back: int = 30,
        include_citations: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query Phoenix for spans that have original feedback and are eligible for inter-rating.

        Uses the AnnotationsCache for feedback lookups (no per-span HTTP calls).

        Args:
            exclude_user_id: User ID to exclude (don't show user their own sessions)
            limit: Maximum number of sessions to return
            days_back: How many days back to look for sessions
            include_citations: If False, skip REFERENCES span query (faster for counts)

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
            real_sessions = await self._query_phoenix_with_client(exclude_user_id, limit, days_back, include_citations)
            if real_sessions:
                logger.info(f"Retrieved {len(real_sessions)} sessions from Phoenix project '{self.project_name}'")
                return real_sessions
            else:
                logger.info(f"No sessions with feedback found in Phoenix project '{self.project_name}' for the last {days_back} days")
                return []
        except ValueError:
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
        days_back: int = 30,
        include_citations: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Query Phoenix for generation response spans, then match against
        the local AnnotationsCache to find spans with user feedback.
        """
        from datetime import datetime, timedelta
        from .annotations_cache import annotations_cache

        if not self.client:
            raise ValueError("Phoenix client not initialized")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        logger.info(f"Querying Phoenix for project '{self.project_name}' (last {days_back} days)")

        try:
            # Server-side filter: only fetch generation response LLM spans
            filter_expr = "name == 'com.atlas.rag.generation.response' and span_kind == 'LLM'"

            spans_df = self.client.get_spans_dataframe(
                filter_expr,
                project_name=self.project_name,
                start_time=start_date,
                end_time=end_date,
                timeout=30
            )

            if spans_df.empty:
                logger.info("No generation response spans found in Phoenix")
                return []

            logger.info(f"Found {len(spans_df)} generation response spans from Phoenix")

            # Collect all span IDs and batch-fetch their annotations
            all_span_ids = [
                row.get('context.span_id')
                for _, row in spans_df.iterrows()
                if row.get('context.span_id')
            ]
            annotations_cache.load(all_span_ids)

            # Now all lookups are local dict reads
            spans_with_feedback = annotations_cache.span_ids_with_feedback()
            logger.info(f"Annotations cache: {len(spans_with_feedback)} spans have user feedback")

            # Build session data — all lookups are local, no HTTP calls
            feedback_spans = []

            for _, row in spans_df.iterrows():
                # Check sufficient output
                output_value = row.get('attributes.output.value')
                if not output_value or len(str(output_value)) < 10:
                    continue

                span_id = row.get('context.span_id')
                if not span_id:
                    continue

                # Fast local check: does this span have user feedback?
                if span_id not in spans_with_feedback:
                    continue

                # Get feedback from cache (local dict read)
                original_feedback = annotations_cache.get_user_feedback(span_id)
                if not original_feedback:
                    continue

                # Extract attributes
                attributes = {}
                for col in spans_df.columns:
                    if col.startswith('attributes.'):
                        key = col.replace('attributes.', '')
                        attributes[key] = row[col]

                session_id = attributes.get('session.id', f"session_{span_id[:8]}")
                qa_id = attributes.get('qa_id', f"qa_{span_id[:8]}")
                citations = self._extract_citations_from_attributes(attributes)

                # Remove user_id from original_feedback before sending to frontend (privacy)
                safe_feedback = {k: v for k, v in original_feedback.items() if k != 'user_id'}

                session_data = {
                    "session_id": session_id,
                    "qa_id": qa_id,
                    "span_id": span_id,
                    "timestamp": row.get('start_time', datetime.now()).isoformat(),
                    "question": attributes.get('input.value', 'Question not available'),
                    "answer": attributes.get('output', 'Answer not available'),
                    "original_feedback": safe_feedback,
                    "citations": citations,
                    "inter_rater_count": annotations_cache.get_inter_rater_count(span_id),
                    "project_name": self.project_name,
                    "original_user_id": original_feedback.get('user_id', 'unknown')  # Used only for filtering, not sent to frontend
                }

                feedback_spans.append(session_data)

            # Fetch REFERENCES spans to populate citations (stored separately from LLM spans)
            if include_citations:
                citations_by_qa_id = self._fetch_citations_by_qa_id(start_date, end_date)
                if citations_by_qa_id:
                    for session in feedback_spans:
                        if not session['citations']:
                            session['citations'] = citations_by_qa_id.get(session['qa_id'], [])

            # Exclude sessions created by requesting user
            if exclude_user_id:
                original_count = len(feedback_spans)
                filtered = []
                excluded_count = 0
                missing_uid = 0

                for session in feedback_spans:
                    uid = session.get("original_user_id")
                    if not uid:
                        missing_uid += 1
                        filtered.append(session)
                    elif uid == exclude_user_id:
                        excluded_count += 1
                    else:
                        filtered.append(session)

                feedback_spans = filtered
                logger.info(
                    f"User exclusion: {original_count} total → {len(feedback_spans)} available, "
                    f"{excluded_count} excluded (own), {missing_uid} missing user_id"
                )

            # Sort by timestamp (most recent first) and limit
            feedback_spans.sort(key=lambda x: x['timestamp'], reverse=True)
            result = feedback_spans[:limit]

            # Remove original_user_id before sending to frontend (privacy - used only for filtering)
            for session in result:
                session.pop('original_user_id', None)

            logger.info(f"Returning {len(result)} spans with feedback for inter-rating")
            return result

        except Exception as e:
            logger.error(f"Error querying Phoenix with client: {e}")
            raise

    def _fetch_citations_by_qa_id(self, start_date, end_date) -> Dict[str, List[Dict[str, Any]]]:
        """
        Query REFERENCES spans to build a qa_id → citations map.
        Citations are stored on REFERENCES spans, not on the LLM span queried for inter-rater.
        """
        try:
            refs_df = self.client.get_spans_dataframe(
                "name == 'com.atlas.rag.references'",
                project_name=self.project_name,
                start_time=start_date,
                end_time=end_date,
                timeout=30
            )
            if refs_df is None or refs_df.empty:
                return {}

            citations_map = {}
            for _, row in refs_df.iterrows():
                attributes = {}
                for col in refs_df.columns:
                    if col.startswith('attributes.'):
                        attributes[col.replace('attributes.', '')] = row[col]

                qa_id = attributes.get('qa_id')
                if not qa_id:
                    continue

                citations = self._extract_citations_from_attributes(attributes)
                if citations:
                    citations_map[qa_id] = citations

            logger.info(f"Built citations map for {len(citations_map)} qa_ids from REFERENCES spans")
            return citations_map

        except Exception as e:
            logger.warning(f"Failed to fetch REFERENCES spans for citations: {e}")
            return {}

    def _extract_citations_from_attributes(self, attributes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract citations from span attributes."""
        import json

        citations = []

        # Try JSON citations attribute
        citations_json = attributes.get('citations')
        if citations_json and str(citations_json).strip() != '':
            try:
                citations_data = json.loads(str(citations_json))
                if isinstance(citations_data, list):
                    return citations_data
            except (json.JSONDecodeError, TypeError):
                pass

        # Try all_citations
        all_citations_json = attributes.get('all_citations')
        if all_citations_json and str(all_citations_json).strip() != '':
            try:
                citations_data = json.loads(str(all_citations_json))
                if isinstance(citations_data, list):
                    return citations_data
            except (json.JSONDecodeError, TypeError):
                pass

        # Fallback: individual citation attributes (citation_0_title, etc.)
        citation_indices = set()
        for key in attributes.keys():
            if key.startswith('citation_') and '_' in key[9:]:
                try:
                    idx = int(key.split('_')[1])
                    citation_indices.add(idx)
                except (ValueError, IndexError):
                    continue

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
            if citation:
                citations.append(citation)

        return citations

    async def get_span_details(self, span_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific span."""
        if not self.has_phoenix_client:
            return None

        try:
            spans_df = self.client.get_spans_dataframe(
                project_name=self.project_name,
                filter_condition=f"span_id == '{span_id}'",
                timeout=30
            )
            if spans_df.empty:
                return None
            return spans_df.iloc[0].to_dict()
        except Exception as e:
            logger.error(f"Error querying span details: {e}")
            return None

# Global instance
phoenix_client = PhoenixAPIClient()
