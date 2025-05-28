#!/usr/bin/env python3
"""
Test script for Phoenix API span annotations
This script tests the Phoenix API directly to validate the correct format for span annotations
"""

import os
import httpx
import json
import logging
import time
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
config_path = os.path.join(os.path.dirname(__file__), "config", ".env.development")
load_dotenv(dotenv_path=config_path)

# Get Phoenix API key from environment
def get_phoenix_api_key():
    """Get Phoenix API key from environment variables"""
    # Try direct API key first
    api_key = os.getenv('PHOENIX_API_KEY')
    if api_key:
        return api_key
        
    # Try parsing from PHOENIX_CLIENT_HEADERS
    client_headers = os.getenv('PHOENIX_CLIENT_HEADERS')
    if client_headers and client_headers.startswith('api_key='):
        return client_headers.replace('api_key=', '').strip('"').strip()
    
    return None

# Configuration
PHOENIX_API_KEY = get_phoenix_api_key()
PHOENIX_ENDPOINT = os.getenv('PHOENIX_COLLECTOR_ENDPOINT', 'https://app.phoenix.arize.com')
ANNOTATION_ENDPOINT = f"{PHOENIX_ENDPOINT}/v1/span_annotations?sync=false"

# Test with a dummy span ID - replace with a real one if you have it
TEST_SPAN_ID = "123456789"

def test_phoenix_annotation_api():
    """Test the Phoenix API with different payload formats"""
    if not PHOENIX_API_KEY:
        logger.error("No Phoenix API key found in environment variables")
        return False
        
    logger.info(f"Using Phoenix API key: {PHOENIX_API_KEY[:5]}...{PHOENIX_API_KEY[-5:] if len(PHOENIX_API_KEY) > 10 else ''}")
    logger.info(f"Testing endpoint: {ANNOTATION_ENDPOINT}")
    
    # Headers for the request
    headers = {
        "Content-Type": "application/json",
        "api_key": PHOENIX_API_KEY
    }
    
    # Generate a unique annotation ID
    annotation_id = f"test_annotation_{int(time.time())}"
    
    # Test payloads with different formats
    test_payloads = [
        # Format 1: Basic annotation
        {
            "data": [
                {
                    "id": f"{annotation_id}_1",
                    "name": "Test Annotation 1",
                    "span_id": TEST_SPAN_ID,
                    "label": "user_feedback",
                    "score": 5,
                    "explanation": "This is a test annotation",
                    "annotator_kind": "HUMAN"
                }
            ]
        },
        
        # Format 2: With metadata
        {
            "data": [
                {
                    "id": f"{annotation_id}_2",
                    "name": "Test Annotation 2",
                    "span_id": TEST_SPAN_ID,
                    "label": "relevance",
                    "score": 4,
                    "explanation": "Test with metadata",
                    "annotator_kind": "HUMAN",
                    "metadata": {"qa_id": "test_qa_id"}
                }
            ]
        },
        
        # Format 3: Multiple annotations
        {
            "data": [
                {
                    "id": f"{annotation_id}_3a",
                    "name": "Test Annotation 3a",
                    "span_id": TEST_SPAN_ID,
                    "label": "relevance",
                    "score": 3,
                    "explanation": None,
                    "annotator_kind": "HUMAN"
                },
                {
                    "id": f"{annotation_id}_3b",
                    "name": "Test Annotation 3b",
                    "span_id": TEST_SPAN_ID,
                    "label": "factual_accuracy",
                    "score": 1,
                    "explanation": None,
                    "annotator_kind": "HUMAN"
                }
            ]
        }
    ]
    
    # Test each payload format
    for i, payload in enumerate(test_payloads):
        logger.info(f"\nTesting payload format {i+1}...")
        logger.info(f"Payload: {json.dumps(payload)}")
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(ANNOTATION_ENDPOINT, json=payload, headers=headers)
                
                logger.info(f"Status code: {response.status_code}")
                logger.info(f"Response: {response.text}")
                
                if response.status_code == 200:
                    logger.info(f"✅ Format {i+1} SUCCESS!")
                else:
                    logger.error(f"❌ Format {i+1} FAILED")
                    
        except Exception as e:
            logger.error(f"Error making request for format {i+1}: {e}")
    
if __name__ == "__main__":
    test_phoenix_annotation_api()
