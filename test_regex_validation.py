#!/usr/bin/env python3
"""Test script for regex validation and date extraction."""

import requests
import json

# Test the regex validation endpoint
base_url = "http://localhost:8000/api/corpus-wizard"

# Test cases for regex patterns
test_cases = [
    {
        "name": "Simple date pattern",
        "pattern": r"(\d+\w*\s+\w+,\s*\d+)",
        "test_string": "Friday, 02 August, 1901.txt",
        "expected": "02 August, 1901"
    },
    {
        "name": "Invalid regex - bad curly braces",
        "pattern": r"(\d{1,2}(?:st|nd|rd|th)?\s+\w+,\s*\d{4})",
        "test_string": "6th June, 1901.txt",
        "expected": "6th June, 1901"
    },
    {
        "name": "Basic date pattern",
        "pattern": r"(\d+\s+\w+,\s*\d+)",
        "test_string": "31 December, 1901.txt",
        "expected": "31 December, 1901"
    }
]

print("🧪 Testing Regex Validation Endpoint\n")
print("=" * 50)

for test in test_cases:
    print(f"\nTest: {test['name']}")
    print(f"Pattern: {test['pattern']}")
    print(f"Test String: {test['test_string']}")

    try:
        response = requests.post(
            f"{base_url}/validate-regex",
            json={
                "pattern": test["pattern"],
                "test_string": test["test_string"]
            }
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                print(f"✅ Pattern is valid")
                if data.get("matches"):
                    print(f"   Matches found: {data['matches']}")
                    if test.get("expected") in data["matches"]:
                        print(f"   ✓ Expected match found: {test['expected']}")
                    else:
                        print(f"   ⚠️ Expected '{test['expected']}' not found")
            else:
                print(f"❌ Pattern invalid: {data.get('error')}")
        else:
            print(f"❌ Request failed: {response.status_code}")

    except Exception as e:
        print(f"❌ Error: {e}")

print("\n" + "=" * 50)
print("\n📝 Recommended pattern for your filenames:")
print("Pattern: r\"(\\d+\\w*\\s+\\w+,\\s*\\d+)\"")
print("This will match dates like:")
print("  - 02 August, 1901")
print("  - 6th June, 1901")
print("  - 31st December, 1901")