#!/usr/bin/env python3
"""
Optimized Question Tasks for 15 Concurrent Users
Enhanced with expanded question pool, cache-busting, and realistic user behavior
"""

import json
import time
import random
import os
import uuid
from locust import HttpUser, task, between
from locust.exception import StopUser
from utils.enhanced_data_generators import enhanced_data_generator
from utils.metrics import metrics_collector

class OptimizedQuestionUser(HttpUser):
    """Optimized load test user for 15 concurrent users with enhanced diversity"""
    
    # Realistic wait times for parliamentary research users
    wait_time = between(3, 12)  # 3-12 seconds between tasks (realistic thinking time)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client.verify = False
        self.client.timeout = 25.0  # Increased timeout for complex queries
        
        # User session tracking
        self.user_type = None
        self.session_start_time = None
        self.questions_asked = 0
        self.corpus_preferences = []
        self.avg_response_time = 0
        
    def on_start(self):
        """Initialize optimized user session"""
        self.session_id = enhanced_data_generator.generate_session_id()
        self.qa_history = []
        self.session_start_time = time.time()
        
        # Assign realistic user type
        user_types = [
            ("researcher", 35),      # Academic researchers
            ("student", 25),         # Graduate students  
            ("journalist", 20),      # Journalists
            ("policy_analyst", 15),  # Policy analysts
            ("librarian", 5),        # Librarians
        ]
        self.user_type = self._weighted_choice(user_types)
        
        # Staggered startup to avoid thundering herd
        startup_delay = random.uniform(1, 8)  # 1-8 second stagger
        time.sleep(startup_delay)
        
        # Health check with retry
        self._perform_health_check()
        
        print(f"🚀 User {self.user_type} started session: {self.session_id}")
    
    def _weighted_choice(self, choices):
        """Make weighted random choice"""
        total = sum(weight for _, weight in choices)
        r = random.uniform(0, total)
        upto = 0
        for choice, weight in choices:
            if upto + weight >= r:
                return choice
            upto += weight
        return choices[-1][0]
    
    def _perform_health_check(self):
        """Perform health check with retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.get("/api/health", timeout=10)
                if response.status_code == 200:
                    return
                elif response.status_code == 503:
                    # Service unavailable - wait and retry
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ Health check failed after {max_retries} attempts: {e}")
                    raise StopUser()
                time.sleep(2 ** attempt)
    
    @task(75)
    def ask_optimized_streaming_question(self):
        """Primary task: Ask streaming question with cache-busting and diversity"""
        
        # Generate optimized request
        question_data = enhanced_data_generator.generate_optimized_ask_request(self.session_id)
        question_data['stream'] = True
        
        # Add user-specific context
        question_data['user_type'] = self.user_type
        question_data['session_context'] = {
            'questions_asked': self.questions_asked,
            'session_duration': time.time() - self.session_start_time,
            'previous_corpus': self.corpus_preferences[-1] if self.corpus_preferences else None
        }
        
        # Enhanced headers with cache-busting
        headers = self._get_enhanced_headers(question_data)
        
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
                    self._record_failure(start_time, response.status_code)
                    return
                
                # Process streaming response
                qa_id = None
                answer_content = ""
                citations = []
                response_complete = False
                chunk_count = 0
                
                for line in response.iter_lines():
                    if line:
                        chunk_count += 1
                        if first_token_time is None:
                            first_token_time = time.time() - start_time
                        
                        try:
                            if line.startswith(b"data: "):
                                data = json.loads(line[6:])
                                
                                if "qaId" in data:
                                    qa_id = data["qaId"]
                                
                                if data.get("responseComplete") is True:
                                    response_complete = True
                                
                                chunk = data.get("chunk", {})
                                if chunk.get("type") == "content":
                                    content = chunk.get("content", "")
                                    answer_content += content
                                    token_count += len(content.split())
                                elif chunk.get("type") == "citations":
                                    citations = chunk.get("citations", [])
                                    
                        except json.JSONDecodeError:
                            continue
                
                # Update user statistics
                self.questions_asked += 1
                self.corpus_preferences.append(question_data.get('corpus_filter', 'all'))
                
                # Store for potential feedback
                if qa_id and response_complete:
                    qa_data = {
                        "qa_id": qa_id,
                        "session_id": self.session_id,
                        "question": question_data["question"],
                        "answer": answer_content,
                        "citations": citations,
                        "response_time": time.time() - start_time,
                        "first_token_time": first_token_time,
                        "chunk_count": chunk_count,
                        "user_type": self.user_type
                    }
                    self.qa_history.append(qa_data)
                
                total_time = time.time() - start_time
                self.avg_response_time = (self.avg_response_time * (self.questions_asked - 1) + total_time) / self.questions_asked
                
                # Record detailed metrics
                self._record_success(total_time, first_token_time, token_count, chunk_count)
                
                response.success()
                
        except Exception as e:
            total_time = time.time() - start_time
            self._record_failure(start_time, 0, str(e))
            print(f"❌ Streaming question failed: {e}")
    
    @task(15)
    def ask_follow_up_question(self):
        """Ask follow-up question based on previous interactions"""
        if not self.qa_history:
            # No history, ask regular question
            self.ask_optimized_streaming_question()
            return
        
        # Generate follow-up based on previous question
        previous_qa = random.choice(self.qa_history)
        question_data = enhanced_data_generator.generate_optimized_ask_request(self.session_id)
        
        # Make it a follow-up by referencing previous context
        original_question = previous_qa["question"]
        follow_up_phrases = [
            f"Building on the previous question about {self._extract_topic(original_question)}, can you provide more details about",
            f"Following up on the earlier discussion, what else was said about",
            f"Continuing from the previous answer, how did MPs specifically address",
            f"As a follow-up to the earlier question, what were the outcomes of",
        ]
        
        follow_up_prefix = random.choice(follow_up_phrases)
        question_data['question'] = f"{follow_up_prefix} {question_data['question'].lower()}"
        question_data['stream'] = True
        
        # Add chat history context
        question_data['chat_history'] = [
            {"role": "user", "content": original_question},
            {"role": "assistant", "content": previous_qa["answer"][:200] + "..."},
            {"role": "user", "content": question_data['question']}
        ]
        
        # Execute the follow-up
        headers = self._get_enhanced_headers(question_data)
        
        start_time = time.time()
        try:
            with self.client.post(
                "/api/ask/stream",
                json=question_data,
                headers=headers,
                stream=True,
                catch_response=True
            ) as response:
                
                if response.status_code == 200:
                    # Process follow-up response (simplified)
                    for line in response.iter_lines():
                        if line:
                            pass  # Just consume the response
                    
                    total_time = time.time() - start_time
                    self._record_success(total_time, None, 0, 0, "follow_up")
                    response.success()
                else:
                    response.failure(f"HTTP {response.status_code}")
                    self._record_failure(start_time, response.status_code)
        
        except Exception as e:
            self._record_failure(start_time, 0, str(e))
    
    @task(8)
    def submit_realistic_feedback(self):
        """Submit realistic feedback based on user behavior"""
        if not self.qa_history:
            return
        
        # Select a recent QA for feedback (users typically provide feedback on recent interactions)
        recent_qa = self.qa_history[-1] if self.qa_history else None
        if not recent_qa:
            return
        
        # Realistic feedback delay (users take time to read and think)
        reading_time = random.uniform(5, 20)  # 5-20 seconds reading time
        time.sleep(reading_time)
        
        # Generate realistic feedback
        feedback_data = enhanced_data_generator.generate_realistic_feedback(
            recent_qa["qa_id"],
            self.session_id,
            recent_qa["question"],
            recent_qa["answer"]
        )
        
        # Add user-specific context
        feedback_data['user_type'] = self.user_type
        feedback_data['session_context'] = {
            'questions_in_session': len(self.qa_history),
            'avg_response_time': self.avg_response_time,
            'preferred_corpus': max(set(self.corpus_preferences), key=self.corpus_preferences.count) if self.corpus_preferences else 'all'
        }
        
        # Submit feedback
        headers = self._get_enhanced_headers(feedback_data)
        
        start_time = time.time()
        try:
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
                            metrics_collector.record_request("feedback", response_time, 200)
                        else:
                            response.failure("Feedback not accepted")
                            metrics_collector.record_request("feedback", response_time, 400)
                    except json.JSONDecodeError:
                        response.failure("Invalid JSON response")
                        metrics_collector.record_request("feedback", response_time, 500)
                else:
                    response.failure(f"HTTP {response.status_code}")
                    metrics_collector.record_request("feedback", response_time, response.status_code)
        
        except Exception as e:
            response_time = time.time() - start_time
            metrics_collector.record_request("feedback", response_time, 0, str(e))
    
    @task(5)
    def query_documents_with_cache_busting(self):
        """Query documents with cache-busting parameters"""
        question = enhanced_data_generator.generate_diverse_question(self.session_id, cache_bust=True)
        corpus_filter = enhanced_data_generator.generate_realistic_corpus_filter(self.session_id)
        
        # Add cache-busting parameters
        query_data = {
            "query": question,
            "corpus_filter": corpus_filter,
            "max_results": random.randint(10, 25),  # Variable result count
            "search_type": random.choice(["similarity", "mmr"]),  # Vary search type
            "timestamp": int(time.time() * 1000),  # Cache buster
            "request_id": uuid.uuid4().hex[:8],  # Unique request ID
        }
        
        headers = self._get_enhanced_headers(query_data)
        
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
                        metrics_collector.record_request("query", response_time, 200)
                    else:
                        response.failure("Unexpected response format")
                        metrics_collector.record_request("query", response_time, 400)
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
                    metrics_collector.record_request("query", response_time, 500)
            else:
                response.failure(f"HTTP {response.status_code}")
                metrics_collector.record_request("query", response_time, response.status_code)
    
    def _get_enhanced_headers(self, request_data):
        """Get enhanced headers with cache-busting"""
        base_host = os.getenv('VITE_API_URL', self.environment.host)
        
        return {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": base_host,
            "Referer": f"{base_host}/",
            "User-Agent": self._get_random_user_agent(),
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Trace-Id": request_data.get("qa_id", enhanced_data_generator.generate_qa_id()),
            "X-Session-Id": self.session_id,
            "X-Request-Id": uuid.uuid4().hex[:8],
            "X-Timestamp": str(int(time.time() * 1000)),
            "X-User-Type": self.user_type,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
    
    def _get_random_user_agent(self):
        """Get random user agent for diversity"""
        user_agents = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        return random.choice(user_agents)
    
    def _extract_topic(self, question):
        """Extract topic from question for follow-ups"""
        # Simple topic extraction
        topics = ["federation", "policy", "parliament", "government", "legislation", "debate"]
        for topic in topics:
            if topic in question.lower():
                return topic
        return "parliamentary matters"
    
    def _record_success(self, total_time, first_token_time, token_count, chunk_count, request_type="ask_stream"):
        """Record successful request metrics"""
        metrics_collector.record_request(request_type, total_time, 200)
        
        if first_token_time:
            metrics_collector.record_streaming_metrics(
                self.session_id, first_token_time, total_time, token_count
            )
        
        # Record additional metrics
        metrics_collector.record_custom_metric(f"{request_type}_chunks", chunk_count)
        metrics_collector.record_custom_metric(f"{request_type}_tokens", token_count)
    
    def _record_failure(self, start_time, status_code, error_msg=""):
        """Record failed request metrics"""
        total_time = time.time() - start_time
        metrics_collector.record_request("ask_stream", total_time, status_code, error_msg)
    
    def on_stop(self):
        """Cleanup when user stops"""
        session_duration = time.time() - self.session_start_time
        
        print(f"🛑 User {self.user_type} session ended:")
        print(f"   Duration: {session_duration:.1f}s")
        print(f"   Questions: {self.questions_asked}")
        print(f"   Avg Response: {self.avg_response_time:.1f}s")
        
        # Cleanup session data
        enhanced_data_generator.cleanup_old_sessions()