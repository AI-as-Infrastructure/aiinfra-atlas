"""Atomic submission guard for inter-rater feedback."""

import hashlib
import logging
import os
from contextlib import asynccontextmanager
from enum import Enum
from typing import AsyncIterator, Dict, Any

logger = logging.getLogger(__name__)


class SubmissionStatus(str, Enum):
    """
    Outcome of an inter-rater submission attempt.

    The refusals are distinct because the client cannot tell them apart
    otherwise: "you already rated this" and "someone else filled it" are
    different facts for the reviewer, and collapsing them reported a reviewer's
    own duplicate as a concurrency loss (#72).
    """

    SUCCESS = "success"
    ALREADY_RATED = "already_rated"
    AT_CAPACITY = "at_capacity"
    OUT_OF_POOL = "out_of_pool"
    ERROR = "error"


class InterRaterSubmissionGate:
    """
    Serialize count-and-write operations for each span across all workers.

    Phoenix does not expose an atomic conditional annotation write. Redis is
    therefore used only as a distributed mutex; Phoenix remains the source of
    truth and is refreshed while the mutex is held. Production and staging
    deployments already require Redis.
    """

    LOCK_TIMEOUT_SECONDS = 120
    LOCK_WAIT_SECONDS = 15

    def _lock_key(self, project_name: str, span_id: str) -> str:
        value = f"{project_name}:{span_id}".encode("utf-8")
        digest = hashlib.sha256(value).hexdigest()
        return f"atlas:inter-rater:submission:{digest}"

    @asynccontextmanager
    async def _span_lock(self, project_name: str, span_id: str) -> AsyncIterator[None]:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required for atomic inter-rater submissions")

        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        lock = client.lock(
            self._lock_key(project_name, span_id),
            timeout=self.LOCK_TIMEOUT_SECONDS,
            blocking_timeout=self.LOCK_WAIT_SECONDS,
        )
        acquired = False
        try:
            acquired = await lock.acquire()
            if not acquired:
                raise RuntimeError("Timed out waiting for the inter-rater submission lock")
            yield
        finally:
            if acquired:
                try:
                    await lock.release()
                except Exception as error:
                    logger.warning(
                        "Failed to release inter-rater submission lock: "
                        f"{type(error).__name__}"
                    )
            await client.aclose()

    async def submit(
        self,
        span_id: str,
        user_id: str,
        feedback_data: Dict[str, Any],
        qa_id: str,
        max_ratings: int,
    ) -> SubmissionStatus:
        """Check current Phoenix state and write one annotation atomically per span."""
        from backend.services.annotations_cache import annotations_cache

        try:
            async with self._span_lock(annotations_cache.project_name, span_id):
                # Pool membership first: a span rehydrated from stale client
                # state must not be rated just because it still has capacity.
                # Never trust a client-supplied qa_id or snapshot id for this.
                try:
                    from backend.services.inter_rater_service import inter_rater_service

                    pool_span_ids = await inter_rater_service.span_ids_in_current_pool()
                except Exception as error:
                    logger.error(
                        "Cannot establish current pool; submission not attempted: "
                        f"{type(error).__name__}"
                    )
                    return SubmissionStatus.ERROR

                if span_id not in pool_span_ids:
                    logger.info("Inter-rater submission rejected: span not in current pool")
                    return SubmissionStatus.OUT_OF_POOL

                refreshed = await annotations_cache.refresh_span(span_id)
                if not refreshed:
                    logger.error("Cannot verify inter-rater capacity; submission not attempted")
                    return SubmissionStatus.ERROR

                if annotations_cache.check_user_already_rated(span_id, user_id):
                    logger.info("Inter-rater submission rejected: user already rated span")
                    return SubmissionStatus.ALREADY_RATED

                existing = annotations_cache.get_inter_rater_count(span_id)
                if existing >= max_ratings:
                    logger.info(
                        "Inter-rater submission rejected: span at max_ratings "
                        f"({existing}/{max_ratings})"
                    )
                    return SubmissionStatus.AT_CAPACITY

                success = await self._submit_annotation(span_id, feedback_data, qa_id)
                if not success:
                    return SubmissionStatus.ERROR

                annotations_cache.record_user_rating(span_id, user_id)
                return SubmissionStatus.SUCCESS
        except Exception as error:
            logger.error(
                "Inter-rater submission guard failed; submission not attempted: "
                f"{type(error).__name__}"
            )
            return SubmissionStatus.ERROR

    async def _submit_annotation(
        self,
        span_id: str,
        feedback_data: Dict[str, Any],
        qa_id: str,
    ) -> bool:
        """Write annotations after capacity has been reserved by the span lock."""
        from backend.telemetry.feedback import submit_span_annotation

        return await submit_span_annotation(span_id, feedback_data, qa_id)


inter_rater_submission_gate = InterRaterSubmissionGate()
