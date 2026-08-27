# ATLAS Test Suite

Test suite for the ATLAS AI Infrastructure Research Platform.

## Manual testing

This document covers the automated suite. For manual acceptance testing of the
inter-rater workflow against a deployment, see
[inter_rater_manual_testing.md](inter_rater_manual_testing.md).

## Setup

Install test dependencies:

```bash
pip install -r config/requirements-test.txt
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/backend/telemetry/test_inter_rater_annotation_numbering.py
```

### Run specific test
```bash
pytest tests/backend/telemetry/test_inter_rater_annotation_numbering.py::TestInterRaterAnnotationNumbering::test_first_inter_rater_gets_number_one
```

### Run only unit tests (fast)
```bash
pytest -m unit
```

### Run integration tests (requires Phoenix)
```bash
pytest -m integration
```

### Run with coverage report
```bash
pytest --cov=backend --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── backend/
│   ├── telemetry/
│   │   ├── test_inter_rater_numbering_logic.py       # Unit tests (no dependencies)
│   │   └── test_inter_rater_annotation_numbering_integration.py.skip  # Integration tests (requires backend)
│   └── services/
│       └── test_phoenix_client_inter_rater_integration.py.skip        # Integration tests (requires Phoenix)
```

**Note**: Files ending in `.skip` are integration tests that require the full backend setup and are not run by default.

## Test Categories

### Unit Tests
- Fast tests with no external dependencies
- Test pure logic and algorithms
- No backend imports required
- Run by default with `pytest`
- Example: `test_inter_rater_numbering_logic.py`

### Integration Tests
- Require full backend dependencies (pydantic, FastAPI, etc.)
- May require external services (Phoenix instance, Redis, etc.)
- Stored as `.skip` files to prevent accidental execution
- Run manually after setting up backend environment
- Example: `test_inter_rater_annotation_numbering_integration.py.skip`

**Running Integration Tests:**
```bash
# Rename .skip file to .py
mv tests/backend/telemetry/test_inter_rater_annotation_numbering_integration.py.skip \
   tests/backend/telemetry/test_inter_rater_annotation_numbering_integration.py

# Install backend dependencies
pip install -r config/requirements.txt

# Run integration tests
pytest tests/backend/telemetry/test_inter_rater_annotation_numbering_integration.py
```

## Writing Tests

### Test Naming
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test
```python
import pytest
from unittest.mock import Mock, patch

class TestMyFeature:
    """Test suite for my feature"""

    def test_basic_functionality(self):
        """Test basic functionality works"""
        result = my_function()
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_functionality(self):
        """Test async functionality"""
        result = await my_async_function()
        assert result == expected_value
```

### Using Fixtures
```python
def test_with_fixtures(sample_feedback_data, mock_phoenix_env):
    """Test using shared fixtures from conftest.py"""
    # Fixtures provide setup data and environment
    assert sample_feedback_data['relevance'] == 4
```

## OpenSpec Integration

Tests are organized by OpenSpec change proposals when applicable:

- `test_inter_rater_numbering_logic.py` - Unit tests for `openspec/changes/update-inter-rater-annotation-numbering`
  - ✅ All 15 tests passing
  - Tests annotation naming logic
  - Tests count calculation
  - Tests format compliance with OpenSpec requirements
  - No backend dependencies required

## Debugging Tests

### Run with verbose output
```bash
pytest -vv
```

### Run with print statements visible
```bash
pytest -s
```

### Run with debugger on failure
```bash
pytest --pdb
```

### Run last failed tests only
```bash
pytest --lf
```

## CI/CD Integration

Tests should be run in CI/CD pipeline:
```bash
# Install dependencies
pip install -r config/requirements.txt
pip install -r config/requirements-test.txt

# Run unit tests only (fast)
pytest -m unit

# Run all tests including integration (if Phoenix available)
pytest
```

## Common Issues

### Import errors
Make sure you're running pytest from the project root:
```bash
cd /path/to/aiinfra-atlas
pytest
```

### Async test failures
Ensure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

### Phoenix API mock issues
Check that httpx mocks are properly configured. See `conftest.py` for mock fixtures.
