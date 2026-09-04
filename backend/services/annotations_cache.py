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
import re
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

# Inter-rater annotations are name-prefixed by feedback.get_annotation_name:
# "[inter-rating-2] Corpus Fidelity", or "[Inter-rater] ..." when the rating
# number was unavailable. The prefix is the only link between a rating's
# metadata-poor annotations and their author.
_INTER_RATER_NUMBERED = re.compile(r"^\[inter-rating-(\d+)\]\s+(.+)$")
_INTER_RATER_UNNUMBERED = "[Inter-rater] "

# Annotation base names written by the current (v0.4.0) rubric.
_RUBRIC_SCORES = {
    "Corpus Fidelity": "corpus_fidelity",
    "Citation Quality": "citation_quality",
    "Relevance Rating": "relevance",
    "Coherence": "coherence",
    "Uncertainty": "uncertainty",
    "Historical Contextualisation": "historical_contextualisation",
}
_RUBRIC_RATIONALES = {
    "Corpus Fidelity Comment": "corpus_fidelity",
    "Citation Quality Comment": "citation_quality",
    "Relevance Comment": "relevance",
    "Coherence Comment": "coherence",
    "Uncertainty Comment": "uncertainty",
    "Historical Contextualisation Comment": "historical_contextualisation",
}
_FAULT_PREFIX = "Fault: "


def _parse_inter_rater_name(name: str):
    """
    Split an inter-rater annotation name into (group_key, base_name).

    Returns None for annotations that are not inter-rater prefixed. The group
    key is the rating number, or "unnumbered" for the fallback prefix.
    """
    match = _INTER_RATER_NUMBERED.match(name)
    if match:
        return match.group(1), match.group(2)
    if name.startswith(_INTER_RATER_UNNUMBERED):
        return "unnumbered", name[len(_INTER_RATER_UNNUMBERED):]
    return None


