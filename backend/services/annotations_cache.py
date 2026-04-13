"""
Local annotations cache for ATLAS inter-rater reliability.

Fetches span annotations from Phoenix in batches (grouped by span_id),
stores in memory, and provides instant local lookups. Eliminates
per-span HTTP round-trips that made inter-rater loads take 60-90s.

The Phoenix API requires span_ids on every request, so the cache is
populated by passing span IDs from the spans dataframe query. Once
loaded, all annotation lookups are local dict reads (<1ms).
"""

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

# Max span_ids per request (URL length safety — ~20 chars per ID)
_BATCH_SIZE = 100


class AnnotationsCache:
    """
    In-memory cache of Phoenix span annotations for a project.

    Call load(span_ids) with the span IDs from get_spans_dataframe().
    Annotations are fetched in batches and indexed by span_id.
    All subsequent lookups are local dict reads (<1ms).
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
        # Track which span_ids we've fetched annotations for
        self._known_span_ids: Set[str] = set()
        self._last_refresh: float = 0
        self._lock = threading.Lock()
        self._refresh_thread: Optional[threading.Thread] = None
        # Local write cache: (span_id, user_id) pairs for ratings submitted
        # this process but not yet propagated to Phoenix
        self._local_ratings: Set[tuple] = set()

    # ------------------------------------------------------------------
    # Loading — called by phoenix_client after spans query
    # ------------------------------------------------------------------

    def load(self, span_ids: List[str]):
        """
        Fetch annotations for the given span_ids in batches and cache locally.

        Safe to call multiple times — only fetches IDs not already cached.
        Starts a background refresh thread on first call to keep data fresh
        for concurrent users.
        """
        new_ids = [sid for sid in span_ids if sid not in self._known_span_ids]
        if not new_ids:
            logger.debug(f"All {len(span_ids)} span_ids already cached")
            return

        logger.info(f"Fetching annotations for {len(new_ids)} new span_ids ({len(self._known_span_ids)} already cached)")
        self._fetch_annotations_for_ids(new_ids)
        self._start_background_refresh()

    def refresh(self):
        """Force re-fetch annotations for all known span_ids."""
        if not self._known_span_ids:
            return
        all_ids = list(self._known_span_ids)
        logger.info(f"Refreshing annotations for {len(all_ids)} span_ids")
        self._fetch_annotations_for_ids(all_ids, replace=True)

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
        for ann in self._by_span.get(span_id, []):
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater", False):
                continue
            if ann.get("name", "") in _USER_FEEDBACK_NAMES:
                return True
        return False

    def span_ids_with_feedback(self) -> Set[str]:
        """Return set of span_ids that have original user feedback."""
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

    def record_user_rating(self, span_id: str, user_id: str):
        """Record a local inter-rater rating before Phoenix propagation."""
        self._local_ratings.add((span_id, user_id))

    def check_user_already_rated(self, span_id: str, user_id: str) -> bool:
        """True if user has already submitted inter-rater feedback for this span."""
        if (span_id, user_id) in self._local_ratings:
            return True
        for ann in self._by_span.get(span_id, []):
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater") and metadata.get("rater_id") == user_id:
                return True
        return False

    def get_inter_rater_count(self, span_id: str) -> int:
        """Count of unique inter-rater users who have rated this span."""
        raters: Set[str] = set()
        for ann in self._by_span.get(span_id, []):
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater") and metadata.get("rater_id"):
                raters.add(metadata["rater_id"])
        return len(raters)

    # ------------------------------------------------------------------
    # Internal fetch
    # ------------------------------------------------------------------

    def _fetch_annotations_for_ids(self, span_ids: List[str], replace: bool = False):
        """
        Fetch annotations for span_ids in batches and add to the local index.

        Args:
            span_ids: List of span IDs to fetch annotations for
            replace: If True, clear existing entries for these IDs first
        """
        url = f"{self._phoenix_endpoint}/v1/projects/{self.project_name}/span_annotations"
        headers = self._get_headers()
        total_fetched = 0

        if replace:
            with self._lock:
                for sid in span_ids:
                    self._by_span.pop(sid, None)

        # Batch into groups to avoid URL length limits
        batches = [span_ids[i:i + _BATCH_SIZE] for i in range(0, len(span_ids), _BATCH_SIZE)]

        try:
            with httpx.Client(timeout=30.0) as client:
                for batch_num, batch in enumerate(batches):
                    cursor = None

                    while True:
                        # Pass span_ids as repeated query params
                        params: List[tuple] = [("span_ids", sid) for sid in batch]
                        params.append(("limit", "1000"))
                        if cursor:
                            params.append(("cursor", cursor))

                        resp = client.get(url, headers=headers, params=params)
                        if resp.status_code != 200:
                            logger.error(
                                f"Annotations batch {batch_num + 1}/{len(batches)} failed: "
                                f"{resp.status_code} {resp.text[:200]}"
                            )
                            break

                        body = resp.json()
                        data = body.get("data", [])
                        if not data:
                            break

                        with self._lock:
                            for ann in data:
                                sid = ann.get("span_id", "")
                                if sid:
                                    self._by_span[sid].append(ann)
                                    total_fetched += 1

                        cursor = body.get("next_cursor")
                        if not cursor:
                            break

            # Track all IDs we've fetched
            self._known_span_ids.update(span_ids)
            self._last_refresh = time.time()

            spans_with_data = sum(1 for sid in span_ids if sid in self._by_span and self._by_span[sid])
            logger.info(
                f"Annotations cache: fetched {total_fetched} annotations "
                f"for {spans_with_data}/{len(span_ids)} spans"
            )

        except Exception as e:
            logger.error(f"Failed to fetch annotations: {e}")

    def _start_background_refresh(self):
        """Start a daemon thread that refreshes known annotations periodically."""
        if self._refresh_thread and self._refresh_thread.is_alive():
            return

        def _loop():
            while True:
                time.sleep(self.REFRESH_INTERVAL)
                try:
                    if self._known_span_ids:
                        self._fetch_annotations_for_ids(
                            list(self._known_span_ids), replace=True
                        )
                except Exception as e:
                    logger.error(f"Background annotations refresh failed: {e}")

        self._refresh_thread = threading.Thread(target=_loop, daemon=True)
        self._refresh_thread.start()
        logger.info(
            f"Annotations background refresh started (every {self.REFRESH_INTERVAL}s)"
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
