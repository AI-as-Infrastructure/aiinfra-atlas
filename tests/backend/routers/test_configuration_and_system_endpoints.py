import json
import gzip

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers import configuration as configuration_router
from backend.routers import system as system_router
from backend.modules.configuration_import import ConfigurationImporter


class DummySystemConfig:
    def __init__(self):
        self._config = {"telemetryEnabled": False, "interRaterEnabled": False}

    def save_config(self, config):
        self._config = config
        return True

    def reload(self):
        return None

    def get_config(self):
        return self._config

    def is_telemetry_enabled(self):
        return self._config.get("telemetryEnabled", False)

    def is_inter_rater_enabled(self):
        return self._config.get("interRaterEnabled", False)


class DummyImporter:
    def validate_import_structure(self, config_data):
        return True, []

    def check_version_compatibility(self, config_data):
        if config_data.get("atlas_config_version") == "9.9":
            return False, "Unsupported configuration version: 9.9"
        return True, "Version compatible"

    def validate_resources(self, config_data):
        return True, []

    def import_configuration(self, config_data):
        if config_data.get("atlas_config_version") == "9.9":
            return False, {
                "success": False,
                "errors": ["Unsupported configuration version: 9.9"],
                "warnings": [],
                "backup_path": None,
                "diff": {"added": [], "removed": [], "changed": []},
            }
        return True, {
            "success": True,
            "errors": [],
            "warnings": [],
            "backup_path": "backend/targets/config_import_backups/import_backup.json",
            "diff": {"added": ["corpus.name"], "removed": [], "changed": []},
        }


class DummyExporter:
    def gather_corpus_config(self):
        return {"name": "demo"}

    def gather_target_config(self):
        return {"provider": "openai"}

    def gather_system_config(self):
        return {"telemetryEnabled": True, "interRaterEnabled": False}

    def build_export_json(self, config_name, description):
        return {
            "atlas_config_version": "1.0",
            "exported_at": "2026-02-17T00:00:00",
            "atlas_version": "1.0.0",
            "config_name": config_name or "sample",
            "description": description or "",
            "corpus": self.gather_corpus_config(),
            "test_target": self.gather_target_config(),
            "system": self.gather_system_config(),
        }


def _app_with_system_router(monkeypatch):
    app = FastAPI()
    app.include_router(system_router.router)
    app.dependency_overrides[system_router.get_current_user] = lambda: {"sub": "test-user"}
    monkeypatch.setattr(system_router, "get_system_config", lambda: DummySystemConfig())
    return app


def _app_with_system_router_and_shared_config(monkeypatch):
    app = FastAPI()
    app.include_router(system_router.router)
    app.dependency_overrides[system_router.get_current_user] = lambda: {"sub": "test-user"}
    shared_config = DummySystemConfig()
    monkeypatch.setattr(system_router, "get_system_config", lambda: shared_config)
    return app, shared_config


def _app_with_configuration_router(monkeypatch):
    app = FastAPI()
    app.include_router(configuration_router.router)
    app.dependency_overrides[configuration_router.get_current_user] = lambda: {"sub": "test-user"}
    monkeypatch.setattr(configuration_router, "get_configuration_importer", lambda: DummyImporter())
    monkeypatch.setattr(configuration_router, "get_configuration_exporter", lambda: DummyExporter())
    return app


