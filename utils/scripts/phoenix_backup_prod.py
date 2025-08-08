#!/usr/bin/env python3
"""
Phoenix backup: export production projects to a dated folder on the server.

Usage (loads env from config/.env.production when used via Make):
  make backup-prod
  make backup-prod-since N=1

Direct usage examples:
  PHOENIX_ENV_FILE=config/.env.production \
  PHOENIX_BACKUP_ROOT=/var/backups/atlas/phoenix \
  python3 utils/scripts/phoenix_backup_prod.py --since-days 1

Config in this file (edit here):
  BACKUP_DIR_DEFAULT            Base folder under $HOME (relative) or absolute path for backups.
                                The script will create a "phoenix" subfolder under it.
  ENV_FILE_DEFAULT              Which env file to load by default (prod).

Env vars (simplest):
  PHOENIX_BACKUP_DIR            Base folder for backups (example: "Dropbox/Technical/.../atlas_hansard_backups").
                                If relative, it's resolved under $HOME. The script will create a "phoenix" subfolder.
                                If unset, defaults to $HOME/atlas_backups.
  PHOENIX_BACKUP_PATH           Convenience: sets the default for PHOENIX_BACKUP_DIR (base folder). If both are set,
                                PHOENIX_BACKUP_DIR wins.

Advanced (optional):
  PHOENIX_BACKUP_ROOT           Full path to the phoenix backup root (overrides PHOENIX_BACKUP_DIR).
  PHOENIX_PROJECTS              Comma-separated list (fallback when auto-discovery not supported)
  PHOENIX_EXPORT_ANNOTATIONS    true|false (default: true)
  PHOENIX_EXPORT_DATASETS       true|false (default: true)
  PHOENIX_ENV_FILE              Path to env file to load (default: config/.env.development)
"""

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime, timedelta
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
# Accept multiple env keys for project specification
ENV_PROJECTS = os.getenv("PHOENIX_PROJECTS", "").strip()
if not ENV_PROJECTS:
    # Common single-project keys used elsewhere in this repo/envs
    for key in ("PHOENIX_PROJECT_NAME", "PHOENIX_PROJECT", "INTER_RATER_PROJECT"):
        val = os.getenv(key, "").strip()
        if val:
            ENV_PROJECTS = val
            break
if ENV_PROJECTS:
    print(f"[backup] Project(s) from env: {ENV_PROJECTS}")
EXPORT_ANNOTATIONS = os.getenv("PHOENIX_EXPORT_ANNOTATIONS", "true").lower() == "true"
EXPORT_DATASETS = os.getenv("PHOENIX_EXPORT_DATASETS", "true").lower() == "true"
EXPORT_CSV = os.getenv("PHOENIX_EXPORT_CSV", "true").lower() == "true"


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Phoenix data (prod)")
    parser.add_argument("--since-days", type=int, default=None,
                        help="Export data since N days ago (UTC)")
    parser.add_argument("--start-date", type=str, default=None,
                        help="Start date YYYY-MM-DD (UTC)")
    parser.add_argument("--end-date", type=str, default=None,
                        help="End date YYYY-MM-DD (UTC, exclusive)")
    return parser.parse_args()


def discover_projects(client: Client) -> List[str]:
    """Try to auto-discover projects from the client; fallback to env list."""
    for attr in ("get_projects", "list_projects", "projects"):
        try:
            meth = getattr(client, attr, None)
            if callable(meth):
                projects_obj = meth()
                names: List[str] = []
                for p in projects_obj or []:
                    if hasattr(p, "name"):
                        names.append(p.name)
                    elif isinstance(p, dict) and "name" in p:
                        names.append(p["name"])
                    elif isinstance(p, str):
                        names.append(p)
                names = [n for n in names if n]
                if names:
                    return sorted(set(names))
        except Exception:
            pass

    # Fallback to env var list
    if ENV_PROJECTS:
        names = [x.strip() for x in ENV_PROJECTS.split(",") if x.strip()]
        if names:
            return sorted(set(names))

    print("ERROR: Could not discover projects and no project env was set.", file=sys.stderr)
    print("Set PHOENIX_PROJECTS='proj1,proj2,...' or PHOENIX_PROJECT_NAME='proj' and rerun.", file=sys.stderr)
    sys.exit(2)


def to_dt(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    return datetime.strptime(date_str, "%Y-%m-%d")


def export_project(
    client: Client,
    project: str,
    out_dir: Path,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> None:
    ensure_dir(out_dir)
    print(f"[{project}] Exporting spans dataframe...", flush=True)

    # get_spans_dataframe supports (project_name, start_time, end_time) on recent phoenix
    spans_df = client.get_spans_dataframe(
        project_name=project,
        start_time=start_time,
        end_time=end_time,
    )
    if spans_df is None or getattr(spans_df, 'empty', False):
        print(f"[{project}] No spans returned for the given range; writing an empty marker.")
        ensure_dir(out_dir)
        (out_dir / "EMPTY").write_text("no spans")
        return
    # Write Parquet
    spans_df.to_parquet(out_dir / "spans.parquet", index=False)
    # Write CSV (optional)
    if EXPORT_CSV:
        spans_df.to_csv(out_dir / "spans.csv", index=False)

    if EXPORT_ANNOTATIONS and hasattr(client, "get_span_annotations"):
        try:
            print(f"[{project}] Exporting annotations...", flush=True)
            annotations = client.get_span_annotations(project_name=project)
            if annotations:
                ann_df = pd.DataFrame([a.dict() if hasattr(a, "dict") else a for a in annotations])
                ann_df.to_parquet(out_dir / "annotations.parquet", index=False)
                if EXPORT_CSV:
                    ann_df.to_csv(out_dir / "annotations.csv", index=False)
        except Exception as e:
            print(f"[{project}] Skipped annotations (error: {e})", file=sys.stderr)

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

    # Date partition (run date in UTC)
    day_dir = Path(datetime.utcnow().strftime("%Y/%m/%d"))
    root = (BACKUP_ROOT / day_dir).resolve()
    ensure_dir(root)

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    if args.since_days is not None:
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=args.since_days)
    else:
        start_time = to_dt(args.start_date)
        end_time = to_dt(args.end_date)

    client = Client()
    projects = discover_projects(client)
    print(f"Discovered projects: {projects}")

    for proj in projects:
        proj_dir = root / proj
        export_project(client, proj, proj_dir, start_time=start_time, end_time=end_time)

    print(f"Backup complete: {root}")


if __name__ == "__main__":
    main()


