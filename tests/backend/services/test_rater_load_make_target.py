"""Contract tests for the production rater-load make target."""

import subprocess
from pathlib import Path


def test_rater_load_is_self_contained_and_defaults_to_production():
    project_root = Path(__file__).resolve().parents[3]

    result = subprocess.run(
        ["make", "-n", "rater-load"],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    )

    command = result.stdout
    assert 'ENV_FILE="${ENV_FILE:-config/.env.production}"' in command
    assert 'DEPS_DIR="${RATER_LOAD_DEPS_DIR:-.rater-load-deps}"' in command
    assert ".complete-pytest-8.3.5-pytest-asyncio-0.25.2" in command
    assert '--target "$DEPS_DIR" pytest==8.3.5 pytest-asyncio==0.25.2' in command
    assert "pytest.__version__ == \"8.3.5\"" in command
    assert "pytest_asyncio.__version__ == \"0.25.2\"" in command
    assert "-perm /022" in command
    assert 'PYTHONPATH="$PYTHONPATH" RATER_LOAD=1' in command
    assert "requirements-test.txt" not in command
    assert "/tmp/atlas-rater-load-deps" not in command
