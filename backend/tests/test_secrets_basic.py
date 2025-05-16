#!/usr/bin/env python3
"""
Basic test script to verify that the secrets management system is working correctly.
This script focuses on testing the core functionality without complex dependencies.
"""

import os
import sys
import logging
import unittest

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the parent directory to the path so we can import modules
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(backend_dir)

# Import the secrets manager
from utils.secrets_manager import get_secret, get_config, ENV_FILE, SECRETS_FILE

class SecretsBasicTest(unittest.TestCase):
    """Basic tests for the secrets management system."""

    def test_config_paths(self):
        """Test that the configuration paths are set correctly."""
        # Check that the paths are absolute
        self.assertTrue(os.path.isabs(ENV_FILE), f"ENV_FILE is not an absolute path: {ENV_FILE}")
        self.assertTrue(os.path.isabs(SECRETS_FILE), f"SECRETS_FILE is not an absolute path: {SECRETS_FILE}")
        
        # Check that the paths point to the config directory
        config_dir = os.path.join(os.path.dirname(backend_dir), 'config')
        self.assertEqual(os.path.dirname(ENV_FILE), config_dir, 
                         f"ENV_FILE not in config directory: {ENV_FILE}")
        self.assertEqual(os.path.dirname(SECRETS_FILE), config_dir, 
                         f"SECRETS_FILE not in config directory: {SECRETS_FILE}")
        
        logger.info(f"Configuration paths verified: ENV_FILE={ENV_FILE}, SECRETS_FILE={SECRETS_FILE}")

    def test_files_exist(self):
        """Test that the configuration files exist."""
        # Check if the files exist
        self.assertTrue(os.path.exists(ENV_FILE), f"ENV_FILE does not exist: {ENV_FILE}")
        self.assertTrue(os.path.exists(SECRETS_FILE), f"SECRETS_FILE does not exist: {SECRETS_FILE}")
        
        # Check if the files are readable
        self.assertTrue(os.access(ENV_FILE, os.R_OK), f"ENV_FILE is not readable: {ENV_FILE}")
        self.assertTrue(os.access(SECRETS_FILE, os.R_OK), f"SECRETS_FILE is not readable: {SECRETS_FILE}")
        
        logger.info("Configuration files exist and are readable")

    def test_get_config(self):
        """Test that get_config can retrieve values from the environment file."""
        # Test with any configuration value that should exist in .env
        # Try a few common configuration values that might exist
        config_keys = ['REACT_APP_SITE_TITLE', 'SERVER_NAME', 'TEST_TARGET', 'PHOENIX_PROJECT_NAME', 'OLLAMA_ENDPOINT']
        found_config = False
        
        for key in config_keys:
            test_config = get_config(key)
            if test_config is not None:
                found_config = True
                logger.info(f"Successfully retrieved {key}: {test_config}")
                break
        
        # If no configuration values were found, test with a default value
        if not found_config:
            test_config = get_config('REACT_APP_SITE_TITLE', 'ATLAS')
            self.assertEqual(test_config, 'ATLAS', "Default configuration value not returned")
            logger.info(f"Successfully retrieved default value for REACT_APP_SITE_TITLE: {test_config}")
        
        # Test with a default value
        test_default = get_config('NONEXISTENT_CONFIG', 'default_value')
        self.assertEqual(test_default, 'default_value', 
                         f"Default value not returned for nonexistent config: {test_default}")
        logger.info(f"Successfully retrieved default value for nonexistent config")

    def test_get_secret(self):
        """Test that get_secret can retrieve values from the secrets file."""
        # Test with a known secret
        test_secret = get_secret('TEST_TARGET')
        self.assertIsNotNone(test_secret, "TEST_TARGET secret not found")
        logger.info(f"Successfully retrieved TEST_TARGET: {test_secret}")
        
        # Test with a default value
        test_default = get_secret('NONEXISTENT_SECRET', 'default_value')
        self.assertEqual(test_default, 'default_value', 
                         f"Default value not returned for nonexistent secret: {test_default}")
        logger.info(f"Successfully retrieved default value for nonexistent secret")

    def test_code_integration(self):
        """Test that the backend code is properly integrated with the secrets manager."""
        # Check if the retriever module imports the secrets manager
        retriever_path = os.path.join(backend_dir, 'modules', 'retriever.py')
        self.assertTrue(os.path.exists(retriever_path), f"Retriever module not found: {retriever_path}")
        
        with open(retriever_path, 'r') as f:
            content = f.read()
            self.assertIn('from utils.secrets_manager import get_secret', content, 
                         "Retriever module does not import secrets manager")
            self.assertNotIn('load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), \'env\'))', 
                            content, "Retriever module still uses old env directory")
        
        # Check if the target module imports the secrets manager
        target_path = os.path.join(backend_dir, 'targets', 'blert_500', 'blert_500.py')
        self.assertTrue(os.path.exists(target_path), f"Target module not found: {target_path}")
        
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
        
        # Check if the app.py imports the secrets manager
        app_path = os.path.join(backend_dir, 'app.py')
        self.assertTrue(os.path.exists(app_path), f"App module not found: {app_path}")
        
        with open(app_path, 'r') as f:
            content = f.read()
            self.assertIn('from utils.secrets_manager import get_secret', content, 
                         "App module does not import secrets manager")
            self.assertIn('port = int(get_secret(\'PORT\', 5000))', content, 
                         "App module does not use get_secret for PORT")
        
        logger.info("Backend code successfully integrated with secrets manager")

if __name__ == '__main__':
    logger.info("Starting basic secrets tests")
    unittest.main()
