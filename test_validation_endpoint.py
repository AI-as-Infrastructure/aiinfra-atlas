#!/usr/bin/env python3
"""
Quick test script for the validation endpoint.
Run this to test validation without rebuilding the corpus.

Usage:
    # Start backend first:
    ./quick_start_backend.sh

    # Then in another terminal:
    python test_validation_endpoint.py
"""

import requests
import json
from pathlib import Path

def test_validation():
    """Test the validation endpoint directly."""

    # Check if corpus files exist
    tmp_path = Path("backend/corpus/tmp")
    print(f"Checking corpus files in {tmp_path}")

    if tmp_path.exists():
        print("✓ tmp directory exists")
        chroma = tmp_path / "chroma_db"
        manifest = tmp_path / "manifest.json"

        print(f"  - chroma_db: {'✓' if chroma.exists() else '✗'}")
        print(f"  - manifest.json: {'✓' if manifest.exists() else '✗'}")

        if manifest.exists():
            with open(manifest, 'r') as f:
                data = json.load(f)
                print(f"  - Corpus name: {data.get('corpus_name', 'Unknown')}")
                print(f"  - Documents: {data.get('statistics', {}).get('total_documents', 0)}")
    else:
        print("✗ No corpus found in backend/corpus/tmp")
        return

    # Test the validation endpoint
    print("\nTesting validation endpoint...")

    # Use a dummy build_id (doesn't matter since we check files now)
    build_id = "test_build_12345"
    url = f"http://localhost:8000/api/corpus-wizard/validate/{build_id}"

    try:
        response = requests.post(url, timeout=5)
        print(f"Response status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\nValidation Results:")
            print(f"  - Structure valid: {data.get('structure_valid', False)}")
            print(f"  - Metadata valid: {data.get('metadata_valid', False)}")
            print(f"  - Search functional: {data.get('search_functional', False)}")
            print(f"  - All valid: {data.get('all_valid', False)}")

            if data.get('message'):
                print(f"  - Message: {data.get('message')}")

            # Pretty print the full response
            print("\nFull response:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error response: {response.text}")

    except requests.exceptions.Timeout:
        print("✗ Request timed out - endpoint may be hanging")
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to backend - is it running on port 8000?")
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_validation()