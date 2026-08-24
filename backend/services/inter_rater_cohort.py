"""Shared cohort-slot assignment for balanced inter-rater study queues."""

import hashlib
import os


class InterRaterCohortRegistry:
    """Assign each authenticated reviewer one stable slot for a seeded pool."""

    _ASSIGN_SLOT = """
    local existing = redis.call('HGET', KEYS[1], ARGV[1])
    if existing then
        return tonumber(existing)
    end
    local next_slot = redis.call('INCR', KEYS[2]) - 1
    if next_slot >= tonumber(ARGV[2]) then
        redis.call('DECR', KEYS[2])
        return -1
    end
    redis.call('HSET', KEYS[1], ARGV[1], next_slot)
    return next_slot
    """

    async def get_slot(
        self,
        project_name: str,
        pool_span_ids: list[str],
        user_id: str,
        reviewer_count: int,
    ) -> int:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required for balanced inter-rater allocation")

        pool_fingerprint = hashlib.sha256(
            "\n".join(sorted(pool_span_ids)).encode("utf-8")
        ).hexdigest()
        cohort_fingerprint = hashlib.sha256(
            f"{project_name}:{pool_fingerprint}".encode("utf-8")
        ).hexdigest()
        users_key = f"atlas:inter-rater:cohort:{cohort_fingerprint}:users"
        next_key = f"atlas:inter-rater:cohort:{cohort_fingerprint}:next"

        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        try:
            slot = await client.eval(
                self._ASSIGN_SLOT,
                2,
                users_key,
                next_key,
                user_id,
                reviewer_count,
            )
        finally:
            await client.aclose()

        if slot < 0:
            raise ValueError("The configured inter-rater reviewer cohort is already full")
        return int(slot)


inter_rater_cohort_registry = InterRaterCohortRegistry()