class AnnotationsCache:
    """
    In-memory cache of Phoenix span annotations for a project.

    Call load(span_ids) with the span IDs from get_spans_dataframe().
    Annotations are fetched in batches and indexed by span_id.
    All subsequent lookups are local dict reads (<1ms).
    """

    REFRESH_INTERVAL = 300  # 5 minutes

    def __init__(self):
        self.project_name = os.getenv("INTER_RATER_PROJECT") or os.getenv("PHOENIX_PROJECT_NAME")
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
        # Local write cache: (span_id, user_id) pairs successfully submitted
        # by this process, retained for immediate read-your-write behaviour.
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
        """Record a successful local inter-rater rating for immediate lookups."""
        with self._lock:
            self._local_ratings.add((span_id, user_id))

    def check_user_already_rated(self, span_id: str, user_id: str) -> bool:
        """True if user has already submitted inter-rater feedback for this span."""
        with self._lock:
            locally_rated = (span_id, user_id) in self._local_ratings
            annotations = list(self._by_span.get(span_id, []))
        if locally_rated:
            return True
        for ann in annotations:
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater") and metadata.get("rater_id") == user_id:
                return True
        return False

    def get_inter_rater_count(self, span_id: str) -> int:
        """Count of unique inter-rater users who have rated this span."""
        raters = self.get_inter_rater_raters(span_id)
        return len(raters)

    def get_inter_rater_raters(self, span_id: str) -> Set[str]:
        """Return unique inter-rater user IDs, including local pending writes."""
        with self._lock:
            annotations = list(self._by_span.get(span_id, []))
            local_raters = {
                user_id
                for local_span_id, user_id in self._local_ratings
                if local_span_id == span_id
            }

        raters: Set[str] = set(local_raters)
        for ann in annotations:
            metadata = ann.get("metadata", {})
            if metadata.get("is_inter_rater") and metadata.get("rater_id"):
                raters.add(metadata["rater_id"])
        return raters

    def get_user_inter_rater_count(
        self, user_id: str, span_ids: Optional[Set[str]] = None
    ) -> int:
        """
        Return distinct spans rated by one user.

        When span_ids is supplied, count only that study snapshot. Without the
        scope this remains the project-wide count used by ad-hoc inter-rating.
        """
        with self._lock:
            if span_ids is None:
                relevant_span_ids = set(self._by_span.keys())
                relevant_span_ids.update(
                    span_id
                    for span_id, local_user_id in self._local_ratings
                    if local_user_id == user_id
                )
            else:
                relevant_span_ids = set(span_ids)
        return sum(
            1 for span_id in relevant_span_ids
            if user_id in self.get_inter_rater_raters(span_id)
        )

    def get_user_inter_rater_rating(
        self, span_id: str, user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Return one reviewer's own recorded rating for a span, or None.

        Scores and the fault rationale carry `rater_id` in metadata, but fault
        tags, Additional Comments and the per-scale comments do not
        (backend/telemetry/feedback.py:657, 672, 690-715). They can only be
        joined to their author through the shared `[inter-rating-N]` name
        prefix, so that join is the disclosure risk for "own ratings only".

        A group is attributed only when exactly one `rater_id` appears in it.
        A group with no identity, or with colliding identities, is omitted
        rather than guessed at.
        """
        with self._lock:
            annotations = list(self._by_span.get(span_id, []))

        groups: Dict[str, List[tuple]] = defaultdict(list)
        for ann in annotations:
            parsed = _parse_inter_rater_name(ann.get("name", "") or "")
            if parsed is None:
                continue
            group_key, base_name = parsed
            groups[group_key].append((base_name, ann))

        for group_key, items in groups.items():
            raters = {
                ann.get("metadata", {}).get("rater_id")
                for _, ann in items
                if ann.get("metadata", {}).get("rater_id")
            }
            if len(raters) != 1:
                # Unattributable: no identity, or more than one rater in the
                # same group. Never fall back to guessing.
                if raters:
                    logger.warning(
                        "Ambiguous inter-rating group; omitting from history"
                    )
                continue
            if next(iter(raters)) != user_id:
                continue
            return self._build_rating(group_key, items)

        return None

    @staticmethod
    def _build_rating(group_key: str, items: List[tuple]) -> Dict[str, Any]:
        """Assemble one reviewer's scores, rationales and faults for a span."""
        rating: Dict[str, Any] = {
            "inter_rater_number": None if group_key == "unnumbered" else int(group_key),
            "scores": {},
            "rationales": {},
            "faults": [],
            "faults_rationale": None,
            "additional_comments": None,
            "timestamp": None,
        }

        for base_name, ann in items:
            result = ann.get("result", {}) or {}
            metadata = ann.get("metadata", {}) or {}

            if rating["timestamp"] is None and metadata.get("inter_rater_timestamp"):
                rating["timestamp"] = metadata["inter_rater_timestamp"]

            if base_name in _RUBRIC_SCORES:
                rating["scores"][_RUBRIC_SCORES[base_name]] = result.get("score")
            elif base_name in _RUBRIC_RATIONALES:
                rating["rationales"][_RUBRIC_RATIONALES[base_name]] = result.get(
                    "explanation"
                )
            elif base_name.startswith(_FAULT_PREFIX):
                rating["faults"].append(base_name[len(_FAULT_PREFIX):])
            elif base_name == "Fault Rationale":
                rating["faults_rationale"] = result.get("explanation")
            elif base_name == "Additional Comments":
                rating["additional_comments"] = result.get("explanation")

        return rating

    async def refresh_span(self, span_id: str) -> bool:
        """
        Refresh one span's annotations directly from Phoenix.

        Submission-time capacity checks use this method while holding a
        distributed per-span lock. The cached entry is replaced only after a
        complete successful response, so a Phoenix error cannot turn an
        unknown count into zero.
        """
        return await self.refresh_spans([span_id])

    async def refresh_spans(self, span_ids: List[str]) -> bool:
        """Refresh annotations for a set of spans, replacing cache entries atomically."""
        if not span_ids:
            return True

        url = f"{self._phoenix_endpoint}/v1/projects/{self.project_name}/span_annotations"
        headers = self._get_headers()
        annotations: List[Dict[str, Any]] = []
        requested_span_ids = set(span_ids)
        batches = [
            span_ids[index:index + _BATCH_SIZE]
            for index in range(0, len(span_ids), _BATCH_SIZE)
        ]

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                for batch in batches:
                    cursor = None
                    while True:
                        params: List[tuple] = [("span_ids", sid) for sid in batch]
                        params.append(("limit", "1000"))
                        if cursor:
                            params.append(("cursor", cursor))

                        response = await client.get(url, headers=headers, params=params)
                        if response.status_code != 200:
                            logger.error(
                                "Failed to refresh annotations: "
                                f"{response.status_code} {response.text[:200]}"
                            )
                            return False

                        body = response.json()
                        annotations.extend(body.get("data", []))
                        cursor = body.get("next_cursor")
                        if not cursor:
                            break

            with self._lock:
                for span_id in span_ids:
                    self._by_span[span_id] = []
                for annotation in annotations:
                    annotation_span_id = annotation.get("span_id")
                    if annotation_span_id in requested_span_ids:
                        self._by_span[annotation_span_id].append(annotation)
                self._known_span_ids.update(span_ids)
                self._last_refresh = time.time()
            return True
        except Exception as error:
            logger.error(
                "Failed to refresh annotations: "
                f"{type(error).__name__}"
            )
            return False

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
