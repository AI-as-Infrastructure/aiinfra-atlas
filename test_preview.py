#!/usr/bin/env python3
"""Test script for the corpus wizard preview endpoint."""

import requests
import json

# Test the preview endpoint
url = "http://localhost:8000/api/corpus-wizard/preview"
payload = {
    "source": {
        "type": "local",
        "location": "backend/corpus/sources",
        "file_extensions": ".txt",
        "include_subdirectories": True,
        "extract_inline_urls": True,
        "date_pattern": "custom",
        "custom_date_pattern": r"(\d{1,2}(?:st|nd|rd|th)\s+\w+,\s*\d{4})"
    },
    "metadata": {
        "name": "Test Corpus",
        "description": "Testing preview"
    }
}

print("Testing preview endpoint...")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload)
    print(f"\nStatus Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Total Documents: {data.get('total_documents')}")
        print(f"Total Size: {data.get('total_size')} bytes")
        print(f"Documents with URLs: {data.get('docs_with_urls')}")
        print(f"Documents with Dates: {data.get('docs_with_dates')}")
        print(f"Number of Filters: {len(data.get('filters', []))}")

        if data.get('filters'):
            print("\nDiscovered Filters:")
            for f in data['filters'][:5]:  # Show first 5
                print(f"  - {f['label']}: {f['document_count']} docs")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Connection Error: {e}")
    print("\nMake sure the backend is running with: make dev")