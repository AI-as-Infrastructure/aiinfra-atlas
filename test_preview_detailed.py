#!/usr/bin/env python3
"""Test script for the corpus wizard preview endpoint with detailed output."""

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

print("Testing preview endpoint with date extraction...")

try:
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Total Documents: {data.get('total_documents')}")
        print(f"✓ Documents with URLs: {data.get('docs_with_urls')}")
        print(f"✓ Documents with Dates: {data.get('docs_with_dates')}")

        if data.get('samples'):
            print("\n📄 Sample Documents with Extracted Metadata:")
            for i, sample in enumerate(data['samples'], 1):
                print(f"\n{i}. {sample['filename']}")
                if sample.get('extracted_metadata'):
                    if sample['extracted_metadata'].get('url'):
                        print(f"   URL: {sample['extracted_metadata']['url']}")
                    if sample['extracted_metadata'].get('date'):
                        print(f"   Date: {sample['extracted_metadata']['date']}")

        if data.get('warnings'):
            print("\n⚠️ Warnings:")
            for warning in data['warnings']:
                print(f"  - {warning}")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Connection Error: {e}")
    print("\nMake sure the backend is running with: make dev")