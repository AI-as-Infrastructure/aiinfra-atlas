"""
Reset the inter-rater test project by deleting it from Phoenix.

Deleting the project removes both the seeded sessions and any inter-rater
annotations submitted during testing. Phoenix auto-recreates the project
on the next span ingest, so `make seed` immediately afterwards restores
the baseline.

Usage:
    .venv/bin/python utils/scripts/seed_reset.py [--yes] [--force]

Safety:
- Refuses by default if the project name looks like a production project
  (contains 'prod' or 'production'). Pass --force to override.
- Prompts for confirmation unless --yes is passed.
"""

from __future__ import annotations

import argparse
import os
import sys

import httpx

PROD_HINTS = ("prod", "production")


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yes", action="store_true", help="Skip the confirmation prompt")
    parser.add_argument("--force", action="store_true", help="Allow deleting a project whose name looks like prod")
    args = parser.parse_args()

    endpoint = get_endpoint()
    project = get_project_name()

    print(f"Phoenix endpoint: {endpoint}")
    print(f"Project to delete: {project}")

    if looks_like_prod(project) and not args.force:
        print(
            f"\nRefusing to delete '{project}': the name looks like a production project.\n"
            "Pass --force if you really mean it (and you should not — use a dedicated\n"
            "INTER_RATER_PROJECT for seed testing, e.g. ATLAS-SeedTest)."
        )
        return 2

    if not args.yes:
        resp = input(f"\nDelete project '{project}' and ALL its spans/annotations? Type the project name to confirm: ").strip()
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
        return 0
    if r.status_code == 404:
        print(f"\nProject '{project}' does not exist on Phoenix — nothing to reset. Run `make seed` to create it.")
        return 0
    print(f"\nDELETE {url} → {r.status_code}: {r.text[:300]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
