import json
from pathlib import Path

from utils.scripts.migrate_system_settings import migrate_system_settings


def test_migration_creates_safe_defaults(tmp_path, monkeypatch):
    monkeypatch.delenv("ENABLE_TELEMETRY", raising=False)

    config_path = tmp_path / "config" / "system_settings.json"
    result = migrate_system_settings(config_path)

    assert result["status"] == "created"
    saved = json.loads(config_path.read_text())
    assert saved["telemetryEnabled"] is False
    assert saved["interRaterEnabled"] is False


def test_migration_uses_env_for_telemetry_default(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_TELEMETRY", "true")

    config_path = tmp_path / "config" / "system_settings.json"
    result = migrate_system_settings(config_path)

    assert result["status"] == "created"
    saved = json.loads(config_path.read_text())
    assert saved["telemetryEnabled"] is True
    assert saved["interRaterEnabled"] is False


def test_migration_preserves_existing_without_force(tmp_path, monkeypatch):
    monkeypatch.setenv("ENABLE_TELEMETRY", "false")

    config_path = tmp_path / "config" / "system_settings.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"telemetryEnabled": True, "interRaterEnabled": True}),
        encoding="utf-8",
    )

    result = migrate_system_settings(config_path, force=False)

    assert result["status"] == "unchanged"
    saved = json.loads(config_path.read_text())
    assert saved["telemetryEnabled"] is True
    assert saved["interRaterEnabled"] is True


def test_migration_force_keeps_existing_values(tmp_path):
    config_path = tmp_path / "config" / "system_settings.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps({"telemetryEnabled": True, "interRaterEnabled": False}),
        encoding="utf-8",
    )

    result = migrate_system_settings(config_path, force=True)

    assert result["status"] == "updated"
    saved = json.loads(config_path.read_text())
    assert saved["telemetryEnabled"] is True
    assert saved["interRaterEnabled"] is False
