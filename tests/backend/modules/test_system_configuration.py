import json
import sys
import types

from backend.modules.system_configuration import SystemConfiguration


def _mock_inter_rater(monkeypatch, enabled: bool):
    fake_module = types.SimpleNamespace(
        inter_rater_service=types.SimpleNamespace(is_enabled=lambda: enabled)
    )
    monkeypatch.setitem(sys.modules, "backend.services.inter_rater_service", fake_module)


def test_save_config_writes_file_and_casts_types(tmp_path, monkeypatch):
    _mock_inter_rater(monkeypatch, enabled=False)

    config_path = tmp_path / "system_settings.json"
    manager = SystemConfiguration(config_path=str(config_path))

    success = manager.save_config({"telemetryEnabled": "yes", "interRaterEnabled": 1})

    assert success is True
    saved = json.loads(config_path.read_text())
    assert saved["telemetryEnabled"] is True
    assert saved["interRaterEnabled"] is True


def test_update_config_merges_values(tmp_path, monkeypatch):
    _mock_inter_rater(monkeypatch, enabled=False)

    config_path = tmp_path / "system_settings.json"
    manager = SystemConfiguration(config_path=str(config_path))
    manager.save_config({"telemetryEnabled": False, "interRaterEnabled": False})

    success = manager.update_config({"telemetryEnabled": True})

    assert success is True
    current = manager.get_config()
    assert current["telemetryEnabled"] is True
    assert current["interRaterEnabled"] is False


def test_env_overrides_telemetry_file_value(tmp_path, monkeypatch):
    _mock_inter_rater(monkeypatch, enabled=False)
    monkeypatch.setenv("ENABLE_TELEMETRY", "true")

    config_path = tmp_path / "system_settings.json"
    config_path.write_text(json.dumps({"telemetryEnabled": False, "interRaterEnabled": False}))

    manager = SystemConfiguration(config_path=str(config_path))

    assert manager.is_telemetry_enabled() is True


def test_inter_rater_reads_from_service(tmp_path, monkeypatch):
    _mock_inter_rater(monkeypatch, enabled=True)

    config_path = tmp_path / "system_settings.json"
    manager = SystemConfiguration(config_path=str(config_path))

    assert manager.is_inter_rater_enabled() is True


def test_save_config_fails_when_directory_not_writable(tmp_path, monkeypatch):
    _mock_inter_rater(monkeypatch, enabled=False)

    config_path = tmp_path / "system_settings.json"
    manager = SystemConfiguration(config_path=str(config_path))

    real_os_access = __import__("os").access

    def fake_access(path, mode):
        if str(path) == str(config_path.parent):
            return False
        return real_os_access(path, mode)

    monkeypatch.setattr("backend.modules.system_configuration.os.access", fake_access)

    success = manager.save_config({"telemetryEnabled": True, "interRaterEnabled": False})

    assert success is False


def test_configuration_persists_across_restart(tmp_path, monkeypatch):
    _mock_inter_rater(monkeypatch, enabled=False)

    config_path = tmp_path / "system_settings.json"
    manager = SystemConfiguration(config_path=str(config_path))
    assert manager.save_config({"telemetryEnabled": True, "interRaterEnabled": False}) is True

    reloaded_manager = SystemConfiguration(config_path=str(config_path))
    current = reloaded_manager.get_config()

    assert current["telemetryEnabled"] is True
    assert current["interRaterEnabled"] is False
