"""
Explicit study pool for inter-rater reliability runs.

`make seed` writes a manifest of the qa_ids it created. Restricting the
allocator to that manifest gives a pure seeded pool with three properties the
study depends on:

- Organic traffic in the same Phoenix project can never enter the pool, so the
  prompt set matches what reviewers were briefed on.
- The pool is identical for every reviewer. Derived from a live Phoenix query
  it is not: `query_spans_for_inter_rating` drops sessions the requesting user
  authored, so one reviewer's pool can differ in size from another's, which
  would place them in different cohorts and hand them the same queue.
- The cohort fingerprint is stable for the whole run, so reviewer slots are not
  reshuffled mid-study when a span is added, deleted, or slow to index.

Without a manifest the allocator falls back to every eligible span in the
project, which is the right behaviour for ad-hoc inter-rating outside a study.
"""

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MANIFEST_PATH = "data/seed_pool.json"


class InterRaterPool:
    """Loads the seeded study pool manifest, if one is configured."""

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_mtime: Optional[float] = None

    @property
    def manifest_path(self) -> str:
        return os.getenv("INTER_RATER_POOL_MANIFEST", DEFAULT_MANIFEST_PATH)

    def load(self) -> Optional[Dict[str, Any]]:
        """
        Return the manifest, or None when no study pool is configured.

        Re-reads on mtime change so a re-seed takes effect without a restart.
        """
        path = self.manifest_path
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            if self._cache is not None:
                logger.warning(f"Inter-rater pool manifest no longer readable at {path}")
            self._cache = None
            self._cache_mtime = None
            return None

        if self._cache is not None and self._cache_mtime == mtime:
            return self._cache

        with open(path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)

        qa_ids = manifest.get("qa_ids")
        if not isinstance(qa_ids, list) or not qa_ids:
            raise ValueError(f"Inter-rater pool manifest {path} has no qa_ids")
        if len(set(qa_ids)) != len(qa_ids):
            raise ValueError(f"Inter-rater pool manifest {path} contains duplicate qa_ids")

        self._cache = manifest
        self._cache_mtime = mtime
        logger.info(
            f"Loaded inter-rater study pool: {len(qa_ids)} prompts "
            f"for project '{manifest.get('project')}' from {path}"
        )
        return manifest

    def qa_ids(self) -> Optional[List[str]]:
        manifest = self.load()
        return list(manifest["qa_ids"]) if manifest else None

    def fingerprint(self) -> Optional[str]:
        """
        Stable identifier for the study pool, used as the cohort key.

        Derived from the manifest rather than from a Phoenix query result, so it
        does not move when spans are added, removed, or filtered per user.
        """
        manifest = self.load()
        if not manifest:
            return None
        payload = "\n".join(sorted(manifest["qa_ids"]))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def restrict(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Keep only sessions belonging to the study pool.

        Logs when the pool is incompletely seeded — a prompt in the manifest
        with no span in Phoenix silently shrinks capacity, so it must be
        visible before reviewers arrive.
        """
        pool_qa_ids = self.qa_ids()
        if pool_qa_ids is None:
            return sessions

        wanted = set(pool_qa_ids)
        in_pool = [session for session in sessions if session.get("qa_id") in wanted]

        missing = wanted - {session.get("qa_id") for session in in_pool}
        if missing:
            logger.warning(
                f"Study pool incomplete: {len(missing)} of {len(wanted)} seeded prompts "
                f"have no eligible span in Phoenix"
            )
        dropped = len(sessions) - len(in_pool)
        if dropped:
            logger.info(f"Study pool filter excluded {dropped} non-pool sessions")

        return in_pool


inter_rater_pool = InterRaterPool()
