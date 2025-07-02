import json
import time
import random
import redis
from locust import HttpUser, task, between
from locust.exception import StopUser
from utils.data_generators import data_generator
from utils.metrics import metrics_collector
import os

class AsyncProcessingUser(HttpUser):
    """Load test user for async processing endpoints and Redis queue"""
    
    wait_time = between(3, 12)  # Longer wait time for async operations
    
    # Disable SSL verification for self-signed certificates
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False
    
    def on_start(self):
        """Initialize async processing user"""
        self.session_id = data_generator.generate_session_id()
        self.pending_requests = {}  # Track submitted async requests
        
        # Setup Redis connection for queue monitoring
        self.setup_redis_connection()
        
        # Test connectivity
        try:
            response = self.client.get("/api/health")
            if response.status_code != 200:
                print(f"Health check failed: {response.status_code}")
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            raise StopUser()
    
    def setup_redis_connection(self):
        """Setup Redis connection for queue monitoring"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_password = os.getenv('REDIS_PASSWORD', 'atlas_development')
            
            self.redis_client = redis.from_url(
                redis_url,
                password=redis_password,
                decode_responses=True
            )
            
            # Test Redis connection
            self.redis_client.ping()
            
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis_client = None
    
    @task(50)
    def submit_async_request(self):
        """Submit async processing request"""
        async_data = data_generator.generate_async_request(self.session_id)
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.post(
            "/api/ask/async",
            json=async_data,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 202:  # Accepted for processing
                try:
                    data = response.json()
                    request_id = data.get("request_id")
                    if request_id:
                        self.pending_requests[request_id] = {
                            "submitted_at": start_time,
                            "question": async_data["question"]
                        }
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 200:
                # Some implementations might return 200
                try:
                    data = response.json()
                    request_id = data.get("request_id")
                    if request_id:
                        self.pending_requests[request_id] = {
                            "submitted_at": start_time,
                            "question": async_data["question"]
                        }
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("async_submit", response_time, response.status_code)
            
            # Monitor Redis queue after submission
            self.check_redis_queue_stats()
    
    @task(40)
    def check_async_status(self):
        """Check status of pending async requests"""
        if not self.pending_requests:
            return
        
        # Pick a random pending request
        request_id = random.choice(list(self.pending_requests.keys()))
        request_info = self.pending_requests[request_id]
        
        headers = {}
        
        start_time = time.time()
        
        with self.client.get(
            f"/api/ask/async/{request_id}",
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    status = data.get("status", "unknown")
                    
                    if status in ["completed", "failed"]:
                        # Request finished, calculate total processing time
                        total_time = time.time() - request_info["submitted_at"]
                        metrics_collector.record_redis_metrics(0, total_time)
                        
                        # Remove from pending
                        del self.pending_requests[request_id]
                    
                    response.success()
                    
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # Request not found, might have been processed
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("async_status", response_time, response.status_code)
    
    @task(20)
    def get_queue_stats(self):
        """Get queue statistics"""
        headers = {}
        
        start_time = time.time()
        
        with self.client.get(
            "/api/queue/stats",
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    stats = response.json()
                    
                    # Extract queue metrics
                    queue_depth = stats.get("queue_depth", 0)
                    processing_count = stats.get("processing_count", 0)
                    completed_count = stats.get("completed_count", 0)
                    
                    # Record queue metrics
                    metrics_collector.record_redis_metrics(queue_depth, 0)
                    
                    response.success()
                    
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("queue_stats", response_time, response.status_code)
    
    def check_redis_queue_stats(self):
        """Directly check Redis queue statistics"""
        if not self.redis_client:
            return
        
        try:
            start_time = time.time()
            
            # Check queue length
            queue_name = "llm_request_queue"
            queue_depth = self.redis_client.llen(queue_name)
            
            # Check for processing keys (assuming a pattern)
            processing_keys = self.redis_client.keys("processing:*")
            processing_count = len(processing_keys)
            
            # Check for completed keys
            completed_keys = self.redis_client.keys("completed:*")
            completed_count = len(completed_keys)
            
            response_time = time.time() - start_time
            
            # Record metrics
            metrics_collector.record_redis_metrics(queue_depth, response_time)
            
            # Log queue status occasionally
            if random.random() < 0.1:  # 10% chance
                print(f"Redis Queue - Depth: {queue_depth}, Processing: {processing_count}, Completed: {completed_count}")
        
        except Exception as e:
            print(f"Redis queue check failed: {e}")
    
    @task(15)
    def bulk_async_submission(self):
        """Submit multiple async requests in bulk"""
        num_requests = random.randint(2, 5)
        requests_data = []
        
        for _ in range(num_requests):
            async_data = data_generator.generate_async_request(self.session_id)
            requests_data.append(async_data)
        
        bulk_data = {
            "requests": requests_data,
            "session_id": self.session_id
        }
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.post(
            "/api/ask/async/bulk",
            json=bulk_data,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 202]:
                try:
                    data = response.json()
                    request_ids = data.get("request_ids", [])
                    
                    # Track all submitted requests
                    for request_id in request_ids:
                        if request_id:
                            self.pending_requests[request_id] = {
                                "submitted_at": start_time,
                                "question": "bulk_request"
                            }
                    
                    response.success()
                    
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # Bulk endpoint might not exist
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("async_bulk", response_time, response.status_code)
    
    @task(10)
    def cancel_async_request(self):
        """Cancel a pending async request"""
        if not self.pending_requests:
            return
        
        # Pick a random pending request to cancel
        request_id = random.choice(list(self.pending_requests.keys()))
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.delete(
            f"/api/ask/async/{request_id}",
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 204]:
                # Successfully cancelled
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                response.success()
            elif response.status_code == 404:
                # Request not found or already processed
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                response.success()
            elif response.status_code == 405:
                # Method not allowed - cancel endpoint might not exist
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("async_cancel", response_time, response.status_code)
    
    @task(5)
    def get_user_async_history(self):
        """Get user's async request history"""
        headers = {}
        
        start_time = time.time()
        
        with self.client.get(
            f"/api/ask/async/history?session_id={self.session_id}",
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    history = response.json()
                    if isinstance(history, (list, dict)):
                        response.success()
                    else:
                        response.failure("Invalid history format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # No history found
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("async_history", response_time, response.status_code)
    
    def on_stop(self):
        """Cleanup when user stops"""
        # Close Redis connection
        if self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass
        
        # Export any remaining pending requests for analysis
        if self.pending_requests:
            print(f"User stopping with {len(self.pending_requests)} pending requests")

class RedisMonitorUser(HttpUser):
    """Dedicated user for monitoring Redis queue performance"""
    
    wait_time = between(1, 3)  # Fast monitoring
    
    # Disable SSL verification for self-signed certificates
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False
    
    def on_start(self):
        """Initialize Redis monitor"""
        # Setup Redis connection
        self.setup_redis_connection()
    
    def setup_redis_connection(self):
        """Setup Redis connection"""
        try:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
            redis_password = os.getenv('REDIS_PASSWORD', 'atlas_development')
            
            self.redis_client = redis.from_url(
                redis_url,
                password=redis_password,
                decode_responses=True
            )
            
            self.redis_client.ping()
            
        except Exception as e:
            print(f"Redis monitor connection failed: {e}")
            self.redis_client = None
            raise StopUser()
    
    @task(80)
    def monitor_queue_depth(self):
        """Monitor Redis queue depth"""
        if not self.redis_client:
            return
        
        try:
            start_time = time.time()
            
            queue_name = "llm_request_queue"
            queue_depth = self.redis_client.llen(queue_name)
            
            response_time = time.time() - start_time
            
            metrics_collector.record_redis_metrics(queue_depth, response_time)
            
        except Exception as e:
            print(f"Queue monitoring failed: {e}")
    
    @task(20)
    def monitor_redis_memory(self):
        """Monitor Redis memory usage"""
        if not self.redis_client:
            return
        
        try:
            start_time = time.time()
            
            info = self.redis_client.info('memory')
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            response_time = time.time() - start_time
            
            # Log memory usage occasionally
            if random.random() < 0.05:  # 5% chance
                print(f"Redis Memory - Used: {used_memory / 1024 / 1024:.2f}MB, Max: {max_memory / 1024 / 1024:.2f}MB")
            
        except Exception as e:
            print(f"Redis memory monitoring failed: {e}")
    
    def on_stop(self):
        """Cleanup Redis monitor"""
        if self.redis_client:
            try:
                self.redis_client.close()
            except:
                pass