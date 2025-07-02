"""
Focused streaming-only load test for ATLAS application.
This test only uses endpoints that are confirmed working to demonstrate 
realistic user behavior and performance metrics.
"""

import json
import time
import random
import os
from locust import HttpUser, task, between, events
from locust.exception import StopUser
from utils.data_generators import data_generator
from utils.metrics import metrics_collector
from utils.evaluator import LoadTestEvaluator
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class StreamingOnlyUser(HttpUser):
    """Load test user focused only on streaming endpoints that work"""
    
    wait_time = between(3, 8)  # Realistic user think time
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False
    
    def on_start(self):
        """Initialize user session"""
        self.session_id = data_generator.generate_session_id()
        
        # Test connectivity
        try:
            response = self.client.get("/api/health")
            if response.status_code != 200:
                print(f"❌ Health check failed: {response.status_code}")
                raise StopUser()
        except Exception as e:
            print(f"❌ Failed to connect to API: {e}")
            raise StopUser()
    
    @task(100)
    def ask_streaming_question(self):
        """Submit streaming question - the main working endpoint"""
        question_data = data_generator.generate_ask_request(self.session_id)
        question_data['stream'] = True
        
        base_host = os.getenv('VITE_API_URL', self.environment.host)
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Origin": base_host,
            "Referer": f"{base_host}/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "Cache-Control": "no-cache",
            "X-Trace-Id": data_generator.generate_qa_id(),
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        
        start_time = time.time()
        first_token_time = None
        token_count = 0
        
        try:
            with self.client.post(
                "/api/ask/stream",
                json=question_data,
                headers=headers,
                stream=True,
                catch_response=True
            ) as response:
                
                if response.status_code != 200:
                    response.failure(f"HTTP {response.status_code}")
                    metrics_collector.record_request("ask_stream", time.time() - start_time, response.status_code, f"HTTP {response.status_code}")
                    return
                
                # Process streaming response
                for line in response.iter_lines():
                    if line:
                        if first_token_time is None:
                            first_token_time = time.time() - start_time
                        
                        try:
                            if line.startswith(b"data: "):
                                data = json.loads(line[6:])
                                if data.get("type") == "content":
                                    token_count += len(data.get("content", "").split())
                        except json.JSONDecodeError:
                            continue
                
                total_time = time.time() - start_time
                
                # Record metrics
                metrics_collector.record_request("ask_stream", total_time, response.status_code)
                if first_token_time:
                    metrics_collector.record_streaming_metrics(
                        self.session_id, first_token_time, total_time, token_count
                    )
                
                response.success()
                
        except Exception as e:
            total_time = time.time() - start_time
            metrics_collector.record_request("ask_stream", total_time, 0, str(e))
            self.environment.events.request_failure.fire(
                request_type="POST",
                name="/api/ask/stream",
                response_time=total_time * 1000,
                exception=e
            )

# Event handlers for reporting
@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Generate evaluation report when test stops"""
    if hasattr(environment, 'stats'):
        print(f"\n🏁 Test completed. Generating evaluation report...")
        
        # Load configuration
        config_file = os.getenv('LOAD_TEST_CONFIG', 'staging')
        
        try:
            evaluator = LoadTestEvaluator(config_file)
            
            # Get metrics data
            metrics_data = metrics_collector.get_metrics()
            
            # Run evaluation
            evaluation_results = evaluator.evaluate(metrics_data)
            
            # Generate and save report
            report_path = evaluator.generate_report(evaluation_results, metrics_data)
            
            print(f"📊 Evaluation report saved to: {report_path}")
            
            # Print summary
            overall_result = evaluation_results.get('summary', {}).get('overall_status', 'UNKNOWN')
            
            if overall_result == 'PASS':
                print("✅ OVERALL RESULT: PASSED")
                print("   🎉 All performance criteria met!")
                exit(0)
            elif overall_result == 'BORDERLINE':
                print("⚠️  OVERALL RESULT: BORDERLINE")
                print("   🔍 Some metrics need attention but system is functional")
                exit(0)
            else:
                print("❌ OVERALL RESULT: FAILED")
                for rec in evaluation_results.get('summary', {}).get('recommendations', []):
                    print(f"   {rec}")
                print("🚨 Load test FAILED - exiting with error code")
                exit(1)
                
        except Exception as e:
            print(f"❌ Error generating evaluation: {e}")
            exit(1)

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Handle all requests (success and failure)"""
    # This replaces the deprecated events.request_success and events.request_failure
    pass