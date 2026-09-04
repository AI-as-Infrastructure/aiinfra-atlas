"""
Read-only check that recorded annotations match what the history reader expects.

The rating-history reader joins a reviewer's annotations by their
`[inter-rating-N]` name prefix, because fault tags, Additional Comments and the
per-scale comments carry no `rater_id` of their own. Two things can therefore
fail silently:

  * a name shape or base name the extractor does not recognise — history simply
    omits it, with no error;
  * a rating group carrying no rater identity, or more than one, which the
    extractor refuses to attribute rather than guess at.

Neither is visible from reading code, so this checks them against the project's
real annotations. It imports the extractor's own parser and name maps, so it
cannot drift from the implementation it is verifying.

Prints names, shapes and counts only — never rationale text, and never a
rater id.

Reads Phoenix; writes nothing. Exits non-zero if anything would be dropped.

Usage:
    ENV_FILE=config/.env.production
    set -a; . "$ENV_FILE"; set +a
    .venv/bin/python utils/scripts/inter_rater_annotation_check.py
"""

from __future__ import annotations

import collections
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx  # noqa: E402

from backend.services.annotations_cache import (  # noqa: E402
    _FAULT_PREFIX,
    _RUBRIC_RATIONALES,
    _RUBRIC_SCORES,
    _parse_inter_rater_name,
)

SPAN_LIMIT = 2000
BATCH = 100
TIMEOUT = 120  # Phoenix's own default is 5s, which this query outruns.

# Base names _build_rating knows what to do with.
KNOWN_EXACT = set(_RUBRIC_SCORES) | set(_RUBRIC_RATIONALES) | {
    "Fault Rationale",
    "Additional Comments",
}


def recognised(base_name: str) -> bool:
    return base_name in KNOWN_EXACT or base_name.startswith(_FAULT_PREFIX)


def iter_annotations(http, url: str, headers: dict, span_ids: list[str]):
    for start in range(0, len(span_ids), BATCH):
        batch = span_ids[start:start + BATCH]
        cursor = None
        while True:
            params = [("span_ids", span_id) for span_id in batch]
            params.append(("limit", "1000"))
            if cursor:
                params.append(("cursor", cursor))
            response = http.get(url, params=params, headers=headers)
            response.raise_for_status()
            body = response.json()
            yield from body.get("data", [])
            cursor = body.get("next_cursor")
            if not cursor:
                break


def main() -> int:
    project = os.getenv("INTER_RATER_PROJECT") or os.getenv("PHOENIX_PROJECT_NAME")
    endpoint = (os.getenv("PHOENIX_COLLECTOR_ENDPOINT") or "").rstrip("/")
    api_key = os.getenv("PHOENIX_API_KEY")

    if not (project and endpoint and api_key):
        print("Set INTER_RATER_PROJECT/PHOENIX_PROJECT_NAME, "
              "PHOENIX_COLLECTOR_ENDPOINT and PHOENIX_API_KEY first.")
        return 2

    from phoenix import Client

    client = Client(endpoint=endpoint, headers={"Authorization": f"Bearer {api_key}"})
    frame = client.get_spans_dataframe(
        project_name=project, limit=SPAN_LIMIT, timeout=TIMEOUT
    )
    span_ids = [s for s in frame.get("context.span_id", []) if s]

    # A span id means nothing to a tester. Carry the question so a rated prompt
    # can be quoted to someone, which is what arranging multi-rater cover needs.
    question_columns = [c for c in frame.columns if c.endswith("input.value")]
    questions: dict = {}
    if question_columns:
        for _, row in frame.iterrows():
            span_id = row.get("context.span_id")
            if span_id:
                questions[span_id] = " ".join(str(row.get(question_columns[0]) or "").split())
    print(f"project: {project}")
    print(f"spans scanned: {len(span_ids)}")
    if not span_ids:
        print("No spans — nothing to check.")
        return 0

    shapes: collections.Counter = collections.Counter()
    bases: collections.Counter = collections.Counter()
    unknown: collections.Counter = collections.Counter()
    # span -> group -> set of rater ids (held only to count them)
    groups: dict = collections.defaultdict(lambda: collections.defaultdict(set))
    # span -> most recent rating timestamp, for "show me the latest ratings"
    latest: dict = {}

    headers = {"Authorization": f"Bearer {api_key}"}
    url = f"{endpoint}/v1/projects/{project}/span_annotations"
    with httpx.Client(timeout=60.0) as http:
        for ann in iter_annotations(http, url, headers, span_ids):
            name = ann.get("name", "") or ""
            parsed = _parse_inter_rater_name(name)
            if parsed is None:
                shapes["not inter-rater prefixed"] += 1
                continue

            group_key, base_name = parsed
            shapes["unnumbered [Inter-rater] prefix" if group_key == "unnumbered"
                   else "[inter-rating-N] prefix"] += 1
            bases[base_name] += 1
            if not recognised(base_name):
                unknown[base_name] += 1

            metadata = ann.get("metadata") or {}
            span_id = ann.get("span_id")
            rater_id = metadata.get("rater_id")
            bucket = groups[span_id][group_key]
            if rater_id:
                bucket.add(rater_id)

            stamp = metadata.get("inter_rater_timestamp")
            if stamp and stamp > latest.get(span_id, ""):
                latest[span_id] = stamp

    print("\nname shapes")
    for shape, count in shapes.most_common():
        print(f"  {count:6d}  {shape}")

    print("\ninter-rater base names")
    for base, count in bases.most_common():
        mark = " " if recognised(base) else "  <-- NOT RECOGNISED"
        print(f"  {count:6d}  {base!r}{mark}")

    attributable = unidentified = colliding = 0
    multi_group_spans = 0
    for span_groups in groups.values():
        if len(span_groups) > 1:
            multi_group_spans += 1
        for raters in span_groups.values():
            if len(raters) == 1:
                attributable += 1
            elif not raters:
                unidentified += 1
            else:
                colliding += 1

    print("\ngroup attribution")
    print(f"  spans carrying inter-ratings : {len(groups)}")
    print(f"  spans with >1 rating group   : {multi_group_spans}")
    print(f"  attributable (exactly 1 rater): {attributable}")
    print(f"  no rater identity             : {unidentified}   -> omitted from history")
    print(f"  colliding rater identities    : {colliding}   -> omitted from history")

    if groups:
        print("\nrated spans, most recently rated first")
        print("  (paste a span id into the Phoenix span search to open it)")
        ordered = sorted(
            groups, key=lambda s: latest.get(s, ""), reverse=True
        )
        for span_id in ordered:
            when = (latest.get(span_id) or "unknown")[:19]
            print(f"  {when}  {span_id}  ({len(groups[span_id])} rating(s))")
            question = questions.get(span_id, "")
            if question:
                if len(question) > 88:
                    question = question[:85] + "..."
                print(f"      {question}")

    problems = []
    if unknown:
        problems.append(f"{sum(unknown.values())} annotations with unrecognised base names")
    if unidentified:
        problems.append(f"{unidentified} rating groups with no rater identity")
    if colliding:
        problems.append(f"{colliding} rating groups with colliding rater identities")

    if problems:
        print("\nFAIL — history would silently omit data:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nOK — every inter-rater annotation is recognised and attributable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
