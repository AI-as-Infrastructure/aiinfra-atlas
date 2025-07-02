"""
Debug script to investigate sync endpoint 500 errors
This will help understand the exact error and compare with streaming behavior
"""

import json
import os
import requests
import urllib3
from utils.data_generators import data_generator

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def test_endpoints():
    # Load environment
    base_url = os.getenv('VITE_API_URL', 'https://192.168.20.17')
    
    # Generate test data
    session_id = data_generator.generate_session_id()
    question_data = data_generator.generate_ask_request(session_id)
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Origin": base_url,
        "Referer": f"{base_url}/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0",
        "Cache-Control": "no-cache",
        "X-Trace-Id": data_generator.generate_qa_id(),
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin"
    }
    
    print("=" * 80)
    print("🔍 DEBUGGING SYNC ENDPOINT ISSUE")
    print("=" * 80)
    
    print(f"\n📍 Base URL: {base_url}")
    print(f"📋 Request payload: {json.dumps(question_data, indent=2)}")
    print(f"📨 Headers: {json.dumps(headers, indent=2)}")
    
    # Test 1: Streaming endpoint (known working)
    print(f"\n" + "=" * 50)
    print("✅ TESTING STREAMING ENDPOINT (WORKING)")
    print("=" * 50)
    
    streaming_data = question_data.copy()
    streaming_data['stream'] = True
    
    try:
        response = requests.post(
            f"{base_url}/api/ask/stream",
            json=streaming_data,
            headers=headers,
            verify=False,
            stream=True,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📨 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ Streaming endpoint: SUCCESS")
            # Read first few lines of stream
            lines_read = 0
            for line in response.iter_lines():
                if line and lines_read < 3:
                    print(f"📄 Stream line {lines_read + 1}: {line.decode()[:100]}...")
                    lines_read += 1
                elif lines_read >= 3:
                    break
        else:
            print(f"❌ Streaming endpoint: FAILED - {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Streaming endpoint: ERROR - {e}")
    
    # Test 2: Sync endpoint (failing)
    print(f"\n" + "=" * 50)
    print("❌ TESTING SYNC ENDPOINT (FAILING)")
    print("=" * 50)
    
    sync_data = question_data.copy()
    sync_data['stream'] = False
    
    try:
        response = requests.post(
            f"{base_url}/api/ask",
            json=sync_data,
            headers=headers,
            verify=False,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📨 Response Headers: {dict(response.headers)}")
        print(f"📄 Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Sync endpoint: SUCCESS")
            try:
                data = response.json()
                print(f"📋 Response JSON: {json.dumps(data, indent=2)}")
            except:
                print("📄 Response is not JSON")
        else:
            print(f"❌ Sync endpoint: FAILED")
            print(f"🔍 Full error response: {response.text}")
            
    except Exception as e:
        print(f"❌ Sync endpoint: ERROR - {e}")
    
    # Test 3: Minimal sync test
    print(f"\n" + "=" * 50)
    print("🧪 TESTING MINIMAL SYNC PAYLOAD")
    print("=" * 50)
    
    minimal_data = {
        "question": "Test question",
        "session_id": session_id,
        "stream": False
    }
    
    minimal_headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/ask",
            json=minimal_data,
            headers=minimal_headers,
            verify=False,
            timeout=30
        )
        
        print(f"📊 Status Code: {response.status_code}")
        print(f"📄 Response Body: {response.text}")
        
        if response.status_code == 200:
            print("✅ Minimal sync: SUCCESS - Issue is with complex payload/headers")
        else:
            print(f"❌ Minimal sync: FAILED - Issue is fundamental to sync endpoint")
            
    except Exception as e:
        print(f"❌ Minimal sync: ERROR - {e}")
    
    # Test 4: Check if sync endpoint exists
    print(f"\n" + "=" * 50)
    print("🔍 TESTING ENDPOINT AVAILABILITY")
    print("=" * 50)
    
    try:
        # OPTIONS request to check endpoint
        response = requests.options(
            f"{base_url}/api/ask",
            verify=False,
            timeout=10
        )
        print(f"📊 OPTIONS /api/ask Status: {response.status_code}")
        print(f"📨 OPTIONS Headers: {dict(response.headers)}")
        
        # Check streaming endpoint for comparison
        response = requests.options(
            f"{base_url}/api/ask/stream", 
            verify=False,
            timeout=10
        )
        print(f"📊 OPTIONS /api/ask/stream Status: {response.status_code}")
        print(f"📨 OPTIONS Headers: {dict(response.headers)}")
        
    except Exception as e:
        print(f"❌ OPTIONS requests: ERROR - {e}")

if __name__ == "__main__":
    # Source environment variables
    import subprocess
    
    try:
        # Load staging environment
        result = subprocess.run(
            ["bash", "-c", "source ../config/.env.staging && env"],
            capture_output=True,
            text=True,
            cwd="/home/jamessmithies/Desktop/tech-local/aiinfra-atlas/load_tests"
        )
        
        # Parse environment variables
        for line in result.stdout.split('\n'):
            if '=' in line and 'VITE_' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                
        test_endpoints()
        
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        print("Using default values...")
        test_endpoints()