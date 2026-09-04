"""Shared current-pool snapshot for inter-rater submission validation."""

import hashlib
import json
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Optional


class InterRaterPoolSnapshotRegistry:
    """Share one short-lived pool snapshot across all Gunicorn workers."""

    TTL_SECONDS = 60
    LOCK_TIMEOUT_SECONDS = 120
    LOCK_WAIT_SECONDS = 60

    def _key(self, project_name: str) -> str:
        digest = hashlib.sha256(project_name.encode("utf-8")).hexdigest()
        return f"atlas:inter-rater:pool:{digest}"

    def _lock_key(self, project_name: str) -> str:
        return f"{self._key(project_name)}:refresh"

    async def get(self, project_name: str) -> Optional[Dict[str, object]]:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required for inter-rater pool validation")

        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        try:
            raw = await client.get(self._key(project_name))
        finally:
            await client.aclose()

        if not raw:
            return None

        payload = json.loads(raw)
        snapshot_id = payload.get("snapshot_id")
        span_ids = payload.get("span_ids")
        if not isinstance(snapshot_id, str) or not isinstance(span_ids, list):
            return None
        if not all(isinstance(span_id, str) for span_id in span_ids):
            return None
        return {"snapshot_id": snapshot_id, "span_ids": span_ids}

    async def publish(
        self, project_name: str, snapshot_id: str, span_ids: list[str]
    ) -> None:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required for inter-rater pool validation")

        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        try:
            await client.set(
                self._key(project_name),
                json.dumps({"snapshot_id": snapshot_id, "span_ids": span_ids}),
                ex=self.TTL_SECONDS,
            )
        finally:
            await client.aclose()

    @asynccontextmanager
    async def refresh_lock(self, project_name: str) -> AsyncIterator[None]:
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            raise RuntimeError("REDIS_URL is required for inter-rater pool validation")

        import redis.asyncio as redis

        client = redis.from_url(redis_url, decode_responses=True)
        lock = client.lock(
            self._lock_key(project_name),
            timeout=self.LOCK_TIMEOUT_SECONDS,
            blocking_timeout=self.LOCK_WAIT_SECONDS,
        )
        acquired = False
        try:
            acquired = await lock.acquire()
            if not acquired:
                raise RuntimeError("Timed out waiting for the inter-rater pool refresh lock")
            yield
        finally:
            if acquired:
                await lock.release()
            await client.aclose()


inter_rater_pool_snapshot_registry = InterRaterPoolSnapshotRegistry()
