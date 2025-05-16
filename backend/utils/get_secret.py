#!/usr/bin/env python3
"""
Command-line utility to get secrets from the secrets manager.
Used by shell scripts to access secrets.

This script looks for secrets in the config/.secrets file in the project root.
"""
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.utils.secrets_manager import get_secret

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: get_secret.py SECRET_NAME [DEFAULT_VALUE]", file=sys.stderr)
        sys.exit(1)
    
    secret_name = sys.argv[1]
    default = sys.argv[2] if len(sys.argv) > 2 else None
    
    value = get_secret(secret_name, default)
    if value is not None:
        print(value)
    else:
        sys.exit(1)
