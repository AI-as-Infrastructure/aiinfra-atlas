#!/usr/bin/env python3
"""
Test script to verify that the secrets management system is properly integrated
with the backend components of the ATLAS application.
"""

import os
import sys
import logging
import unittest
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

# Import the secrets manager
from utils.secrets_manager import get_secret, get_config

class SecretsIntegrationTest(unittest.TestCase):
    """Test the integration of the secrets management system with backend components."""

    def test_secrets_file_exists(self):
        """Test that the secrets file exists and is readable."""
        from utils.secrets_manager import SECRETS_FILE
        self.assertTrue(os.path.exists(SECRETS_FILE), f"Secrets file not found: {SECRETS_FILE}")
        self.assertTrue(os.access(SECRETS_FILE, os.R_OK), f"Secrets file not readable: {SECRETS_FILE}")

    def test_env_file_exists(self):
        """Test that the environment file exists and is readable."""
        from utils.secrets_manager import ENV_FILE
        self.assertTrue(os.path.exists(ENV_FILE), f"Environment file not found: {ENV_FILE}")
        self.assertTrue(os.access(ENV_FILE, os.R_OK), f"Environment file not readable: {ENV_FILE}")

    def test_get_secret(self):
        """Test that get_secret can retrieve values from the secrets file."""
        # Test with a known secret (use a dummy value if testing in CI environment)
        test_secret = get_secret('TEST_TARGET')
        self.assertIsNotNone(test_secret, "TEST_TARGET secret not found")
        logger.info(f"Successfully retrieved TEST_TARGET: {test_secret}")

    def test_get_config(self):
        """Test that get_config can retrieve values from the environment file."""
        # Test with a known configuration value
        test_config = get_config('PROJECT_TITLE')
        self.assertIsNotNone(test_config, "PROJECT_TITLE configuration not found")
        logger.info(f"Successfully retrieved PROJECT_TITLE: {test_config}")

    @patch('utils.secrets_manager.get_secret')
    @patch('importlib.import_module')
    def test_retriever_module_integration(self, mock_import, mock_get_secret):
        """Test that the retriever module correctly uses the secrets manager."""
        # Mock the get_secret function to return test values
        mock_get_secret.side_effect = lambda key, default=None: {
            'TEST_TARGET': 'targets.blert_500.blert_500',
            'REDIS_PASSWORD': 'test_password',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'OLLAMA_ENDPOINT': 'http://localhost:11434',
            'OPENAI_API_KEY': 'test_openai_key',
            'ANTHROPIC_API_KEY': 'test_anthropic_key'
        }.get(key, default)
        
        # Mock the importlib.import_module to return a mock module
        mock_module = MagicMock()
        mock_module.LLM = MagicMock()
        mock_module.EMBEDDING_MODEL = 'test-embedding-model'
        mock_module.DATABASE_URL = 'redis://localhost:6379'
        mock_module.SEARCH_TYPE = 'similarity'
        mock_module.SEARCH_KWARGS = {'k': 3}
        mock_module.INDEX_NAME = 'test-index'
        mock_module.ALGORITHM = 'test-algorithm'
        mock_module.CHUNK_SIZE = 1000
        mock_module.CHUNK_OVERLAP = 200
        mock_module.index_schema = {}
        mock_module.format_docs = lambda x: x
        mock_module.get_retriever = MagicMock(return_value=MagicMock())
        mock_import.return_value = mock_module

        # Import the retriever module (this will use our mocked get_secret)
        try:
            # We need to reload the module to ensure our mocks are used
            import importlib
            if 'modules.retriever' in sys.modules:
                del sys.modules['modules.retriever']
                
            from modules.retriever import test_config_module_name
            self.assertEqual(test_config_module_name, 'targets.blert_500.blert_500')
            logger.info("Retriever module successfully integrated with secrets manager")
        except ImportError as e:
            self.fail(f"Failed to import retriever module: {e}")
        except Exception as e:
            self.fail(f"Error in retriever module: {e}")

    def test_target_module_direct(self):
        """Test the target module directly by importing and patching."""
        # Set up the path to the target module
        target_path = os.path.join(backend_dir, 'targets', 'blert_500', 'blert_500.py')
        self.assertTrue(os.path.exists(target_path), f"Target module not found: {target_path}")
        
        # Check if the target module imports the secrets manager
        with open(target_path, 'r') as f:
            content = f.read()
            self.assertIn('from utils.secrets_manager import get_secret', content, 
                         "Target module does not import secrets manager")
            self.assertIn('REDIS_PASSWORD = get_secret', content, 
                         "Target module does not use get_secret for REDIS_PASSWORD")
            self.assertIn('OPENAI_API_KEY = get_secret', content, 
                         "Target module does not use get_secret for OPENAI_API_KEY")
            self.assertIn('ANTHROPIC_API_KEY = get_secret', content, 
                         "Target module does not use get_secret for ANTHROPIC_API_KEY")
            
        logger.info("Target module successfully integrated with secrets manager")

if __name__ == '__main__':
    logger.info("Starting secrets integration tests")
    unittest.main()
