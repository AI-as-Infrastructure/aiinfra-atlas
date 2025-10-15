#!/usr/bin/env python3
"""
Phoenix backup: export full production project contents to a dated folder.

Usage (loads env from config/.env.production when used via Make):
  make backup-prod

Direct usage examples:
  PHOENIX_ENV_FILE=config/.env.production \
  PHOENIX_BACKUP_ROOT=/var/backups/atlas/phoenix \
  python3 utils/scripts/phoenix_backup_prod.py

Config in this file (edit here):
  BACKUP_DIR_DEFAULT            Base folder under $HOME (relative) or absolute path for backups.
                                The script will create a "phoenix" subfolder under it.
  ENV_FILE_DEFAULT              Which env file to load by default (prod).

Env vars (simplest):
  PHOENIX_PROJECT_BACKUPS       Comma-separated list of projects to backup (required)
  PHOENIX_BACKUP_DIR            Base folder for backups (example: "Dropbox/Technical/.../atlas_hansard_backups").
                                If relative, it's resolved under $HOME. The script will create a "phoenix" subfolder.
                                If unset, defaults to $HOME/atlas_backups.
  PHOENIX_BACKUP_PATH           Convenience: sets the default for PHOENIX_BACKUP_DIR (base folder). If both are set,
                                PHOENIX_BACKUP_DIR wins.

Advanced (optional):
  PHOENIX_BACKUP_ROOT           Full path to the phoenix backup root (overrides PHOENIX_BACKUP_DIR).
  PHOENIX_EXPORT_ANNOTATIONS    true|false (default: true)
  PHOENIX_EXPORT_DATASETS       true|false (default: true)
  PHOENIX_ENV_FILE              Path to env file to load (default: config/.env.development)
"""

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv

try:
    from phoenix import Client
except Exception as e:
    print(f"ERROR: Failed to import phoenix Client: {e}", file=sys.stderr)
    sys.exit(1)

# ---- Defaults you can edit in this script ----
ENV_FILE_DEFAULT = "config/.env.production"

# Load environment (allow override)
ENV_FILE = os.getenv("PHOENIX_ENV_FILE", ENV_FILE_DEFAULT)
try:
    # Ensure values from the env file override existing ones for predictability
    load_dotenv(ENV_FILE, override=True)
except Exception:
    pass
print(f"[backup] Using env file: {ENV_FILE}")

# If PHOENIX_BACKUP_PATH is provided (e.g., in .env.production), use it as the default base directory.
BACKUP_DIR_DEFAULT = os.getenv("PHOENIX_BACKUP_PATH", "atlas_backups")

# Resolve backup path with a single simple variable users can set
HOME_DEFAULT = os.path.expanduser(os.getenv("HOME", "~"))

# If users set PHOENIX_BACKUP_ROOT we honor it directly (advanced override)
_backup_root_env = os.getenv("PHOENIX_BACKUP_ROOT", "").strip()
if _backup_root_env:
    BACKUP_ROOT = Path(_backup_root_env).expanduser().resolve()
    BACKUP_BASE = BACKUP_ROOT.parent
else:
    # Prefer simple PHOENIX_BACKUP_DIR; if relative, resolve under $HOME
    _backup_dir_env = os.getenv("PHOENIX_BACKUP_DIR", BACKUP_DIR_DEFAULT).strip()
    if not _backup_dir_env:
        # default base folder under home
        _backup_dir_env = os.path.join(HOME_DEFAULT, "atlas_backups")
    base_path = Path(_backup_dir_env)
    if not base_path.is_absolute():
        base_path = Path(HOME_DEFAULT) / base_path
    BACKUP_BASE = base_path.expanduser().resolve()
    BACKUP_ROOT = (BACKUP_BASE / "phoenix").resolve()

print(f"[backup] Backup base: {BACKUP_BASE}")
print(f"[backup] Backup root (phoenix): {BACKUP_ROOT}")
# Get projects specifically for backup from env
ENV_PROJECTS = os.getenv("PHOENIX_PROJECT_BACKUPS", "").strip()
if ENV_PROJECTS:
    print(f"[backup] Project(s) from env: {ENV_PROJECTS}")
EXPORT_ANNOTATIONS = os.getenv("PHOENIX_EXPORT_ANNOTATIONS", "true").lower() == "true"
EXPORT_DATASETS = os.getenv("PHOENIX_EXPORT_DATASETS", "true").lower() == "true"
EXPORT_CSV = os.getenv("PHOENIX_EXPORT_CSV", "true").lower() == "true"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Phoenix data (prod) - full project contents")
    return parser.parse_args()