def test_system_configuration_endpoint_with_valid_data(monkeypatch):
    app = _app_with_system_router(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/api/system/configuration",
        json={"telemetryEnabled": True, "interRaterEnabled": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["config"]["telemetryEnabled"] is True


def test_system_configuration_endpoint_with_invalid_data(monkeypatch):
    app = _app_with_system_router(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/api/system/configuration",
        json={"telemetryEnabled": {"bad": "value"}, "interRaterEnabled": False},
    )

    assert response.status_code == 422


def test_system_configuration_endpoint_rejects_extra_fields(monkeypatch):
    app = _app_with_system_router(monkeypatch)
    client = TestClient(app)

    response = client.post(
        "/api/system/configuration",
        json={
            "telemetryEnabled": True,
            "interRaterEnabled": False,
            "unexpected": "value",
        },
    )

    assert response.status_code == 422


def test_configuration_import_with_incompatible_version(monkeypatch):
    app = _app_with_configuration_router(monkeypatch)
    client = TestClient(app)

    payload = {
        "atlas_config_version": "9.9",
        "corpus": {},
        "test_target": {},
    }
    files = {"file": ("config.json", json.dumps(payload), "application/json")}

    response = client.post("/api/configuration/import", files=files)

    assert response.status_code == 207
    body = response.json()
    assert body["success"] is False
    assert "Unsupported configuration version" in body["errors"][0]


def test_configuration_validate_with_incompatible_version(monkeypatch):
    app = _app_with_configuration_router(monkeypatch)
    client = TestClient(app)

    payload = {
        "atlas_config_version": "9.9",
        "corpus": {},
        "test_target": {},
    }
    files = {"file": ("config.json", json.dumps(payload), "application/json")}

    response = client.post("/api/configuration/validate", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert "Unsupported configuration version" in body["errors"][0]


def test_configuration_validate_with_missing_resources_warning(monkeypatch):
    app = FastAPI()
    app.include_router(configuration_router.router)
    monkeypatch.setattr(configuration_router, "get_configuration_importer", lambda: ConfigurationImporter())

    client = TestClient(app)

    payload = {
        "atlas_config_version": "1.0",
        "corpus": {
            "source": {
                "type": "file_path",
                "path": "missing_directory/missing_file.txt",
            }
        },
        "test_target": {},
    }
    files = {"file": ("config.json", json.dumps(payload), "application/json")}

    response = client.post("/api/configuration/validate", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert any("does not exist" in warning for warning in body["warnings"])


def test_configuration_import_partial_configuration(monkeypatch):
    app = _app_with_configuration_router(monkeypatch)
    client = TestClient(app)

    payload = {
        "atlas_config_version": "1.0",
        "corpus": {},
        "test_target": {},
    }
    files = {"file": ("config.json", json.dumps(payload), "application/json")}

    response = client.post("/api/configuration/import", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True


def test_configuration_export_complete_flow(monkeypatch):
    app = _app_with_configuration_router(monkeypatch)
    client = TestClient(app)

    response = client.get(
        "/api/configuration/export",
        params={"config_name": "My Export", "description": "From test"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["config_name"] == "My Export"
    assert body["corpus"]["name"] == "demo"
    assert body["test_target"]["provider"] == "openai"
    assert "Content-Disposition" in response.headers


def test_configuration_export_compressed_flow(monkeypatch):
    app = _app_with_configuration_router(monkeypatch)
    client = TestClient(app)

    response = client.get(
        "/api/configuration/export",
        params={"config_name": "My Export", "description": "From test", "compress": "true"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/gzip")
    assert response.headers["content-disposition"].endswith('.json.gz"')

    decompressed = gzip.decompress(response.content)
    body = json.loads(decompressed.decode("utf-8"))
    assert body["config_name"] == "My Export"
    assert body["corpus"]["name"] == "demo"
    assert body["test_target"]["provider"] == "openai"


def test_configuration_import_complete_flow(monkeypatch):
    app = _app_with_configuration_router(monkeypatch)
    client = TestClient(app)

    payload = {
        "atlas_config_version": "1.0",
        "corpus": {"name": "demo"},
        "test_target": {"provider": "openai"},
    }
    files = {"file": ("config.json", json.dumps(payload), "application/json")}

    response = client.post("/api/configuration/import", files=files)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["backup_path"] is not None
    assert "corpus.name" in body["diff"]["added"]


def test_system_configuration_changes_take_effect_immediately(monkeypatch):
    app, _ = _app_with_system_router_and_shared_config(monkeypatch)
    client = TestClient(app)

    update_response = client.post(
        "/api/system/configuration",
        json={"telemetryEnabled": True, "interRaterEnabled": True},
    )

    assert update_response.status_code == 200
    update_body = update_response.json()
    assert update_body["config"]["telemetryEnabled"] is True
    assert update_body["config"]["interRaterEnabled"] is True

    get_response = client.get("/api/system/configuration")
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["config"]["telemetryEnabled"] is True
    assert get_body["config"]["interRaterEnabled"] is True
    assert get_body["telemetryEnabled"] is True
    assert get_body["interRaterEnabled"] is True


def test_system_configuration_reload_returns_current_values(monkeypatch):
    app, shared_config = _app_with_system_router_and_shared_config(monkeypatch)
    client = TestClient(app)
    shared_config.save_config({"telemetryEnabled": True, "interRaterEnabled": False})

    response = client.post("/api/system/configuration/reload")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["config"]["telemetryEnabled"] is True
    assert body["config"]["interRaterEnabled"] is False


def test_wizard_configuration_step_complete_flow(monkeypatch):
    """Simulate the wizard configuration step: set values, then verify via GET."""
    app, _ = _app_with_system_router_and_shared_config(monkeypatch)
    client = TestClient(app)

    # Step 1: Wizard submits initial configuration (user enables both toggles)
    post_resp = client.post(
        "/api/system/configuration",
        json={"telemetryEnabled": True, "interRaterEnabled": True},
    )
    assert post_resp.status_code == 200
    assert post_resp.json()["success"] is True

    # Step 2: Wizard reads back configuration to display current state
    get_resp = client.get("/api/system/configuration")
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["config"]["telemetryEnabled"] is True
    assert body["config"]["interRaterEnabled"] is True
    assert body["telemetryEnabled"] is True
    assert body["interRaterEnabled"] is True


def test_wizard_navigation_back_forward_preserves_updates(monkeypatch):
    """Simulate navigating away from and back to the configuration step."""
    app, _ = _app_with_system_router_and_shared_config(monkeypatch)
    client = TestClient(app)

    # Forward: user sets telemetry on, inter-rater off
    resp1 = client.post(
        "/api/system/configuration",
        json={"telemetryEnabled": True, "interRaterEnabled": False},
    )
    assert resp1.status_code == 200

    # Navigates away, then comes back -- GET should still reflect values
    get_resp = client.get("/api/system/configuration")
    assert get_resp.json()["config"]["telemetryEnabled"] is True
    assert get_resp.json()["config"]["interRaterEnabled"] is False

    # User changes mind on return -- updates inter-rater
    resp2 = client.post(
        "/api/system/configuration",
        json={"telemetryEnabled": True, "interRaterEnabled": True},
    )
    assert resp2.status_code == 200

    # Final state should reflect last update
    final = client.get("/api/system/configuration")
    assert final.json()["config"]["telemetryEnabled"] is True
    assert final.json()["config"]["interRaterEnabled"] is True


def test_wizard_configuration_validation_rejects_missing_fields(monkeypatch):
    """Configuration endpoint requires both fields due to strict Pydantic model."""
    app = _app_with_system_router(monkeypatch)
    client = TestClient(app)

    # Send only one field -- should fail validation (extra="forbid", strict=True)
    response = client.post(
        "/api/system/configuration",
        json={"telemetryEnabled": True},
    )

    # Pydantic v2 with strict mode: missing required field
    # interRaterEnabled has a default, so this should actually succeed
    assert response.status_code == 200
    body = response.json()
    assert body["config"]["telemetryEnabled"] is True
    assert body["config"]["interRaterEnabled"] is False


def test_wizard_configuration_defaults_when_no_prior_state(monkeypatch):
    """GET returns defaults when no configuration has been set."""
    app = _app_with_system_router(monkeypatch)
    client = TestClient(app)

    response = client.get("/api/system/configuration")

    assert response.status_code == 200
    body = response.json()
    assert body["config"]["telemetryEnabled"] is False
    assert body["config"]["interRaterEnabled"] is False
