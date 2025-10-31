#!/usr/bin/env python3
"""
Phoenix backup: export spans and feedback annotations (incl. UI "note") from Phoenix (Legacy by default).

Usage (loads env from config/.env.production unless overridden):
  PHOENIX_PROJECT_BACKUPS="Project A,Project B" \
  PHOENIX_API_KEY="system:..." \
  PHOENIX_BASE_URL="https://app.phoenix.arize.com/legacy" \
  python3 phoenix_backup_prod.py

Common env vars:
  PHOENIX_PROJECT_BACKUPS       Comma-separated project names or IDs (required).
  PHOENIX_BASE_URL              Phoenix base URL. Default: https://app.phoenix.arize.com/legacy
  PHOENIX_API_KEY               API key (colons are OK). Uses Bearer auth.
  PHOENIX_ENV_FILE              .env path (default: config/.env.production)
  PHOENIX_BACKUP_DIR            Base folder for backups (relative to $HOME if relative).
  PHOENIX_BACKUP_ROOT           Advanced: absolute path to use directly as backup root.
  PHOENIX_EXPORT_ANNOTATIONS    true|false (default: true)
  PHOENIX_EXPORT_DATASETS       true|false (default: true)
  PHOENIX_EXPORT_CSV            true|false (default: true)
  PHOENIX_INCLUDE_NAMES         Comma list to *include* specific annotation names (e.g., "correctness,relevance,note")
  PHOENIX_EXCLUDE_NAMES         Comma list to *exclude* annotation names (overrides the default)
"""

from __future__ import annotations

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pandas as pd

# --- dotenv (optional) ---
ENV_FILE_DEFAULT = "config/.env.production"
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv(os.getenv("PHOENIX_ENV_FILE", ENV_FILE_DEFAULT), override=True)
except Exception:
    pass

print(f"[backup] Using env file: {os.getenv('PHOENIX_ENV_FILE', ENV_FILE_DEFAULT)}")

# --- Resolve backup paths ---
HOME_DEFAULT = os.path.expanduser(os.getenv("HOME", "~"))
BACKUP_DIR_DEFAULT = os.getenv("PHOENIX_BACKUP_PATH", "atlas_backups")

_backup_root_env = os.getenv("PHOENIX_BACKUP_ROOT", "").strip()
if _backup_root_env:
    BACKUP_ROOT = Path(_backup_root_env).expanduser().resolve()
    BACKUP_BASE = BACKUP_ROOT.parent
else:
    _backup_dir_env = os.getenv("PHOENIX_BACKUP_DIR", BACKUP_DIR_DEFAULT).strip() or os.path.join(HOME_DEFAULT, "atlas_backups")
    base_path = Path(_backup_dir_env)
    if not base_path.is_absolute():
        base_path = Path(HOME_DEFAULT) / base_path
    BACKUP_BASE = base_path.expanduser().resolve()
    BACKUP_ROOT = (BACKUP_BASE / "phoenix").resolve()

print(f"[backup] Backup base: {BACKUP_BASE}")
print(f"[backup] Backup root (phoenix): {BACKUP_ROOT}")

# --- Export toggles ---
EXPORT_ANNOTATIONS = os.getenv("PHOENIX_EXPORT_ANNOTATIONS", "true").lower() == "true"
EXPORT_DATASETS = os.getenv("PHOENIX_EXPORT_DATASETS", "true").lower() == "true"
EXPORT_CSV = os.getenv("PHOENIX_EXPORT_CSV", "true").lower() == "true"


# --- Annotation name filters (optional) ---
def _csv_list(env_name: str) -> Optional[list[str]]:
    raw = os.getenv(env_name, "").strip()
    if not raw:
        return None
    vals = [x.strip() for x in raw.split(",") if x.strip()]
    return vals or None

