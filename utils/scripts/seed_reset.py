"""
Reset the inter-rater test project by deleting it from Phoenix.

Deleting the project removes both the seeded sessions and any inter-rater
annotations submitted during testing. Phoenix auto-recreates the project
on the next span ingest, so `make seed` immediately afterwards restores
the baseline.

Usage:
    .venv/bin/python utils/scripts/seed_reset.py [--yes] [--force]

Safety:
- Refuses by default when the loaded environment file is a production
  deployment (ENVIRONMENT=production), or when the project name looks like a
  production project. Pass --force to override.
- Prompts for confirmation unless --yes is passed. A protected target always
  prompts, so --yes --force cannot delete a live study unattended.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.services.inter_rater_pool import require_manifest_path  # noqa: E402

PROD_HINTS = ("prod", "production")


def remove_pool_manifest() -> None:
    """
    Drop the study pool manifest along with the project it describes.

    Left behind it would name qa_ids that no longer exist, so the allocator
    would surface an empty pool until the next `make seed` rewrites it.
    """
    try:
        path = require_manifest_path()
    except ValueError as error:
        raise SystemExit(str(error)) from error
    try:
        os.remove(path)
    except FileNotFoundError:
        return
    print(f"Removed stale study pool manifest: {path}")


def get_endpoint() -> str:
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "").rstrip("/")
    if not endpoint:
        raise SystemExit("PHOENIX_COLLECTOR_ENDPOINT is not set")
    return endpoint


def get_project_name() -> str:
    name = os.getenv("INTER_RATER_PROJECT") or os.getenv("PHOENIX_PROJECT_NAME")
    if not name:
        raise SystemExit("Neither INTER_RATER_PROJECT nor PHOENIX_PROJECT_NAME is set")
    return name


def get_headers() -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("PHOENIX_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def looks_like_prod(name: str) -> bool:
    lowered = name.lower()
    return any(hint in lowered for hint in PROD_HINTS)


def protection_reason(project: str) -> str | None:
    """
    Name why this target is protected, or None if it is not.

    ENVIRONMENT is set by the environment file the caller sourced, so it
    identifies the deployment whatever the study project happens to be called
    — the name heuristic alone misses any production project not named for
    one. The heuristic stays as a second net for a production-looking project
    reached through some other environment file.
    """
    if (os.getenv("ENVIRONMENT") or "").strip().lower() == "production":
        return "ENVIRONMENT=production in the loaded environment file"
    if looks_like_prod(project):
        return f"the project name '{project}' looks like a production project"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    parser.add_argument("--force", action="store_true", help="Allow deleting a project whose name looks like prod")
    args = parser.parse_args()

    # Validate all environment-specific targets before deleting the project.
    # Otherwise a missing manifest setting could leave a stale pool behind only
    # after the irreversible part of the reset had already succeeded.
    try:
        require_manifest_path()
    except ValueError as error:
        raise SystemExit(str(error)) from error

    endpoint = get_endpoint()
    project = get_project_name()

    print(f"Phoenix endpoint: {endpoint}")
    print(f"Project to delete: {project}")

    reason = protection_reason(project)
    if reason and not args.force:
        print(
            f"\nRefusing to delete '{project}': {reason}.\n"
            "Pass --force if you really mean it (and you should not — use a dedicated\n"
            "INTER_RATER_PROJECT for seed testing, e.g. ATLAS-SeedTest)."
        )
        return 2

    # --force lifts the refusal above but never the confirmation: deleting a
    # protected study is always a deliberate keystroke, so an automated or
    # mistyped --yes --force cannot destroy reviewer data.
    if not args.yes or reason:
        try:
            resp = input(f"\nDelete project '{project}' and ALL its spans/annotations? Type the project name to confirm: ").strip()
        except EOFError:
            print("\nNo input available to confirm a protected deletion — aborting.")
            return 1
        if resp != project:
            print("Confirmation did not match — aborting.")
            return 1

    url = f"{endpoint}/v1/projects/{project}"
    try:
        r = httpx.delete(url, headers=get_headers(), timeout=30.0)
    except httpx.HTTPError as e:
        print(f"Request failed: {e}")
        return 1

    if r.status_code == 204:
        print(f"\nDeleted project '{project}'. Run `make seed` to repopulate the baseline.")
        remove_pool_manifest()
        return 0
    if r.status_code == 404:
        print(f"\nProject '{project}' does not exist on Phoenix — nothing to reset. Run `make seed` to create it.")
        remove_pool_manifest()
        return 0
    print(f"\nDELETE {url} → {r.status_code}: {r.text[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
