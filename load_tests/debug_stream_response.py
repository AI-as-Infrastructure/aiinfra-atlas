"""
Debug script to examine the actual streaming response format
to understand when responseComplete appears
"""

import json
import os
import requests
import urllib3
from utils.data_generators import data_generator

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def debug_streaming_response():
    # Load environment
    base_url = os.getenv('VITE_API_URL', 'https://192.168.20.17')
    
    # Generate test data
    session_id = data_generator.generate_session_id()
    question_data = data_generator.generate_ask_request(session_id)
    question_data['stream'] = True
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "X-Trace-Id": data_generator.generate_qa_id(),
    }
    
    print("🔍 DEBUGGING STREAMING RESPONSE FORMAT")
    print("=" * 80)
    print(f"Question: {question_data['question']}")
    print(f"QA ID: {question_data['qa_id']}")
    print(f"Session ID: {question_data['session_id']}")
    print()
    
    try:
        response = requests.post(
            f"{base_url}/api/ask/stream",
            json=question_data,
            headers=headers,
            verify=False,
            stream=True,
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Request failed: {response.status_code}")
            return
        
        print("✅ Starting to process streaming response...")
        print()
        
        line_count = 0
        qa_id_found = None
        response_complete_found = False
        
        for line in response.iter_lines():
            if line:
                line_count += 1
                line_decoded = line.decode()
                
                print(f"📄 Line {line_count}: {line_decoded[:100]}...")
                
                try:
                    if line.startswith(b"data: "):
                        data = json.loads(line[6:])
                        
                        # Check for qaId
                        if "qaId" in data and not qa_id_found:
                            qa_id_found = data["qaId"]
                            print(f"🆔 Found qaId: {qa_id_found}")
                        
                        # Check for responseComplete
                        if data.get("responseComplete") is True:
                            response_complete_found = True
                            print(f"✅ Found responseComplete: True at line {line_count}")
                            print(f"📋 Full completion data: {json.dumps(data, indent=2)}")
                            break
                        
                        # Show some key fields for first few lines
                        if line_count <= 5:
                            print(f"   🔍 Keys in data: {list(data.keys())}")
                            if "chunk" in data:
                                chunk = data["chunk"]
                                print(f"   📦 Chunk type: {chunk.get('type')}")
                                if chunk.get("type") == "content":
                                    print(f"   📝 Content preview: {chunk.get('content', '')[:50]}...")
                        
                except json.JSONDecodeError as e:
                    if line_count <= 5:  # Only show decode errors for first few lines
                        print(f"   ⚠️  JSON decode error: {e}")
                
                # Stop after reasonable number of lines to avoid flooding
                if line_count > 100:
                    print(f"🛑 Stopping after {line_count} lines to avoid flooding")
                    break
        
        print()
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total lines processed: {line_count}")
        print(f"QA ID found: {qa_id_found}")
        print(f"Response complete found: {response_complete_found}")
        
        if not response_complete_found:
            print("❌ responseComplete: true was NOT found!")
            print("   This means feedback will never be triggered in load test")
        else:
            print("✅ responseComplete: true was found")
            print("   Feedback should be triggered correctly")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # Source environment variables
    import subprocess
    
    try:
        result = subprocess.run(
            ["bash", "-c", "source ../config/.env.staging && env"],
            capture_output=True,
            text=True,
            cwd="/home/jamessmithies/Desktop/tech-local/aiinfra-atlas/load_tests"
        )
        
        for line in result.stdout.split('\n'):
            if '=' in line and 'VITE_' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value
                
        debug_streaming_response()
        
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        debug_streaming_response()