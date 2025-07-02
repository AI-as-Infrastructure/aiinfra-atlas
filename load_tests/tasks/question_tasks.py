import json
import time
import random
import os
from locust import HttpUser, task, between
from locust.exception import StopUser
from utils.data_generators import data_generator
from utils.metrics import metrics_collector

class QuestionSubmissionUser(HttpUser):
    """Load test user for question submission endpoints"""
    
    wait_time = between(2, 8)  # Wait 2-8 seconds between tasks
    
    # Disable SSL verification for self-signed certificates
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False
    
    def on_start(self):
        """Initialize user session"""
        self.session_id = data_generator.generate_session_id()
        self.qa_history = []  # Track Q&A pairs for feedback
        
        # Test connectivity (no auth headers needed)
        try:
            response = self.client.get("/api/health")
            if response.status_code != 200:
                print(f"Health check failed: {response.status_code}")
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            raise StopUser()
            
        # Test CORS preflight for ask endpoint
        try:
            base_host = os.getenv('VITE_API_URL', self.environment.host)
            cors_headers = {
                "Origin": base_host,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
            
            response = self.client.options("/api/ask", headers=cors_headers)
            print(f"🔍 DEBUG - CORS preflight status: {response.status_code}")
            print(f"🔍 DEBUG - CORS response headers: {dict(response.headers)}")
            
            # Check if CORS is properly configured
            cors_origin = response.headers.get('Access-Control-Allow-Origin')
            cors_methods = response.headers.get('Access-Control-Allow-Methods')
            print(f"🔍 DEBUG - CORS Allow-Origin: {cors_origin}")
            print(f"🔍 DEBUG - CORS Allow-Methods: {cors_methods}")
            
        except Exception as e:
            print(f"CORS preflight test failed: {e}")
    
    @task(80)
    def ask_streaming_question(self):
        """Submit streaming question - most common user action"""
        question_data = data_generator.generate_ask_request(self.session_id)
        question_data['stream'] = True
        
        # Get the base host from environment
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
            "X-Trace-Id": data_generator.generate_qa_id(),  # Critical missing header!
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        
        # DEBUG: Log the request payload
        print(f"🔍 DEBUG - Streaming request payload: {question_data}")
        print(f"🔍 DEBUG - Headers: {headers}")
        print(f"🔍 DEBUG - URL: /api/ask/stream")
        
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
                
                # DEBUG: Log response details
                print(f"🔍 DEBUG - Response status: {response.status_code}")
                print(f"🔍 DEBUG - Response headers: {dict(response.headers)}")
                
                if response.status_code != 200:
                    print(f"🔍 DEBUG - Error response body: {response.text[:500]}...")
                    response.failure(f"HTTP {response.status_code}")
                    metrics_collector.record_request("ask_stream", time.time() - start_time, response.status_code, f"HTTP {response.status_code}")
                    return
                
                # Process streaming response and track completion
                qa_id = None
                answer_content = ""
                citations = []
                response_complete = False
                
                for line in response.iter_lines():
                    if line:
                        if first_token_time is None:
                            first_token_time = time.time() - start_time
                        
                        try:
                            if line.startswith(b"data: "):
                                data = json.loads(line[6:])
                                
                                # Extract qaId from response
                                if "qaId" in data:
                                    qa_id = data["qaId"]
                                
                                # Check for response completion
                                if data.get("responseComplete") is True:
                                    response_complete = True
                                
                                # Extract content from chunks
                                chunk = data.get("chunk", {})
                                if chunk.get("type") == "content":
                                    content = chunk.get("content", "")
                                    answer_content += content
                                    token_count += len(content.split())
                                elif chunk.get("type") == "citations":
                                    citations = chunk.get("citations", [])
                                    
                        except json.JSONDecodeError:
                            continue
                
                # Store QA data for potential feedback
                if qa_id:
                    qa_data = {
                        "qa_id": qa_id,
                        "session_id": self.session_id,
                        "question": question_data["question"],
                        "answer": answer_content,
                        "citations": citations,
                        "response_complete": response_complete
                    }
                    self.qa_history.append(qa_data)
                
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
    
    @task(3)
    def query_documents(self):
        """Search documents directly"""
        question = data_generator.generate_question()
        corpus_filter = data_generator.generate_corpus_filter()
        
        query_data = {
            "query": question,
            "corpus_filter": corpus_filter,
            "max_results": random.randint(5, 20)
        }
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.post(
            "/api/query",
            json=query_data,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict) and "results" in data:
                        response.success()
                    else:
                        response.failure("Unexpected response format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("query", response_time, response.status_code)
    
    @task(5)
    def get_config(self):
        """Get application configuration"""
        headers = {}
        
        start_time = time.time()
        
        with self.client.get("/api/config", headers=headers, catch_response=True) as response:
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    config = response.json()
                    if isinstance(config, dict):
                        response.success()
                    else:
                        response.failure("Invalid config format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("config", response_time, response.status_code)
    
    @task(3)
    def get_diagnostics(self):
        """Get diagnostic information"""
        headers = {}
        
        start_time = time.time()
        
        with self.client.get("/api/diagnostics", headers=headers, catch_response=True) as response:
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("diagnostics", response_time, response.status_code)
    
    def on_stop(self):
        """Cleanup when user stops"""
        # Export user-specific metrics if needed
        pass