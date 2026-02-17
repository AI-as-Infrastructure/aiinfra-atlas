#!/usr/bin/env python3
"""
Migrate runtime system configuration for existing ATLAS deployments.

Creates or updates config/system_settings.json with safe defaults while preserving
existing settings unless --force is specified.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict


DEFAULT_SETTINGS: Dict[str, Any] = {
    "telemetryEnabled": False,
    "interRaterEnabled": False,
}


def _env_to_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def derive_safe_defaults_from_env() -> Dict[str, Any]:
    settings = DEFAULT_SETTINGS.copy()

    telemetry_env = os.getenv("ENABLE_TELEMETRY")
    if telemetry_env is not None:
        settings["telemetryEnabled"] = _env_to_bool(telemetry_env)

    return settings


def migrate_system_settings(config_path: Path, force: bool = False) -> Dict[str, Any]:
    config_path.parent.mkdir(parents=True, exist_ok=True)

    env_defaults = derive_safe_defaults_from_env()
    already_exists = config_path.exists()

    if already_exists:
        with open(config_path, "r", encoding="utf-8") as f:
            existing = json.load(f)

        if not force:
            return {
                "status": "unchanged",
                "path": str(config_path),
                "settings": existing,
                "reason": "existing_config_preserved",
            }

        merged = {
            "telemetryEnabled": bool(existing.get("telemetryEnabled", env_defaults["telemetryEnabled"])),
            "interRaterEnabled": bool(existing.get("interRaterEnabled", env_defaults["interRaterEnabled"])),
        }
    else:
        merged = env_defaults

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    return {
        "status": "updated" if already_exists else "created",
        "path": str(config_path),
        "settings": merged,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate ATLAS runtime system settings")
    parser.add_argument(
        "--config-path",
        default="config/system_settings.json",
        help="Path to system settings file (default: config/system_settings.json)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite existing config with merged safe defaults",
    )

    args = parser.parse_args()
    result = migrate_system_settings(Path(args.config_path), force=args.force)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