INCLUDE_NAMES = _csv_list("PHOENIX_INCLUDE_NAMES")
EXCLUDE_NAMES = _csv_list("PHOENIX_EXCLUDE_NAMES")
# Important: Some client versions *exclude* "note" by default. We want ALL feedback,
# so unless the user explicitly sets PHOENIX_EXCLUDE_NAMES, we disable the exclusion list.
if EXCLUDE_NAMES is None:
    EXCLUDE_NAMES = None  # include everything (incl. "note")

# --- Phoenix client import (supports both new and older client package layouts) ---
Client = None
_client_import_err = None
try:
    # Preferred modern import path
    from phoenix.client import Client as _PhoenixClient  # type: ignore
    Client = _PhoenixClient
except Exception as e1:
    _client_import_err = e1
    try:
        # Back-compat fallback (older packages)
        from phoenix import Client as _PhoenixClientOld  # type: ignore
        Client = _PhoenixClientOld
    except Exception as e2:
        print("ERROR: Could not import Phoenix Client API.", file=sys.stderr)
        print(f" - Tried 'from phoenix.client import Client': {e1}", file=sys.stderr)
        print(f" - Tried 'from phoenix import Client': {e2}", file=sys.stderr)
        sys.exit(1)

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Phoenix spans and feedback annotations (Legacy-compatible).")
    # Reserved for future flags; env drives most behavior for simplicity.
    return parser.parse_args()

def discover_projects() -> List[str]:
    env_projects = os.getenv("PHOENIX_PROJECT_BACKUPS", "").strip()
    if not env_projects:
        print("ERROR: No projects defined in PHOENIX_PROJECT_BACKUPS.", file=sys.stderr)
        print("Set PHOENIX_PROJECT_BACKUPS='proj1,proj2,...' and rerun.", file=sys.stderr)
        sys.exit(2)
    names = sorted(set([x.strip() for x in env_projects.split(",") if x.strip()]))
    print(f"[backup] Project(s): {', '.join(names)}")
    return names

def init_client() -> "Client":
    api_key = os.getenv("PHOENIX_API_KEY", "").strip()
    base_url = os.getenv("PHOENIX_BASE_URL", "https://app.phoenix.arize.com/legacy").strip()

    if not base_url:
        base_url = "https://app.phoenix.arize.com/legacy"

    # The Client signature is (base_url=..., api_key=...) in modern SDKs.
    # Older clients may also accept endpoint=..., headers=...; we try the modern way first.
    try:
        client = Client(base_url=base_url, api_key=api_key if api_key else None)
        return client
    except TypeError:
        # Older SDK fallback
        kwargs = {}
        if api_key:
            kwargs["api_key"] = api_key
        try:
            client = Client(endpoint=base_url, **kwargs)  # type: ignore
            return client
        except Exception as e:
            print(f"ERROR: Failed to initialize Phoenix client: {e}", file=sys.stderr)
            sys.exit(3)

