import json
from pathlib import Path

from backend.modules.configuration_export import ConfigurationExporter
from backend.modules.configuration_import import ConfigurationImporter


class DummySystemConfig:
    def __init__(self, config):
        self._config = config

    def get_config(self):
        return self._config


def test_exporter_sanitizes_description():
    exporter = ConfigurationExporter()
    raw = "  hello\x00world\r\n"

    result = exporter._sanitize_description(raw)

    assert result == "helloworld"


def test_exporter_filters_sensitive_system_fields(monkeypatch):
    exporter = ConfigurationExporter()

    from backend.modules import system_configuration

    monkeypatch.setattr(
        system_configuration,
        "get_system_config",
        lambda: DummySystemConfig(
            {
                "telemetryEnabled": True,
                "interRaterEnabled": False,
                "apiKey": "secret",
                "auth_token": "secret-2",
            }
        ),
    )

    system = exporter.gather_system_config()

    assert system["telemetryEnabled"] is True
    assert system["interRaterEnabled"] is False
    assert "apiKey" not in system
    assert "auth_token" not in system


def test_importer_create_configuration_diff():
    importer = ConfigurationImporter()
    current = {
        "corpus": {"name": "old", "source": "local"},
        "system": {"telemetryEnabled": False},
    }
    incoming = {
        "corpus": {"name": "new"},
        "system": {"telemetryEnabled": True},
        "test_target": {"provider": "openai"},
    }

    diff = importer.create_configuration_diff(current, incoming)

    assert "test_target" in diff["added"]
    assert "corpus.source" in diff["removed"]
    assert "corpus.name" in diff["changed"]
    assert "system.telemetryEnabled" in diff["changed"]


def test_importer_rolls_back_when_apply_fails(tmp_path, monkeypatch):
    importer = ConfigurationImporter()

    backup_file = tmp_path / "backup.json"
    backup_file.write_text(
        json.dumps(
            {
                "corpus": {"name": "previous"},
                "test_target": {"provider": "openai", "model": "gpt-4"},
                "system": {"telemetryEnabled": False, "interRaterEnabled": False},
            }
        )
    )

    monkeypatch.setattr(importer, "create_configuration_backup", lambda: backup_file)
    monkeypatch.setattr(importer, "rollback_from_backup", lambda _: True)
    monkeypatch.setattr(importer, "apply_corpus_config", lambda _: False)
    monkeypatch.setattr(importer, "apply_target_config", lambda _: True)
    monkeypatch.setattr(importer, "apply_system_config", lambda _: True)

    config_data = {
        "atlas_config_version": "1.0",
        "corpus": {"name": "new"},
        "test_target": {"provider": "openai", "model": "gpt-4"},
        "system": {"telemetryEnabled": True, "interRaterEnabled": True},
    }

    success, result = importer.import_configuration(config_data)

    assert success is False
    assert result["backup_path"] == str(backup_file)
    assert "Import failed and rollback completed from backup" in result["warnings"]


def test_exporter_build_export_json_format(monkeypatch):
    exporter = ConfigurationExporter()

    monkeypatch.setattr(exporter, "gather_corpus_config", lambda: {"name": "demo"})
    monkeypatch.setattr(exporter, "gather_target_config", lambda: {"provider": "openai"})
    monkeypatch.setattr(exporter, "gather_system_config", lambda: {"telemetryEnabled": True})

    payload = exporter.build_export_json(config_name="Sample", description="Test")

    assert payload["atlas_config_version"] == "1.0"
    assert payload["config_name"] == "Sample"
    assert payload["corpus"]["name"] == "demo"
    assert payload["test_target"]["provider"] == "openai"
    assert payload["system"]["telemetryEnabled"] is True


def test_exporter_caches_corpus_gathering(monkeypatch):
    exporter = ConfigurationExporter()

    call_counter = {"count": 0}

    class FakePath:
        def __init__(self, *_args, **_kwargs):
            pass

        def exists(self):
            call_counter["count"] += 1
            return False

    monkeypatch.setattr("backend.modules.configuration_export.Path", FakePath)

    first = exporter.gather_corpus_config()
    second = exporter.gather_corpus_config()

    assert first == second
    assert call_counter["count"] == 2


def test_exporter_minimizes_json_size_by_pruning_empty_values(monkeypatch):
    exporter = ConfigurationExporter()

    monkeypatch.setattr(
        exporter,
        "gather_corpus_config",
        lambda: {
            "name": "",
            "embedding": {
                "model": "demo-model",
                "chunk_size": 0,
                "notes": "",
            },
            "filters": [],
            "metadata": None,
        },
    )
    monkeypatch.setattr(
        exporter,
        "gather_target_config",
        lambda: {
            "provider": "openai",
            "model": "",
        },
    )
    monkeypatch.setattr(
        exporter,
        "gather_system_config",
        lambda: {
            "telemetryEnabled": False,
            "interRaterEnabled": True,
            "notes": "",
        },
    )

    payload = exporter.build_export_json(config_name="Minimized", description="")

    assert "name" not in payload["corpus"]
    assert payload["corpus"]["embedding"]["model"] == "demo-model"
    assert payload["corpus"]["embedding"]["chunk_size"] == 0
    assert "filters" not in payload["corpus"]
    assert "metadata" not in payload["corpus"]
    assert payload["test_target"]["provider"] == "openai"
    assert "model" not in payload["test_target"]
    assert payload["system"]["telemetryEnabled"] is False
    assert payload["system"]["interRaterEnabled"] is True
    assert "notes" not in payload["system"]
