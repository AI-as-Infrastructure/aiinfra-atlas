"""
Pytest configuration and shared fixtures for ATLAS tests

This file provides shared fixtures and configuration for all tests.
"""

import pytest
import os
import sys
from pathlib import Path

# Add backend directory to Python path for imports
backend_path = Path(__file__).parent.parent / 'backend'
sys.path.insert(0, str(backend_path))


@pytest.fixture
def mock_phoenix_env(monkeypatch):
    """Fixture to set up mock Phoenix environment variables"""
    monkeypatch.setenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://test.phoenix.arize.com')
    monkeypatch.setenv('PHOENIX_API_KEY', 'test_api_key')
    monkeypatch.setenv('PHOENIX_PROJECT_NAME', 'test-project')


@pytest.fixture
def mock_inter_rater_manifest(tmp_path, monkeypatch):
    """Fixture to set up inter-rater configuration via manifest file"""
    import json

    # Create a mock corpus directory with manifest
    corpus_dir = tmp_path / "backend" / "corpus"
    corpus_dir.mkdir(parents=True)

    manifest = {
        "metadata": {
            "name": "test-corpus",
            "display_name": "Test Corpus"
        },
        "inter_rater": {
            "enabled": True,
            "max_ratings": 3,
            "sessions_per_user": 5
        }
    }

    manifest_path = corpus_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))

    # Change to temp directory so the service finds the manifest
    monkeypatch.chdir(tmp_path)

    return manifest_path


@pytest.fixture
def sample_feedback_data():
    """Fixture providing sample feedback data"""
    return {
        'session_id': 'test_session_123',
        'qa_id': 'test_qa_456',
        'relevance': 4,
        'factual_accuracy': 5,
        'clarity': 4,
        'feedback_text': 'Test feedback comment'
    }


@pytest.fixture
def sample_inter_rater_feedback():
    """Fixture providing sample inter-rater feedback data"""
    return {
        'session_id': 'test_session_123',
        'qa_id': 'test_qa_456',
        'is_inter_rater': True,
        'original_span_id': 'original_span_789',
        'rater_id': 'test_rater_abc',
        'relevance': 3,
        'factual_accuracy': 4,
        'clarity': 3,
        'feedback_text': 'Inter-rater feedback comment'
    }


@pytest.fixture
def mock_phoenix_annotations_response():
    """Fixture providing mock Phoenix annotations API response"""
    def _make_response(count=0, rater_ids=None):
        """
        Generate mock annotations response

        Args:
            count: Number of inter-rater annotations to include
            rater_ids: List of rater IDs, defaults to ['user_1', 'user_2', ...]
        """
        if rater_ids is None:
            rater_ids = [f'user_{i+1}' for i in range(count)]

        annotations = []
        for rater_id in rater_ids[:count]:
            annotations.append({
                'name': '[inter-rating] Relevance Rating',
                'metadata': {
                    'is_inter_rater': True,
                    'rater_id': rater_id
                },
                'result': {
                    'label': 'relevance',
                    'score': 4
                }
            })

        return {
            'data': annotations
        }

    return _make_response


# Configure pytest markers
def pytest_configure(config):
    """Register custom markers"""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests requiring external services"
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests as unit tests (default)"
    )