def export_project(client: "Client", project: str, out_dir: Path) -> None:
    ensure_dir(out_dir)
    print(f"[{project}] Exporting spans…", flush=True)

    # --- (A) Spans ---
    spans_df = None
    # Prefer modern method path: client.spans.get_spans_dataframe(...)
    if hasattr(client, "spans") and hasattr(client.spans, "get_spans_dataframe"):
        spans_df = client.spans.get_spans_dataframe(
            project_identifier=project,
            timeout=300,
        )
    elif hasattr(client, "get_spans_dataframe"):
        # Older client fallback
        spans_df = client.get_spans_dataframe(project_name=project, timeout=300)
    else:
        print(f"[{project}] ERROR: Client does not support spans export.", file=sys.stderr)
        return

    if spans_df is None or getattr(spans_df, "empty", False):
        print(f"[{project}] No spans found; skipping.")
        return

    print(f"[{project}] Spans shape: {spans_df.shape}")

    # --- (B) Fetch and merge annotations into spans ---
    if EXPORT_ANNOTATIONS:
        ann_df = None
        if hasattr(client, "spans") and hasattr(client.spans, "get_span_annotations_dataframe"):
            ann_df = client.spans.get_span_annotations_dataframe(
                spans_dataframe=spans_df,
                project_identifier=project,
                include_annotation_names=INCLUDE_NAMES,  # None → include all names
                exclude_annotation_names=EXCLUDE_NAMES,  # None → do NOT exclude "note"
                limit=10_000,
                timeout=300,
            )
        elif hasattr(client, "get_span_annotations"):
            # Very old fallback: returns a list; we convert to DataFrame
            try:
                anns = client.get_span_annotations(project_name=project)  # type: ignore
                if anns:
                    ann_df = pd.DataFrame([a.dict() if hasattr(a, "dict") else a for a in anns])
            except Exception as e:
                print(f"[{project}] Warning: legacy get_span_annotations failed: {e}", file=sys.stderr)

        if ann_df is not None and not getattr(ann_df, "empty", False):
            print(f"[{project}] Annotations fetched: {ann_df.shape[0]} rows")

            # Merge annotations into spans
            # Spans is indexed by context.span_id, annotations is indexed by span_id
            try:
                # Reset annotation index to make span_id a column
                ann_df_reset = ann_df.reset_index()

                # Merge using index (context.span_id) matched to span_id column
                spans_df = spans_df.merge(
                    ann_df_reset,
                    left_index=True,
                    right_on='span_id',
                    how='left',
                    suffixes=('', '_annotation')
                )
                print(f"[{project}] Merged annotations into spans. Final shape: {spans_df.shape}")
            except Exception as e:
                print(f"[{project}] Warning: Failed to merge annotations: {e}", file=sys.stderr)
        else:
            print(f"[{project}] No annotations returned.")

    # --- (C) Save merged spans (annotations are now part of spans_df) ---
    ensure_dir(out_dir)
    spans_parquet = out_dir / "spans.parquet"
    spans_csv = out_dir / "spans.csv"

    print(f"[{project}] Saving merged data...")
    spans_df.to_parquet(spans_parquet, index=False)
    if EXPORT_CSV:
        spans_df.to_csv(spans_csv, index=False)
    print(f"[{project}] Saved: {spans_parquet.name} ({spans_df.shape[0]} rows, {spans_df.shape[1]} columns)")

    # --- (D) Datasets (optional, if client supports it) ---
    if EXPORT_DATASETS:
        try:
            ds_df = None
            if hasattr(client, "datasets") and hasattr(client.datasets, "list_datasets"):
                # modern datasets surface
                ds_list = client.datasets.list_datasets(project_identifier=project)  # type: ignore
                if ds_list:
                    ds_df = pd.DataFrame([d.dict() if hasattr(d, "dict") else d for d in ds_list])
            elif hasattr(client, "get_datasets"):
                ds_list = client.get_datasets()  # type: ignore
                if ds_list:
                    ds_df = pd.DataFrame([d.dict() if hasattr(d, "dict") else d for d in ds_list])

            if ds_df is not None and not ds_df.empty:
                ds_parquet = out_dir / "datasets.parquet"
                ds_csv = out_dir / "datasets.csv"
                ds_df.to_parquet(ds_parquet, index=False)
                if EXPORT_CSV:
                    ds_df.to_csv(ds_csv, index=False)
                print(f"[{project}] Datasets saved: {ds_df.shape[0]} rows")
            else:
                print(f"[{project}] No datasets found or client lacks dataset APIs.")
        except Exception as e:
            print(f"[{project}] Datasets export skipped (error): {e}", file=sys.stderr)

def main() -> None:
    _ = parse_args()

    # Date partition (local time)
    day_dir = Path(datetime.now().strftime("%Y/%m/%d"))
    root = (BACKUP_ROOT / day_dir).resolve()
    ensure_dir(root)

    client = init_client()
    projects = discover_projects()

    print(f"[backup] Output root: {root}")
    for proj in projects:
        proj_dir = root / proj
        export_project(client, proj, proj_dir)

    print(f"[backup] Complete: {root}")

if __name__ == "__main__":
    main()
