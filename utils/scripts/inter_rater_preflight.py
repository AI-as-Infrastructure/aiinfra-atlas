"""
Read-only pre-flight for an inter-rater study pool.

Answers the questions worth answering before reviewers arrive:
whether the design is saturated, which cohort slots are already taken, and
what each already-allocated reviewer would actually be served.

Reads Phoenix and Redis; writes nothing.

Usage:
    ENV_FILE=config/.env.production
    set -a; . "$ENV_FILE"; set +a
    .venv/bin/python utils/scripts/inter_rater_preflight.py
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.services.inter_rater_pool import inter_rater_pool  # noqa: E402
from backend.services.inter_rater_service import inter_rater_service  # noqa: E402


def cohort_keys(project: str, pool_fingerprint: str) -> tuple[str, str]:
    """Reproduce InterRaterCohortRegistry.get_slot's key derivation."""
    span_fp = hashlib.sha256(pool_fingerprint.encode("utf-8")).hexdigest()
    cohort_fp = hashlib.sha256(f"{project}:{span_fp}".encode("utf-8")).hexdigest()
    return (
        f"atlas:inter-rater:cohort:{cohort_fp}:users",
        f"atlas:inter-rater:cohort:{cohort_fp}:next",
    )


async def main() -> int:
    project = inter_rater_service.project_name
    reviewers = inter_rater_service.reviewer_count
    per_user = inter_rater_service.sessions_per_user
    max_ratings = inter_rater_service.max_ratings

    print(f"Project:           {project}")
    print(f"Design:            {reviewers} reviewers x {per_user} each, "
          f"max {max_ratings} ratings per prompt")

    manifest = inter_rater_pool.load()
    if manifest is None:
        print("\nNo study pool manifest — allocation would fall back to ad-hoc mode.")
        return 1
    qa_ids = manifest["qa_ids"]
    print(f"Manifest:          {len(qa_ids)} prompts, project '{manifest.get('project')}'")

    # 1. Is the design saturated? Balanced allocation is silently off if not.
    demand = reviewers * per_user
    capacity = len(qa_ids) * max_ratings
    print(f"\nCapacity:          {len(qa_ids)} x {max_ratings} = {capacity}")
    print(f"Demand:            {reviewers} x {per_user} = {demand}")
    if demand == capacity:
        print("                   BALANCED — even overlap, every prompt fully rated")
    else:
        print("                   *** NOT BALANCED — falls back to unbalanced ranking ***")

    # 2. How much of the pool actually has spans in Phoenix?
    sessions, pool_fp, _ = await inter_rater_service._get_pool(
        include_citations=False,
        publish_shared=False,
    )
    print(f"\nSpans in Phoenix:  {len(sessions)} of {len(qa_ids)} seeded prompts")
    if len(sessions) != len(qa_ids):
        print("                   *** pool incomplete — capacity is lower than it looks ***")

    # 3. Which cohort slots are already spent, and on whom?
    users_key, next_key = cohort_keys(project, pool_fp)
    import redis.asyncio as redis

    client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    try:
        assigned = await client.hgetall(users_key)
        taken = await client.get(next_key)
    finally:
        await client.aclose()

    print(f"\nCohort slots used: {taken or 0} of {reviewers}")
    for user_id, slot in sorted(assigned.items(), key=lambda kv: int(kv[1])):
        print(f"  slot {slot:>2}  {user_id}")
    if not assigned:
        print("  (none yet — first login takes slot 0)")

    # 4. What would each already-allocated reviewer actually be served?
    queues = {}
    for user_id in assigned:
        queues[user_id] = await inter_rater_service.get_sessions_for_inter_rating(
            user_id,
            publish_shared=False,
        )

    for user_id, queue in queues.items():
        first = ", ".join(s["span_id"][:8] for s in queue[:3])
        print(f"\n{user_id}: {len(queue)} prompts (expect {per_user})")
        print(f"  first three span_ids: {first}")

    ids = {u: {s["span_id"] for s in q} for u, q in queues.items()}
    users = sorted(ids)
    for i, a in enumerate(users):
        for b in users[i + 1:]:
            shared = len(ids[a] & ids[b])
            print(f"\nOverlap {a[:12]} / {b[:12]}: {shared} shared of {per_user}")
            if ids[a] == ids[b]:
                print("  *** identical queues — balanced allocation is not active ***")
            expected = len(sessions) * max_ratings * (max_ratings - 1) / (reviewers * (reviewers - 1))
            print(f"  expected ~{expected:.1f} for this design")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
