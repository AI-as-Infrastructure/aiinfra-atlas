"""
Seed inter-rater sessions by running questions through the live RAG pipeline.

Usage:
    .venv/bin/python utils/scripts/seed_questions.py [--file PATH] [--count N] [--dry-run]
                                                     [--api URL] [--no-verify]

Reads questions from a JSON file and POSTs each to /api/ask/stream on the
configured server (default localhost:8000). The pipeline emits both the LLM
span and the com.atlas.rag.references span; once the SSE stream completes,
the resulting session is eligible for inter-rating (no baseline feedback).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import requests

DEFAULT_FILE = Path("data/seed_questions.json")
DEFAULT_API = "http://localhost:8000"
DEFAULT_MAX_RATINGS = 1  # matches .env.development; overridden by INTER_RATER_MAX_RATINGS
SSE_TIMEOUT_SECS = 300


@dataclass
class SeedResult:
    index: int
    question: str
    corpus_filter: str
    qa_id: str
    session_id: str
    saw_chunk: bool = False
    saw_references: bool = False
    saw_complete: bool = False
    error: Optional[str] = None
    elapsed_secs: float = 0.0

    @property
    def ok(self) -> bool:
        return self.saw_chunk and self.saw_references and self.saw_complete and self.error is None


@dataclass
class RunStats:
    total: int = 0
    succeeded: int = 0
    failed: List[SeedResult] = field(default_factory=list)


def load_questions(path: Path) -> List[dict]:
    if not path.exists():
        raise SystemExit(f"Seed file not found: {path}")
    with path.open() as f:
        data = json.load(f)
    questions = data.get("questions") if isinstance(data, dict) else data
    if not isinstance(questions, list) or not questions:
        raise SystemExit(f"No questions found in {path}")
    for i, q in enumerate(questions):
        if "question" not in q or "corpus_filter" not in q:
            raise SystemExit(f"Question {i} missing 'question' or 'corpus_filter': {q}")
    return questions


def print_sizing_check(n: int) -> int:
    max_ratings = int(os.getenv("INTER_RATER_MAX_RATINGS", DEFAULT_MAX_RATINGS))
    capacity = n * max_ratings
    print(f"Seed pool: {n} questions × INTER_RATER_MAX_RATINGS={max_ratings} → up to {capacity} total ratings")
    print(f"  Focus group target: 15 raters × 20 ratings = 300 rating slots")
    if capacity < 300:
        print(f"  WARNING: capacity ({capacity}) is below the 300-slot focus group target")
    return max_ratings


def post_and_drain(api_base: str, q: dict, index: int) -> SeedResult:
    qa_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    result = SeedResult(
        index=index,
        question=q["question"],
        corpus_filter=q["corpus_filter"],
        qa_id=qa_id,
        session_id=session_id,
    )

    payload = {
        "question": q["question"],
        "session_id": session_id,
        "qa_id": qa_id,
        "chat_history": [{"role": "user", "content": q["question"]}],
        "filters": {"corpus_filtering": q["corpus_filter"]},
        "previous_filters": {},
    }

    started = time.monotonic()
    try:
        with requests.post(
            f"{api_base}/api/ask/stream",
            json=payload,
            stream=True,
            timeout=SSE_TIMEOUT_SECS,
            headers={
                "Accept": "text/event-stream",
                "X-Telemetry-Opt-In": "true",
                "X-Trace-Id": qa_id,
            },
        ) as resp:
            if resp.status_code != 200:
                result.error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                return result

            current_event = "message"
            for raw in resp.iter_lines(decode_unicode=True):
                if raw is None:
                    continue
                line = raw.strip()
                if not line:
                    current_event = "message"
                    continue
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                data_str = line.split(":", 1)[1].strip()
                # Track structural milestones via event type, and chunks via payload.
                if current_event == "complete":
                    result.saw_complete = True
                    break
                if current_event == "references":
                    result.saw_references = True
                    continue
                if current_event == "error":
                    result.error = data_str[:500]
                    break
                # Default 'message' carries streamed chunks of the answer.
                try:
                    chunk = json.loads(data_str)
                    if isinstance(chunk, dict) and chunk.get("chunk"):
                        result.saw_chunk = True
                except json.JSONDecodeError:
                    if data_str:
                        result.saw_chunk = True

    except requests.RequestException as e:
        result.error = f"request failed: {e}"

    result.elapsed_secs = time.monotonic() - started
    return result


def verify_in_phoenix(qa_ids: List[str]) -> dict:
    """
    Best-effort Phoenix verification: check that each qa_id has both an LLM
    span and a references span. Returns {qa_id: {"llm": bool, "refs": bool}}.
    """
    try:
        from phoenix import Client
    except ImportError:
        print("phoenix client not installed; skipping post-seed verification")
        return {}

    project = os.getenv("INTER_RATER_PROJECT") or os.getenv("PHOENIX_PROJECT_NAME")
    if not project:
        print("PHOENIX_PROJECT_NAME not set; skipping post-seed verification")
        return {}

    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    api_key = os.getenv("PHOENIX_API_KEY")
    if not endpoint or not api_key:
        print("PHOENIX_COLLECTOR_ENDPOINT or PHOENIX_API_KEY not set; skipping verification")
        return {}

    from datetime import datetime, timedelta
    client = Client(endpoint=endpoint, headers={"Authorization": f"Bearer {api_key}"})
    end = datetime.now()
    start = end - timedelta(hours=1)

    out = {qa: {"llm": False, "refs": False} for qa in qa_ids}

    try:
        llm_df = client.get_spans_dataframe(
            "name == 'com.atlas.rag.generation.response'",
            project_name=project,
            start_time=start,
            end_time=end,
            timeout=30,
        )
        if llm_df is not None and not llm_df.empty and "attributes.qa_id" in llm_df.columns:
            seen = set(str(v) for v in llm_df["attributes.qa_id"].dropna().tolist())
            for qa in qa_ids:
                if qa in seen:
                    out[qa]["llm"] = True
    except Exception as e:
        print(f"phoenix LLM span query failed: {e}")

    try:
        refs_df = client.get_spans_dataframe(
            "name == 'com.atlas.rag.references'",
            project_name=project,
            start_time=start,
            end_time=end,
            timeout=30,
        )
        if refs_df is not None and not refs_df.empty and "attributes.qa_id" in refs_df.columns:
            seen = set(str(v) for v in refs_df["attributes.qa_id"].dropna().tolist())
            for qa in qa_ids:
                if qa in seen:
                    out[qa]["refs"] = True
    except Exception as e:
        print(f"phoenix references span query failed: {e}")

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="Seed questions JSON file")
    parser.add_argument("--count", type=int, default=0, help="Seed only the first N questions (0 = all)")
    parser.add_argument("--dry-run", action="store_true", help="Validate JSON and print sizing check, then exit")
    parser.add_argument("--api", default=DEFAULT_API, help="API base URL")
    parser.add_argument("--no-verify", action="store_true", help="Skip Phoenix span verification at end")
    parser.add_argument("--verify-wait", type=int, default=15, help="Seconds to wait for spans to flush before verification")
    args = parser.parse_args()

    questions = load_questions(args.file)
    if args.count and args.count > 0:
        questions = questions[: args.count]

    print(f"Loaded {len(questions)} questions from {args.file}")
    print_sizing_check(len(questions))

    if args.dry_run:
        print("Dry run — exiting before submission.")
        return 0

    stats = RunStats(total=len(questions))
    results: List[SeedResult] = []
    for i, q in enumerate(questions, start=1):
        print(f"[{i}/{len(questions)}] {q['corpus_filter']} :: {q['question'][:80]}", flush=True)
        r = post_and_drain(args.api, q, i)
        results.append(r)
        status = "ok" if r.ok else "FAIL"
        details = []
        if not r.saw_chunk:
            details.append("no-chunks")
        if not r.saw_references:
            details.append("no-references")
        if not r.saw_complete:
            details.append("no-complete")
        if r.error:
            details.append(f"err={r.error}")
        suffix = f" ({', '.join(details)})" if details else ""
        print(f"      → {status} in {r.elapsed_secs:.1f}s qa_id={r.qa_id}{suffix}", flush=True)
        if r.ok:
            stats.succeeded += 1
        else:
            stats.failed.append(r)

    print()
    print(f"Seeding complete: {stats.succeeded}/{stats.total} successful")

    if stats.failed:
        print(f"Failures ({len(stats.failed)}):")
        for r in stats.failed:
            print(f"  - #{r.index} qa_id={r.qa_id} :: {r.question[:60]}")
            if r.error:
                print(f"      {r.error}")

    if not args.no_verify and stats.succeeded > 0:
        if args.verify_wait > 0:
            print(f"Waiting {args.verify_wait}s for spans to flush…")
            time.sleep(args.verify_wait)
        qa_ids = [r.qa_id for r in results if r.ok]
        verification = verify_in_phoenix(qa_ids)
        if verification:
            missing_llm = [qa for qa, v in verification.items() if not v["llm"]]
            missing_refs = [qa for qa, v in verification.items() if not v["refs"]]
            print(f"Phoenix verification: {len(qa_ids) - len(missing_llm)}/{len(qa_ids)} have LLM span, "
                  f"{len(qa_ids) - len(missing_refs)}/{len(qa_ids)} have references span")
            if missing_llm:
                print(f"  Missing LLM span: {missing_llm[:5]}{' …' if len(missing_llm) > 5 else ''}")
            if missing_refs:
                print(f"  Missing references span: {missing_refs[:5]}{' …' if len(missing_refs) > 5 else ''}")

    return 0 if not stats.failed else 1


if __name__ == "__main__":
    sys.exit(main())