def discover_projects(client: Client) -> List[str]:
    """Get projects from PHOENIX_PROJECT_BACKUPS environment variable only."""
    if ENV_PROJECTS:
        names = [x.strip() for x in ENV_PROJECTS.split(",") if x.strip()]
        if names:
            return sorted(set(names))

    print("ERROR: No projects defined in PHOENIX_PROJECT_BACKUPS environment variable.", file=sys.stderr)
    print("Set PHOENIX_PROJECT_BACKUPS='proj1,proj2,...' in your .env file and rerun.", file=sys.stderr)
    sys.exit(2)




def export_project(
    client: Client,
    project: str,
    out_dir: Path,
) -> None:
    ensure_dir(out_dir)
    print(f"[{project}] Exporting full spans dataframe...", flush=True)

    # Export all spans for the project (no time filtering)
    # Use a longer timeout for large projects (300 seconds = 5 minutes)
    spans_df = client.get_spans_dataframe(project_name=project, timeout=300)
    if spans_df is None or getattr(spans_df, 'empty', False):
        print(f"[{project}] No spans found in project; skipping export.")
        return

    # Merge annotations with spans if available
    if EXPORT_ANNOTATIONS and hasattr(client, "get_span_annotations"):
        try:
            print(f"[{project}] Fetching and merging annotations with spans...", flush=True)
            annotations = client.get_span_annotations(project_name=project)
            if annotations:
                ann_df = pd.DataFrame([a.dict() if hasattr(a, "dict") else a for a in annotations])
                # Merge annotations with spans on span_id or similar key
                # This assumes annotations have a column that links to spans
                if 'span_id' in ann_df.columns and 'span_id' in spans_df.columns:
                    spans_df = spans_df.merge(ann_df, on='span_id', how='left', suffixes=('', '_annotation'))
                elif 'id' in spans_df.columns and 'span_id' in ann_df.columns:
                    spans_df = spans_df.merge(ann_df, left_on='id', right_on='span_id', how='left', suffixes=('', '_annotation'))
                else:
                    print(f"[{project}] Warning: Could not find matching columns to merge annotations with spans")
        except Exception as e:
            print(f"[{project}] Warning: Could not merge annotations (error: {e})", file=sys.stderr)

    # Write combined spans (with annotations if merged)
    spans_df.to_parquet(out_dir / "spans.parquet", index=False)
    if EXPORT_CSV:
        spans_df.to_csv(out_dir / "spans.csv", index=False)

    # Export datasets separately (they're not span-specific)
    if EXPORT_DATASETS and hasattr(client, "get_datasets"):
        try:
            print(f"[{project}] Exporting datasets...", flush=True)
            datasets = client.get_datasets()
            if datasets:
                ds_df = pd.DataFrame([d.dict() if hasattr(d, "dict") else d for d in datasets])
                ds_df.to_parquet(out_dir / "datasets.parquet", index=False)
                if EXPORT_CSV:
                    ds_df.to_csv(out_dir / "datasets.csv", index=False)
        except Exception as e:
            print(f"[{project}] Skipped datasets (error: {e})", file=sys.stderr)


def main() -> None:
    args = parse_args()

    # Date partition (run date in local time)
    day_dir = Path(datetime.now().strftime("%Y/%m/%d"))
    root = (BACKUP_ROOT / day_dir).resolve()
    ensure_dir(root)

    # Configure Phoenix client with API key from environment
    client_headers = os.getenv('PHOENIX_CLIENT_HEADERS', '').strip()
    phoenix_endpoint = "https://app.phoenix.arize.com/legacy"  # Use legacy endpoint for backups
    
    if client_headers:
        # Extract API key from headers string (format: "api_key=xxx")
        if client_headers.startswith('api_key='):
            api_key = client_headers[8:]
            client = Client(api_key=api_key, endpoint=phoenix_endpoint)
        else:
            # Try to use headers as-is
            client = Client(api_key=client_headers, endpoint=phoenix_endpoint)
    else:
        print("WARNING: No PHOENIX_CLIENT_HEADERS found, using default client", file=sys.stderr)
        client = Client(endpoint=phoenix_endpoint)
    
    projects = discover_projects(client)
    print(f"Discovered projects: {projects}")

    for proj in projects:
        proj_dir = root / proj
        export_project(client, proj, proj_dir)

    print(f"Backup complete: {root}")


if __name__ == "__main__":
    main()


