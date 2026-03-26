"""
Local annotations cache for ATLAS inter-rater reliability.

Fetches all span annotations from Phoenix once, stores in memory,
and refreshes periodically. Eliminates per-span HTTP round-trips
that made inter-rater page loads take 60-90 seconds.

Pattern: bulk load on first access, local lookups, periodic delta sync.
"""

import asyncio
import logging
import os
import time
import threading
from collections import defaultdict
from typing import Dict, List, Any, Optional, Set

import httpx

logger = logging.getLogger(__name__)

# Annotation names that represent original user feedback (not inter-rater)
_USER_FEEDBACK_NAMES = frozenset([
    'Relevance Rating', 'Clarity', 'Factual Accuracy',
    'Analysis Quality', 'Additional Comments', 'Query Difficulty',
])


class AnnotationsCache:
    """
    In-memory cache of all Phoenix span annotations for a project.

    On first access, fetches all annotations via the REST API and indexes
    them by span_id. Subsequent lookups are local dict reads (<1ms).
    A background thread refreshes the cache every REFRESH_INTERVAL seconds.
    """

    REFRESH_INTERVAL = 300  # 5 minutes

    def __init__(self):
        self.project_name = os.getenv(
            "INTER_RATER_PROJECT",
            os.getenv("PHOENIX_PROJECT_NAME", "atlas-telemetry"),
        )
        self._phoenix_endpoint = os.getenv(
            "PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com"
        )

        # span_id -> list of raw annotation dicts
        self._by_span: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._loaded = False
        self._last_refresh: float = 0
        self._lock = threading.Lock()
        self._refresh_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public lookup API (all synchronous, <1ms)
    # ------------------------------------------------------------------

    def get_user_feedback(self, span_id: str) -> Dict[str, Any]:
        """
        Return the original user feedback for a span (not inter-rater).

        Maps annotation names to feedback fields matching the existing
        schema used by inter_rater_service / phoenix_client.
        Returns empty dict if span has no user feedback.
        """
        self._ensure_loaded()
        feedback: Dict[str, Any] = {}

        for ann in self._by_span.get(span_id, []):
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater", False):
                continue

            name = ann.get("name", "")
            if name not in _USER_FEEDBACK_NAMES:
                continue

            result = ann.get("result", {})
            score = result.get("score")
            explanation = result.get("explanation", "")

            if name == "Relevance Rating":
                feedback["relevance"] = score
            elif name == "Clarity":
                feedback["clarity"] = score
            elif name == "Factual Accuracy":
                feedback["factual_accuracy"] = score
            elif name == "Analysis Quality":
                feedback["analysis_quality"] = score
            elif name == "Additional Comments":
                feedback["feedback_text"] = explanation
            elif name == "Query Difficulty":
                feedback["query_difficulty"] = score

            # Capture metadata fields
            if metadata.get("qa_id"):
                feedback["qa_id"] = metadata["qa_id"]
            if metadata.get("feedback_type"):
                feedback["feedback_type"] = metadata["feedback_type"]
            if metadata.get("user_id"):
                feedback["user_id"] = metadata["user_id"]

        return feedback

    def has_user_feedback(self, span_id: str) -> bool:
        """True if span has at least one original user feedback annotation."""
        self._ensure_loaded()
        for ann in self._by_span.get(span_id, []):
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater", False):
                continue
            if ann.get("name", "") in _USER_FEEDBACK_NAMES:
                return True
        return False

    def span_ids_with_feedback(self) -> Set[str]:
        """Return set of span_ids that have original user feedback."""
        self._ensure_loaded()
        result = set()
        for span_id, annotations in self._by_span.items():
            for ann in annotations:
                metadata = ann.get("metadata", {})
                if metadata.get("is_inter_rater", False):
                    continue
                if ann.get("name", "") in _USER_FEEDBACK_NAMES:
                    result.add(span_id)
                    break
        return result

    def check_user_already_rated(self, span_id: str, user_id: str) -> bool:
        """True if user has already submitted inter-rater feedback for this span."""
        self._ensure_loaded()
        for ann in self._by_span.get(span_id, []):
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater") and metadata.get("rater_id") == user_id:
                return True
        return False

    def get_inter_rater_count(self, span_id: str) -> int:
        """Count of unique inter-rater users who have rated this span."""
        self._ensure_loaded()
        raters: Set[str] = set()
        for ann in self._by_span.get(span_id, []):
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater") and metadata.get("rater_id"):
                raters.add(metadata["rater_id"])
        return len(raters)

    # ------------------------------------------------------------------
    # Loading / refresh
    # ------------------------------------------------------------------

    def _ensure_loaded(self):
        """Load annotations on first access, start background refresh."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            self._fetch_all_annotations()
            self._loaded = True
            self._start_background_refresh()

    def refresh(self):
        """Force an immediate refresh (e.g. after feedback submission)."""
        self._fetch_all_annotations()

    def _fetch_all_annotations(self):
        """
        Fetch all annotations for the project via paginated REST API.
        Replaces the entire local index atomically.
        """
        url = f"{self._phoenix_endpoint}/v1/projects/{self.project_name}/span_annotations"
        headers = self._get_headers()
        new_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        total = 0
        cursor = None

        try:
            with httpx.Client(timeout=30.0) as client:
                while True:
                    params: Dict[str, Any] = {"limit": 1000}
                    if cursor:
                        params["cursor"] = cursor

                    resp = client.get(url, headers=headers, params=params)
                    if resp.status_code != 200:
                        logger.error(
                            f"Annotations fetch failed: {resp.status_code} {resp.text[:200]}"
                        )
                        break

                    body = resp.json()
                    data = body.get("data", [])
                    if not data:
                        break

                    for ann in data:
                        span_id = ann.get("span_id", "")
                        if span_id:
                            new_index[span_id].append(ann)
                            total += 1

                    cursor = body.get("next_cursor")
                    if not cursor:
                        break

            # Atomic swap
            self._by_span = new_index
            self._last_refresh = time.time()
            logger.info(
                f"Annotations cache loaded: {total} annotations across "
                f"{len(new_index)} spans for project '{self.project_name}'"
            )

        except Exception as e:
            logger.error(f"Failed to fetch annotations: {e}")
            # Keep stale data if we had any
            if not self._by_span:
                self._by_span = new_index

    def _start_background_refresh(self):
        """Start a daemon thread that refreshes the cache periodically."""
        if self._refresh_thread and self._refresh_thread.is_alive():
            return

        def _loop():
            while True:
                time.sleep(self.REFRESH_INTERVAL)
                try:
                    self._fetch_all_annotations()
                except Exception as e:
                    logger.error(f"Background annotations refresh failed: {e}")

        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()
        logger.info(
            f"Annotations cache background refresh started "
            f"(every {self.REFRESH_INTERVAL}s)"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Auth headers for Phoenix REST API."""
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        api_key = os.getenv("PHOENIX_API_KEY")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers


# Global singleton
annotations_cache = AnnotationsCache()
