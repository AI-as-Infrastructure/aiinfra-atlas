"""
Inter-rater reliability service for ATLAS.

This module provides functionality for managing inter-rater reliability sessions,
retrieving sessions for rating, and managing the inter-rater workflow.
"""

import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

class InterRaterService:
    """Service for managing inter-rater reliability functionality."""

    def __init__(self):
        self.enabled = os.getenv("INTER_RATER_ENABLED", "false").lower() == "true"
        self.project_name = os.getenv("INTER_RATER_PROJECT") or os.getenv("PHOENIX_PROJECT_NAME")
        self.max_ratings = self._positive_int_setting("INTER_RATER_MAX_RATINGS")
        self.reviewer_count = self._positive_int_setting("INTER_RATER_REVIEWERS")
        self.sessions_per_user = self._positive_int_setting("INTER_RATER_SESSIONS_PER_USER")
        self.default_ui = os.getenv("INTER_RATER_DEFAULT_UI", "false").lower() == "true"

        if self.enabled and not self.project_name:
            raise ValueError(
                "INTER_RATER_PROJECT or PHOENIX_PROJECT_NAME is required when inter-rating is enabled"
            )
        telemetry_project = os.getenv("PHOENIX_PROJECT_NAME")
        inter_rater_project = os.getenv("INTER_RATER_PROJECT")
        if self.enabled and telemetry_project and inter_rater_project:
            if telemetry_project != inter_rater_project:
                raise ValueError(
                    "INTER_RATER_PROJECT must exactly match PHOENIX_PROJECT_NAME"
                )
        if self.enabled and not os.getenv("REDIS_URL"):
            raise ValueError("REDIS_URL is required when inter-rating is enabled")

        # Focus-group mode without a study pool has no legitimate reading, and
        # it is the one remaining way to lose every study guarantee silently:
        # no pool purity, no capacity check, and the cohort key falls back to a
        # fingerprint over query results that moves whenever a span does. A
        # single organic session in the project would then switch balanced
        # allocation off and under-rate part of the pool. Ad-hoc inter-rating
        # runs with INTER_RATER_DEFAULT_UI=false and is unaffected.
        if self.enabled and self.default_ui:
            from .inter_rater_pool import MANIFEST_PATH_ENV, manifest_path

            if manifest_path() is None:
                raise ValueError(
                    f"{MANIFEST_PATH_ENV} is required when INTER_RATER_DEFAULT_UI=true. "
                    f"Focus-group mode runs a study, so the study pool must be explicit; "
                    f"without it the allocator falls back to project-wide ad-hoc rating "
                    f"and the pool, capacity and cohort guarantees do not apply."
                )

        # Study pool cache. Shared across users — the Phoenix span query is the
        # expensive part of an allocation and returns the same pool for everyone.
        self._pool_cache = {}
        self._pool_cache_timeout = 60  # 1 minute

        # Stats cache
        self._stats_cache = {}
        self._stats_cache_timeout = 300  # 5 minutes

    def _positive_int_setting(self, name: str) -> Optional[int]:
        """Read a positive integer setting without embedding study-design defaults."""
        raw_value = os.getenv(name)
        if raw_value is None:
            if self.enabled:
                raise ValueError(f"{name} is required when inter-rating is enabled")
            return None
        try:
            value = int(raw_value)
        except ValueError as error:
            raise ValueError(f"{name} must be a positive integer") from error
        if value <= 0:
            raise ValueError(f"{name} must be a positive integer")
        return value

    def is_enabled(self) -> bool:
        """Check if inter-rater functionality is enabled."""
        return self.enabled

    def _allocate_sessions_to_user(
        self,
        available_sessions: List[Dict[str, Any]],
        user_id: str,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Rank sessions for a user, prioritising under-rated sessions.

        Primary sort key: inter_rater_count ASC — sessions with fewer existing
        ratings surface first, so the pool fills bottom-up and every session
        is more likely to clear the ≥2-ratings floor before any session is
        saturated. Tie-breaker: SHA-256(span_id:user_id) — gives each user a
        deterministic, de-correlated ordering within a count bucket so two
        users at the same count don't dogpile the same session.

        The max_ratings cap is enforced upstream by the inter_rater_count
        pre-filter — once a session reaches max_ratings it drops out of
        available_sessions on the next allocation refresh.
        """
        if not available_sessions:
            return []

        scored = []
        for session in available_sessions:
            count = session.get('inter_rater_count', 0)
            pair = f"{session.get('span_id', '')}:{user_id}"
            h = hashlib.sha256(pair.encode()).hexdigest()
            tiebreak = int(h[:16], 16)
            scored.append(((count, tiebreak), session))

        scored.sort(key=lambda x: x[0])

        allocation_limit = self.sessions_per_user if limit is None else limit
        return [s for _, s in scored[:allocation_limit]]

    def _study_assignment(self, span_ids: List[str]) -> List[List[str]]:
        """
        Assign every prompt to exactly max_ratings reviewer slots.

        Each prompt is given to the slots with the most quota left, tie-broken
        by SHA-256(span_id:slot). Filling by remaining quota keeps every
        reviewer at exactly sessions_per_user, and the hash tiebreak spreads
        each reviewer's items across the whole pool so reviewer pairs overlap
        evenly — mean overlap converges on the theoretical
        pool*cap*(cap-1) / (reviewers*(reviewers-1)).

        Even overlap is what makes cohort-wide analysis possible: it keeps
        rater severity from being confounded with any block of prompts, and
        lets any reviewer be compared against the rest of the cohort rather
        than only against whoever shares their queue.

        Deterministic, so every worker derives the same assignment without
        coordination.
        """
        quota = [self.sessions_per_user] * self.reviewer_count
        queues: List[List[str]] = [[] for _ in range(self.reviewer_count)]

        for span_id in sorted(span_ids):
            eligible = [slot for slot in range(self.reviewer_count) if quota[slot] > 0]
            if len(eligible) < self.max_ratings:
                raise ValueError(
                    "Inter-rater study assignment exhausted reviewer quota; check "
                    "INTER_RATER_REVIEWERS, INTER_RATER_SESSIONS_PER_USER and "
                    "INTER_RATER_MAX_RATINGS against the study pool size"
                )
            eligible.sort(
                key=lambda slot: (
                    -quota[slot],
                    hashlib.sha256(f"{span_id}:{slot}".encode()).hexdigest(),
                )
            )
            for slot in eligible[: self.max_ratings]:
                queues[slot].append(span_id)
                quota[slot] -= 1

        return queues

    def _balanced_assignment(
        self,
        sessions: List[Dict[str, Any]],
        reviewer_slot: int,
    ) -> Optional[List[Dict[str, Any]]]:
        """Return a balanced queue when configured demand exactly matches capacity."""
        pool_size = len(sessions)
        if not pool_size:
            return []
        if self.reviewer_count * self.sessions_per_user != pool_size * self.max_ratings:
            return None
        if self.sessions_per_user > pool_size:
            raise ValueError("INTER_RATER_SESSIONS_PER_USER cannot exceed the study pool size")

        by_span_id = {session["span_id"]: session for session in sessions}
        assigned = self._study_assignment(list(by_span_id))[reviewer_slot]
        return [by_span_id[span_id] for span_id in assigned]

    @staticmethod
    def _allocation_snapshot_id(sessions: List[Dict[str, Any]]) -> str:
        """
        Identify the exact shared pool snapshot a client allocation came from.

        Distinct from the cohort fingerprint, which is derived from manifest
        qa_ids, is None in ad-hoc mode, and is deliberately stable when the
        Phoenix span set changes (inter_rater_pool.fingerprint). Those are the
        right properties for keeping reviewer slots stable and the wrong ones
        for deciding whether saved client state is still real.

        Hashed from the authoritative (span_id, qa_id) pairs before any
        per-reviewer author, rating or capacity filtering, so it exists in every
        mode, is identical for every reviewer, and does not move merely because
        ratings were submitted or a span reached its cap.
        """
        payload = "\n".join(
            sorted(
                f"{session.get('span_id', '')}:{session.get('qa_id', '')}"
                for session in sessions
            )
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    async def _get_pool(
        self, include_citations: bool, force_refresh: bool = False
    ) -> tuple[List[Dict[str, Any]], Optional[str], str]:
        """
        Return (study pool, cohort fingerprint, allocation snapshot id), cached
        briefly and shared across users.

        The Phoenix span query is the expensive part of an allocation and its
        result is the same for every reviewer, so it is cached rather than
        repeated per request. Caching is safe because the queue a reviewer sees
        no longer depends on live rating counts: cohort assignment is
        deterministic, and the authoritative cap check happens under a
        distributed lock in inter_rater_submission_gate at submission time. A
        count that goes stale within the TTL can only mean a reviewer is shown
        an item that has since filled, which the gate rejects and the dashboard
        replaces.
        """
        from .phoenix_client import phoenix_client
        from .inter_rater_pool import inter_rater_pool

        cache_key = f"pool_{self.project_name}_{include_citations}"
        cached = self._pool_cache.get(cache_key)
        if (
            not force_refresh
            and cached
            and (datetime.now().timestamp() - cached['timestamp']) < self._pool_cache_timeout
        ):
            return cached['sessions'], cached['fingerprint'], cached['snapshot_id']

        # Fetched without exclude_user_id so one pool serves every reviewer;
        # per-user exclusion is applied by the caller.
        sessions = await phoenix_client.query_spans_for_inter_rating(
            exclude_user_id=None,
            limit=self.sessions_per_user * 10,
            include_citations=include_citations,
            keep_author_id=True,
        )
        # Restriction and fingerprinting deliberately share one manifest
        # snapshot. Calling restrict() and fingerprint() separately leaves a
        # re-seed race between the two reads even if the resulting values are
        # subsequently cached together.
        sessions, fingerprint = inter_rater_pool.restrict_with_fingerprint(sessions)
        self._validate_study_capacity(sessions, fingerprint)

        snapshot_id = self._allocation_snapshot_id(sessions)
        self._pool_cache[cache_key] = {
            'sessions': sessions,
            'fingerprint': fingerprint,
            'snapshot_id': snapshot_id,
            'timestamp': datetime.now().timestamp(),
        }
        try:
            from .inter_rater_pool_snapshot import inter_rater_pool_snapshot_registry

            await inter_rater_pool_snapshot_registry.publish(
                self.project_name,
                snapshot_id,
                [session["span_id"] for session in sessions if session.get("span_id")],
            )
        except Exception as error:
            logger.warning(
                "Could not publish shared inter-rater pool snapshot: "
                f"{type(error).__name__}"
            )
        return sessions, fingerprint, snapshot_id

    def _validate_study_capacity(self, sessions: List[Dict[str, Any]], fingerprint: Optional[str]) -> None:
        """
        Refuse to run a study whose pool no longer matches the configuration.

        Balanced allocation is active only while
        reviewers x sessions_per_user == pool x max_ratings. If the pool has
        shrunk — prompts that failed to seed, a deleted span, a partially
        written manifest — allocation would quietly fall back to unbalanced
        ranking and under-rate part of the pool. That is invisible until the
        data is analysed and the session cannot be repeated, so it fails here
        instead. Only enforced in study mode: without a manifest, ad-hoc
        inter-rating is expected to use whatever is in the project.
        """
        if fingerprint is None:
            # A configured pool must never fall through to ad-hoc rating. The
            # manifest can define a study even when the normal chat UI remains
            # available, so data integrity cannot depend on default_ui. Only an
            # explicitly unset path in non-focus-group mode means ad-hoc use.
            #
            # Checked here rather than at startup on purpose: the manifest is
            # written by `make seed`, which POSTs to the running backend, so
            # requiring a loadable manifest to boot would deadlock a first-time
            # study (no manifest -> no boot -> no seeding -> no manifest). The
            # backend starts, seeding works, and only inter-rating itself
            # refuses until the pool exists.
            from .inter_rater_pool import MANIFEST_PATH_ENV, manifest_path

            configured_path = manifest_path()
            if self.default_ui or configured_path is not None:
                raise ValueError(
                    f"Inter-rating requires the configured study pool manifest to be "
                    f"readable, but none loaded from "
                    f"{MANIFEST_PATH_ENV}={configured_path!r}. Run `make seed` to create "
                    f"it, restore the file, or unset {MANIFEST_PATH_ENV} for deliberate "
                    f"project-wide ad-hoc rating when INTER_RATER_DEFAULT_UI=false."
                )
            return

        demand = self.reviewer_count * self.sessions_per_user
        capacity = len(sessions) * self.max_ratings
        if demand == capacity:
            return

        raise ValueError(
            f"Inter-rater study pool does not match the configured design: "
            f"{len(sessions)} prompts x INTER_RATER_MAX_RATINGS={self.max_ratings} "
            f"= {capacity} ratings, but INTER_RATER_REVIEWERS={self.reviewer_count} "
            f"x INTER_RATER_SESSIONS_PER_USER={self.sessions_per_user} = {demand}. "
            f"Re-seed the missing prompts, or align the settings with the pool "
            f"(pool must be demand / max_ratings = {demand / self.max_ratings:g} prompts)."
        )

    async def get_allocation_snapshot_id(self, include_citations: bool = True) -> str:
        """
        Snapshot id for the current shared pool. Served from the pool cache, so
        calling this after get_sessions_for_inter_rating costs no extra query.
        """
        _, _, snapshot_id = await self._get_pool(include_citations)
        return snapshot_id

    async def span_ids_in_current_pool(self) -> set:
        """
        Authoritative span ids from the pool snapshot shared by every worker.

        Raises rather than returning an empty set when the pool cannot be
        established, so callers can fail closed instead of treating an
        unverifiable pool as "not a member".
        """
        from .inter_rater_pool_snapshot import inter_rater_pool_snapshot_registry

        shared = await inter_rater_pool_snapshot_registry.get(self.project_name)
        if shared is not None:
            return set(shared["span_ids"])

        async with inter_rater_pool_snapshot_registry.refresh_lock(self.project_name):
            shared = await inter_rater_pool_snapshot_registry.get(self.project_name)
            if shared is not None:
                return set(shared["span_ids"])

            pool_sessions, _, snapshot_id = await self._get_pool(
                include_citations=False,
                force_refresh=True,
            )
            span_ids = [
                session["span_id"]
                for session in pool_sessions
                if session.get("span_id")
            ]
            await inter_rater_pool_snapshot_registry.publish(
                self.project_name, snapshot_id, span_ids
            )
            return set(span_ids)

    async def get_sessions_for_inter_rating(self, user_id: str, include_citations: bool = True) -> List[Dict[str, Any]]:
        """
        Get sessions available for inter-rating by a specific user.

        Span data and current annotations are refreshed from Phoenix before
        eligibility, quota, and allocation rules are applied.

        Args:
            include_citations: If False, skip REFERENCES span query (faster for counts).
        """
        if not self.enabled:
            return []

        try:
            from .annotations_cache import annotations_cache
            sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
            logger.info(f"Building inter-rater allocation for user {sanitized_user_id}")

            pool_sessions, pool_fingerprint, snapshot_id = await self._get_pool(include_citations)

            # Exclude sessions this user authored. Applied locally so the pool
            # stays identical for every reviewer and can be shared from cache;
            # seeded sessions have no author and always pass through.
            all_sessions = [
                session for session in pool_sessions
                if not session.get("original_user_id")
                or session.get("original_user_id") != user_id
            ]

            # For an exactly saturated design, assign each reviewer a shared
            # Redis cohort slot and derive a balanced queue before filtering.
            balanced_design = (
                self.reviewer_count * self.sessions_per_user
                == len(all_sessions) * self.max_ratings
            )
            assigned_sessions = None
            if balanced_design:
                from .inter_rater_cohort import inter_rater_cohort_registry

                # Prefer the manifest fingerprint: it is stable for the whole
                # run, where a fingerprint over query results moves whenever a
                # span is added, removed, or filtered.
                cohort_key = pool_fingerprint or "\n".join(
                    sorted(session["span_id"] for session in all_sessions)
                )
                reviewer_slot = await inter_rater_cohort_registry.get_slot(
                    self.project_name,
                    [cohort_key],
                    user_id,
                    self.reviewer_count,
                )
                assigned_sessions = self._balanced_assignment(all_sessions, reviewer_slot)
            candidate_sessions = assigned_sessions if assigned_sessions is not None else all_sessions

            # Filter: user hasn't already rated, and span hasn't reached max ratings
            # All lookups are local dict reads from the annotations cache
            available_sessions = []
            for session in candidate_sessions:
                span_id = session['span_id']

                already_rated = annotations_cache.check_user_already_rated(span_id, user_id)
                if already_rated:
                    continue

                inter_rater_count = annotations_cache.get_inter_rater_count(span_id)
                if inter_rater_count >= self.max_ratings:
                    continue

                # Copy before mutating: these dicts belong to the shared pool
                # cache. Drop original_user_id — it is used only for the local
                # self-authored filter above and must not reach the frontend.
                candidate = {k: v for k, v in session.items() if k != 'original_user_id'}
                candidate['inter_rater_count'] = inter_rater_count
                available_sessions.append(candidate)

            # Enforce the per-user quota across reloads and browser sessions.
            # In study mode quota belongs to this manifest, not to every
            # inter-rating the user has ever submitted in the Phoenix project.
            # This is essential when a new manifest intentionally starts a new
            # cohort without deleting the old project.
            study_span_ids = (
                {session["span_id"] for session in all_sessions}
                if pool_fingerprint is not None
                else None
            )
            completed_sessions = annotations_cache.get_user_inter_rater_count(
                user_id, study_span_ids
            )
            remaining_slots = max(self.sessions_per_user - completed_sessions, 0)

            # Allocate sessions to this specific user
            if assigned_sessions is not None:
                final_sessions = available_sessions[:remaining_slots]
            else:
                final_sessions = self._allocate_sessions_to_user(
                    available_sessions,
                    user_id,
                    limit=remaining_slots,
                )

            logger.info(f"Found {len(final_sessions)} available sessions for user {sanitized_user_id}")
            return final_sessions

        except ValueError as e:
            logger.error(f"Phoenix data error for inter-rating: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error retrieving sessions for inter-rating: {e}")
            raise ValueError(f"Failed to retrieve inter-rater sessions: {str(e)}")

    async def get_inter_rater_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics about inter-rater sessions for a user."""
        if not self.enabled:
            return {"enabled": False}

        # Check stats cache first
        stats_cache_key = f"stats_{user_id}"
        if stats_cache_key in self._stats_cache:
            cache_entry = self._stats_cache[stats_cache_key]
            cache_time = cache_entry.get('timestamp', 0)
            current_time = datetime.now().timestamp()
            if (current_time - cache_time) < self._stats_cache_timeout:
                sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
                logger.debug(f"Returning cached stats for user {sanitized_user_id}")
                return cache_entry['stats']

        try:
            available_sessions = await self.get_sessions_for_inter_rating(user_id, include_citations=False)

            stats = {
                "enabled": True,
                "available_sessions": len(available_sessions),
                "completed_sessions": await self.get_completed_sessions_for_inter_rating(
                    user_id, include_citations=False
                ),
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name,
                "default_ui": self.default_ui
            }

            self._stats_cache[stats_cache_key] = {
                'stats': stats,
                'timestamp': datetime.now().timestamp()
            }

            return stats

        except Exception as e:
            logger.error(f"Error getting inter-rater stats: {e}")
            error_stats = {
                "enabled": True,
                "available_sessions": 0,
                "completed_sessions": 0,
                "max_sessions_per_user": self.sessions_per_user,
                "project_name": self.project_name,
                "default_ui": self.default_ui,
                "error": "Failed to retrieve inter-rater stats"
            }

            self._stats_cache[stats_cache_key] = {
                'stats': error_stats,
                'timestamp': datetime.now().timestamp()
            }

            return error_stats

    async def get_completed_sessions_for_inter_rating(
        self, user_id: str, include_citations: bool = True
    ) -> int:
        """Count completed work against the active pool used by allocation."""
        pool_sessions, pool_fingerprint, _ = await self._get_pool(include_citations)
        if pool_fingerprint is None:
            return self.get_completed_sessions(user_id)

        study_span_ids = {
            session["span_id"]
            for session in pool_sessions
            if not session.get("original_user_id")
            or session.get("original_user_id") != user_id
        }
        return self.get_completed_sessions(user_id, study_span_ids)

    def get_completed_sessions(
        self, user_id: str, span_ids: Optional[set[str]] = None
    ) -> int:
        """Return distinct rated spans, optionally scoped to the active study."""
        from .annotations_cache import annotations_cache

        return annotations_cache.get_user_inter_rater_count(user_id, span_ids)

    def invalidate_user_cache(self, user_id: str):
        """
        Invalidate caches after a user submits inter-rater feedback.

        Clears the submitting user's stats cache. Session retrieval
        refreshes annotation counts from Phoenix, while submission uses a
        distributed per-span lock to enforce max_ratings across workers.
        """
        stats_key = f"stats_{user_id}"
        self._stats_cache.pop(stats_key, None)

        sanitized_user_id = user_id[:8] + "..." if len(user_id) > 8 else user_id
        logger.info(f"Invalidated cache for user {sanitized_user_id} after feedback submission")

    def clear_all_cache(self):
        """Clear cached inter-rater statistics."""
        self._stats_cache.clear()
        logger.info("Cleared inter-rater stats cache")

# Global instance
inter_rater_service = InterRaterService()
