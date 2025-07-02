"""
Debug WebSocket feedback submission to match how the UI does it
This should result in feedback appearing in Phoenix telemetry
"""

import json
import os
import asyncio
import websockets
import requests
import urllib3
from utils.data_generators import data_generator

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

async def test_websocket_feedback():
    # Load environment
    base_url = os.getenv('VITE_API_URL', 'https://192.168.20.17')
    ws_url = base_url.replace('https://', 'wss://').replace('http://', 'ws://')
    
    # Generate test data
    session_id = data_generator.generate_session_id()
    question_data = data_generator.generate_ask_request(session_id)
    question_data['stream'] = True
    
    print("🔍 TESTING WEBSOCKET FEEDBACK SUBMISSION")
    print("=" * 80)
    print(f"Session ID: {session_id}")
    print(f"Question: {question_data['question']}")
    print(f"QA ID: {question_data['qa_id']}")
    print()
    
    # Step 1: Submit streaming question via HTTP first
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "X-Trace-Id": data_generator.generate_qa_id(),
    }
    
    print("📤 Step 1: Submitting streaming question...")
    
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
            print(f"❌ Streaming request failed: {response.status_code}")
            return
        
        print("✅ Streaming request successful")
        
        # Process response to get completion
        qa_id = None
        answer_content = ""
        response_complete = False
        
        for line in response.iter_lines():
            if line:
                try:
                    if line.startswith(b"data: "):
                        data = json.loads(line[6:])
                        
                        if "qaId" in data:
                            qa_id = data["qaId"]
                        
                        if data.get("responseComplete") is True:
                            response_complete = True
                            answer_content = data.get("responseText", "")
                            print(f"✅ Response completed, QA ID: {qa_id}")
                            break
                            
                except json.JSONDecodeError:
                    continue
        
        if not response_complete or not qa_id:
            print("❌ Failed to get complete response or QA ID")
            return
            
    except Exception as e:
        print(f"❌ Error with streaming request: {e}")
        return
    
    # Step 2: Wait a bit for span registration 
    print("⏳ Waiting 5 seconds for span registration...")
    await asyncio.sleep(5)
    
    # Step 3: Connect to WebSocket and submit feedback
    ws_endpoint = f"{ws_url}/ws/{session_id}"
    print(f"🔌 Step 2: Connecting to WebSocket: {ws_endpoint}")
    
    try:
        # Note: We need to handle SSL verification for WebSocket too
        ssl_context = None
        if ws_url.startswith('wss://'):
            import ssl
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        async with websockets.connect(ws_endpoint, ssl=ssl_context) as websocket:
            print("✅ WebSocket connected")
            
            # Generate feedback data
            feedback_data = data_generator.generate_feedback_data(
                qa_id, session_id, question_data["question"], answer_content
            )
            
            # Format for WebSocket submission (matching the backend expectation)
            ws_message = {
                "type": "feedback",
                "data": {
                    "qa_id": qa_id,
                    "feedback": feedback_data
                }
            }
            
            print(f"📤 Submitting feedback via WebSocket...")
            print(f"🔍 Feedback data preview: {json.dumps(feedback_data, indent=2)[:500]}...")
            
            # Send feedback
            await websocket.send(json.dumps(ws_message))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                print(f"📨 WebSocket response: {response_data}")
                
                if response_data.get("status") == "success":
                    print("✅ Feedback submitted successfully via WebSocket!")
                    print("🎯 This should appear in Phoenix telemetry as span annotations")
                else:
                    print(f"❌ Feedback submission failed: {response_data}")
                    
            except asyncio.TimeoutError:
                print("⏳ No response received within timeout (may still be successful)")
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()

def main():
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
                
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
    
    # Run the async test
    asyncio.run(test_websocket_feedback())

if __name__ == "__main__":
    main()