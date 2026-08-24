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
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MANIFEST_PATH_ENV = "INTER_RATER_POOL_MANIFEST"


def manifest_path() -> Optional[str]:
    """
    Return the configured manifest location, or None for ad-hoc mode.

    Imported by the seed and reset scripts so the writer, the remover and the
    reader can never disagree about which file is the study pool. There is no
    code default: a filesystem path is environment-specific and must live in
    the selected environment file.
    """
    value = os.getenv(MANIFEST_PATH_ENV)
    return value.strip() if value and value.strip() else None


def require_manifest_path() -> str:
    """Return the configured path or fail a study-management command loudly."""
    path = manifest_path()
    if path is None:
        raise ValueError(
            f"{MANIFEST_PATH_ENV} must be set in the selected environment file"
        )
    return path


def active_project() -> Optional[str]:
    return os.getenv("INTER_RATER_PROJECT") or os.getenv("PHOENIX_PROJECT_NAME")


class InterRaterPool:
    """Loads the seeded study pool manifest, if one is configured."""

    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_mtime_ns: Optional[int] = None

    @property
    def manifest_path(self) -> Optional[str]:
        return manifest_path()

    def load(self) -> Optional[Dict[str, Any]]:
        """
        Return the manifest, or None when no study pool is configured.

        Re-reads on mtime change so a re-seed takes effect without a restart.
        """
        path = self.manifest_path
        if path is None:
            self._cache = None
            self._cache_mtime_ns = None
            return None

        try:
            mtime_ns = os.stat(path).st_mtime_ns
        except OSError:
            if self._cache is not None:
                logger.warning(f"Inter-rater pool manifest no longer readable at {path}")
            self._cache = None
            self._cache_mtime_ns = None
            return None

        if self._cache is not None and self._cache_mtime_ns == mtime_ns:
            return self._cache

        with open(path, "r", encoding="utf-8") as handle:
            manifest = json.load(handle)
            # Cache the timestamp of the inode we actually read. If an atomic
            # replacement occurred after os.stat(), the next load sees the new
            # path timestamp and refreshes rather than pinning new data to an
            # old timestamp (or vice versa).
            loaded_mtime_ns = os.fstat(handle.fileno()).st_mtime_ns

        qa_ids = manifest.get("qa_ids")
        if not isinstance(qa_ids, list) or not qa_ids:
            raise ValueError(f"Inter-rater pool manifest {path} has no qa_ids")
        if len(set(qa_ids)) != len(qa_ids):
            raise ValueError(f"Inter-rater pool manifest {path} contains duplicate qa_ids")

        # A manifest from another environment names qa_ids that do not exist
        # here, which would empty the pool rather than fail visibly.
        manifest_project = manifest.get("project")
        current_project = active_project()
        if manifest_project and current_project and manifest_project != current_project:
            raise ValueError(
                f"Inter-rater pool manifest {path} was seeded for project "
                f"'{manifest_project}' but the active project is '{current_project}'. "
                f"Re-seed for this project, or point INTER_RATER_POOL_MANIFEST at the "
                f"manifest belonging to it."
            )

        self._cache = manifest
        self._cache_mtime_ns = loaded_mtime_ns
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
        return self._fingerprint(manifest)

    @staticmethod
    def _fingerprint(manifest: Dict[str, Any]) -> str:
        payload = "\n".join(sorted(manifest["qa_ids"]))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def restrict_with_fingerprint(
        self, sessions: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Filter sessions and fingerprint the exact same manifest snapshot."""
        manifest = self.load()
        if manifest is None:
            return sessions, None

        in_pool = self._restrict(sessions, manifest["qa_ids"])
        return in_pool, self._fingerprint(manifest)

    def restrict(self, sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Keep only sessions belonging to the study pool.

        Logs when the pool is incompletely seeded — a prompt in the manifest
        with no span in Phoenix silently shrinks capacity, so it must be
        visible before reviewers arrive.
        """
        manifest = self.load()
        if manifest is None:
            return sessions

        return self._restrict(sessions, manifest["qa_ids"])

    def _restrict(
        self, sessions: List[Dict[str, Any]], pool_qa_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Apply one already-loaded manifest snapshot to a Phoenix result."""
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
