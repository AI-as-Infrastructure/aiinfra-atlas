import json
import time
import random
from locust import HttpUser, task, between
from locust.exception import StopUser
from utils.data_generators import data_generator
from utils.metrics import metrics_collector

class FeedbackUser(HttpUser):
    """Load test user focused on feedback submission"""
    
    wait_time = between(5, 15)  # Longer wait time - feedback is less frequent
    
    # Disable SSL verification for self-signed certificates
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False
    
    def on_start(self):
        """Initialize feedback user"""
        self.session_id = data_generator.generate_session_id()
        self.qa_pairs = []
        
        # Generate some Q&A pairs to provide feedback on
        self._generate_qa_pairs()
    
    def _generate_qa_pairs(self):
        """Generate some Q&A pairs for feedback testing"""
        for _ in range(random.randint(2, 5)):
            qa_id = data_generator.generate_qa_id()
            question = data_generator.generate_question()
            
            self.qa_pairs.append({
                "qa_id": qa_id,
                "session_id": self.session_id,
                "question": question
            })
    
    @task(60)
    def submit_http_feedback(self):
        """Submit feedback via HTTP POST"""
        if not self.qa_pairs:
            self._generate_qa_pairs()
        
        qa_pair = random.choice(self.qa_pairs)
        # Generate realistic answer for feedback
        answer_text = f"Based on parliamentary records, {random.choice(['the government', 'MPs', 'the opposition'])} discussed {qa_pair['question'].lower()} extensively. The findings indicate {random.choice(['significant progress', 'areas for improvement', 'ongoing challenges'])}."
        feedback_data = data_generator.generate_feedback_data(
            qa_pair["qa_id"], 
            qa_pair["session_id"],
            qa_pair["question"],
            answer_text
        )
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.post(
            "/api/feedback",
            json=feedback_data,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    if result.get("status") == "success":
                        response.success()
                    else:
                        response.failure("Feedback submission failed")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 201:
                # Some APIs return 201 for created resources
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("feedback", response_time, response.status_code)
    
    @task(20)
    def submit_bulk_feedback(self):
        """Submit multiple feedback items at once"""
        if len(self.qa_pairs) < 2:
            self._generate_qa_pairs()
        
        # Select 2-4 Q&A pairs for bulk feedback
        selected_pairs = random.sample(self.qa_pairs, min(random.randint(2, 4), len(self.qa_pairs)))
        
        bulk_feedback = {
            "feedback_items": [
                data_generator.generate_feedback_data(
                    pair["qa_id"], 
                    pair["session_id"],
                    pair["question"],
                    f"Parliamentary analysis shows {random.choice(['comprehensive', 'detailed', 'thorough'])} coverage of {pair['question'].split()[-3:]}."
                )
                for pair in selected_pairs
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.post(
            "/api/feedback/bulk",
            json=bulk_feedback,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 404:
                # Bulk endpoint might not exist, that's ok
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("feedback_bulk", response_time, response.status_code)
    
    @task(10)
    def get_feedback_stats(self):
        """Get feedback statistics"""
        headers = {}
        
        start_time = time.time()
        
        with self.client.get(
            f"/api/feedback/stats?session_id={self.session_id}",
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    stats = response.json()
                    if isinstance(stats, dict):
                        response.success()
                    else:
                        response.failure("Invalid stats format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # Stats endpoint might not exist
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("feedback_stats", response_time, response.status_code)
    
    @task(5)
    def get_session_feedback(self):
        """Get all feedback for current session"""
        headers = {}
        
        start_time = time.time()
        
        with self.client.get(
            f"/api/feedback/session/{self.session_id}",
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    feedback_list = response.json()
                    if isinstance(feedback_list, (list, dict)):
                        response.success()
                    else:
                        response.failure("Invalid feedback format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            elif response.status_code == 404:
                # No feedback found, that's ok
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("feedback_session", response_time, response.status_code)

class MixedFeedbackUser(HttpUser):
    """User that asks questions AND provides feedback (realistic user behavior)"""
    
    wait_time = between(3, 10)
    
    # Disable SSL verification for self-signed certificates
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False
    
    def on_start(self):
        """Initialize mixed user"""
        self.session_id = data_generator.generate_session_id()
        self.qa_history = []
    
    @task(50)
    def ask_question_and_maybe_feedback(self):
        """Ask a question and potentially provide feedback"""
        question_data = data_generator.generate_ask_request(self.session_id)
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        # Submit question
        with self.client.post(
            "/api/ask",
            json=question_data,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    qa_id = data.get("qa_id")
                    if qa_id:
                        self.qa_history.append({
                            "qa_id": qa_id,
                            "session_id": self.session_id,
                            "question": question_data["question"]
                        })
                        
                        # 60% chance to provide feedback after question
                        if random.random() < 0.6:
                            self._provide_delayed_feedback(qa_id)
                    
                    response.success()
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("ask_sync", response_time, response.status_code)
    
    def _provide_delayed_feedback(self, qa_id: str):
        """Provide feedback after a short delay (simulates user reading response)"""
        # Simulate user reading the response
        time.sleep(random.uniform(2, 8))
        
        # Get question text and generate answer
        question_text = next((item["question"] for item in self.qa_history if item["qa_id"] == qa_id), "What was discussed in Parliament?")
        answer_text = f"Based on parliamentary records, this {random.choice(['policy', 'legislation', 'debate'])} received {random.choice(['substantial', 'careful', 'detailed'])} consideration."
        feedback_data = data_generator.generate_feedback_data(qa_id, self.session_id, question_text, answer_text)
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.post(
            "/api/feedback",
            json=feedback_data,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("feedback", response_time, response.status_code)
    
    @task(30)
    def provide_feedback_on_history(self):
        """Provide feedback on previously asked questions"""
        if not self.qa_history:
            return
        
        qa_pair = random.choice(self.qa_history)
        # Generate realistic answer for historical feedback
        answer_text = f"Parliamentary records indicate {random.choice(['extensive', 'thorough', 'comprehensive'])} discussion of {qa_pair['question'].split()[-2:]} with {random.choice(['positive', 'mixed', 'significant'])} outcomes."
        feedback_data = data_generator.generate_feedback_data(
            qa_pair["qa_id"],
            qa_pair["session_id"],
            qa_pair["question"],
            answer_text
        )
        
        headers = {"Content-Type": "application/json"}
        
        start_time = time.time()
        
        with self.client.post(
            "/api/feedback",
            json=feedback_data,
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code in [200, 201]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("feedback", response_time, response.status_code)
    
    @task(20)
    def browse_previous_sessions(self):
        """Simulate user browsing their previous Q&A sessions"""
        headers = {}
        
        start_time = time.time()
        
        with self.client.get(
            f"/api/sessions/{self.session_id}",
            headers=headers,
            catch_response=True
        ) as response:
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Session might not exist yet
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
            
            metrics_collector.record_request("session_browse", response_time, response.status_code)