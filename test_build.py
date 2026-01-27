#!/usr/bin/env python3
"""Test script for the corpus wizard build endpoint."""

import requests
import json
import time
import threading
from datetime import datetime

def monitor_progress(build_id):
    """Monitor build progress via SSE."""
    print(f"\n📊 Monitoring progress for build_id: {build_id}\n")
    try:
        # Use requests to get SSE stream
        response = requests.get(
            f"http://localhost:8000/api/corpus-wizard/progress-stream/{build_id}",
            stream=True
        )

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith('data: '):
                    data = json.loads(decoded_line[6:])
                    print(f"Status: {data.get('status')}")
                    print(f"Progress: {data.get('processed_documents', 0)}/{data.get('total_documents', 0)}")
                    print(f"Current: {data.get('current_document', 'N/A')}")
                    print("-" * 40)

                    if data.get('status') in ['completed', 'failed']:
                        if data.get('status') == 'failed':
                            print(f"❌ Build failed: {data.get('error')}")
                        else:
                            print(f"✅ Build completed!")
                        break
    except Exception as e:
        print(f"Error monitoring progress: {e}")

# Test configuration
config = {
    "metadata": {
        "name": "Test Corpus Build",
        "description": "Testing build functionality",
        "workflow_type": "text",
        "created_by": "test_script",
        "copyright": "Test copyright",
        "source_doi": "10.1234/test"
    },
    "source": {
        "type": "local",
        "location": "backend/corpus/sources",
        "file_extensions": ".txt",
        "include_subdirectories": True
    },
    "filters": [
        {
            "id": "all",
            "label": "All Documents",
            "type": "all",
            "pattern": "**/*.txt"
        }
    ],
    "embeddings": {
        "model": "sentence-transformers/all-MiniLM-L6-v2",
        "pooling": "mean",
        "chunk_size": 1000,
        "chunk_overlap": 100,
        "batch_size": 100
    },
    "vector_store": {
        "type": "chromadb",
        "collection_name": "test_corpus_build",
        "persist_directory": "backend/targets/chroma_db"
    },
    "search": {
        "type": "hybrid",
        "k_default": 10,
        "large_single_corpus": 120,
        "large_all_corpus": 80
    }
}

print("🔨 Testing corpus build endpoint...")
print(f"📁 Source location: {config['source']['location']}")
print(f"🤖 Embedding model: {config['embeddings']['model']}")
print()

try:
    # Start the build
    print("📤 Sending build request...")
    response = requests.post(
        "http://localhost:8000/api/corpus-wizard/build",
        json={
            "config": config,
            "mode": "cpu"
        }
    )

    print(f"Response status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        build_id = result.get('build_id')
        print(f"✅ Build started successfully!")
        print(f"🆔 Build ID: {build_id}")

        # Monitor progress in a separate thread
        if build_id:
            monitor_progress(build_id)
    else:
        print(f"❌ Build failed to start")
        print(f"Response: {response.text}")

except requests.exceptions.ConnectionError:
    print("❌ Connection Error: Cannot connect to backend")
    print("Make sure the backend is running with: make dev")
except Exception as e:
    print(f"❌ Unexpected error: {e}")