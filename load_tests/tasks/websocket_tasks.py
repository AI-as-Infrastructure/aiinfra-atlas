import json
import time
import random
import threading
from typing import Optional
import websocket
from locust import User, task, between, events
from locust.exception import StopUser
from utils.data_generators import data_generator
from utils.metrics import metrics_collector

class WebSocketUser(User):
    """Load test user for WebSocket connections"""
    
    wait_time = between(1, 5)
    
    def __init__(self, environment):
        super().__init__(environment)
        self.ws = None
        self.session_id = None
        self.auth_manager = None
        self.connected = False
        self.message_count = 0
        self.error_count = 0
        self.connection_start_time = None
        
    def on_start(self):
        """Initialize WebSocket connection"""
        self.session_id = data_generator.generate_session_id()
        self.connect_websocket()
    
    def connect_websocket(self):
        """Establish WebSocket connection"""
        if self.connected:
            return
            
        try:
            # Get WebSocket URL
            base_url = self.environment.host.replace('http://', 'ws://').replace('https://', 'wss://')
            ws_url = f"{base_url}/ws/{self.session_id}"
            
            # No auth headers needed
            headers = {}
            
            self.connection_start_time = time.time()
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                header=list(headers.items()) if headers else None,
                on_open=self.on_websocket_open,
                on_message=self.on_websocket_message,
                on_error=self.on_websocket_error,
                on_close=self.on_websocket_close
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection to establish
            timeout = 10
            start_wait = time.time()
            while not self.connected and (time.time() - start_wait) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise Exception("WebSocket connection timeout")
                
        except Exception as e:
            self.error_count += 1
            events.request_failure.fire(
                request_type="WebSocket",
                name="connect",
                response_time=(time.time() - self.connection_start_time) * 1000,
                exception=e
            )
            raise StopUser()
    
    def on_websocket_open(self, ws):
        """Handle WebSocket connection open"""
        connection_time = time.time() - self.connection_start_time
        self.connected = True
        
        events.request_success.fire(
            request_type="WebSocket",
            name="connect",
            response_time=connection_time * 1000,
            response_length=0
        )
        
        metrics_collector.record_request("websocket_connect", connection_time, 200)
    
    def on_websocket_message(self, ws, message):
        """Handle incoming WebSocket message"""
        self.message_count += 1
        
        try:
            data = json.loads(message)
            message_type = data.get('type', 'unknown')
            
            # Record different message types
            events.request_success.fire(
                request_type="WebSocket",
                name=f"message_{message_type}",
                response_time=0,
                response_length=len(message)
            )
            
        except json.JSONDecodeError:
            self.error_count += 1
            events.request_failure.fire(
                request_type="WebSocket",
                name="message_decode",
                response_time=0,
                exception=Exception("Invalid JSON in WebSocket message")
            )
    
    def on_websocket_error(self, ws, error):
        """Handle WebSocket error"""
        self.error_count += 1
        events.request_failure.fire(
            request_type="WebSocket",
            name="error",
            response_time=0,
            exception=error
        )
    
    def on_websocket_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.connected = False
        
        # Record connection metrics
        if hasattr(self, 'connection_start_time') and self.connection_start_time:
            total_connection_time = time.time() - self.connection_start_time
            metrics_collector.record_websocket_metrics(
                total_connection_time, self.message_count, self.error_count
            )
    
    @task(40)
    def send_feedback_message(self):
        """Send feedback via WebSocket"""
        if not self.connected or not self.ws:
            self.connect_websocket()
            return
        
        qa_id = data_generator.generate_qa_id()
        feedback_data = data_generator.generate_feedback_data(qa_id, self.session_id)
        
        message = {
            "type": "feedback",
            "data": feedback_data
        }
        
        start_time = time.time()
        
        try:
            self.ws.send(json.dumps(message))
            
            events.request_success.fire(
                request_type="WebSocket",
                name="send_feedback",
                response_time=(time.time() - start_time) * 1000,
                response_length=len(json.dumps(message))
            )
            
            metrics_collector.record_request("websocket_feedback", time.time() - start_time, 200)
            
        except Exception as e:
            events.request_failure.fire(
                request_type="WebSocket",
                name="send_feedback",
                response_time=(time.time() - start_time) * 1000,
                exception=e
            )
            
            metrics_collector.record_request("websocket_feedback", time.time() - start_time, 0, str(e))
            self.error_count += 1
    
    @task(30)
    def send_status_request(self):
        """Request status via WebSocket"""
        if not self.connected or not self.ws:
            self.connect_websocket()
            return
        
        message = {
            "type": "status_request",
            "session_id": self.session_id
        }
        
        start_time = time.time()
        
        try:
            self.ws.send(json.dumps(message))
            
            events.request_success.fire(
                request_type="WebSocket",
                name="status_request",
                response_time=(time.time() - start_time) * 1000,
                response_length=len(json.dumps(message))
            )
            
        except Exception as e:
            events.request_failure.fire(
                request_type="WebSocket",
                name="status_request",
                response_time=(time.time() - start_time) * 1000,
                exception=e
            )
            self.error_count += 1
    
    @task(20)
    def send_ping(self):
        """Send ping to keep connection alive"""
        if not self.connected or not self.ws:
            self.connect_websocket()
            return
        
        message = {
            "type": "ping",
            "timestamp": time.time()
        }
        
        start_time = time.time()
        
        try:
            self.ws.send(json.dumps(message))
            
            events.request_success.fire(
                request_type="WebSocket",
                name="ping",
                response_time=(time.time() - start_time) * 1000,
                response_length=len(json.dumps(message))
            )
            
        except Exception as e:
            events.request_failure.fire(
                request_type="WebSocket",
                name="ping",
                response_time=(time.time() - start_time) * 1000,
                exception=e
            )
            self.error_count += 1
    
    @task(10)
    def send_bulk_message(self):
        """Send multiple messages in quick succession"""
        if not self.connected or not self.ws:
            self.connect_websocket()
            return
        
        messages = []
        for i in range(random.randint(2, 5)):
            qa_id = data_generator.generate_qa_id()
            feedback_data = data_generator.generate_feedback_data(qa_id, self.session_id)
            
            messages.append({
                "type": "bulk_feedback",
                "index": i,
                "data": feedback_data
            })
        
        start_time = time.time()
        sent_count = 0
        
        try:
            for message in messages:
                self.ws.send(json.dumps(message))
                sent_count += 1
                time.sleep(0.1)  # Small delay between messages
            
            events.request_success.fire(
                request_type="WebSocket",
                name="bulk_message",
                response_time=(time.time() - start_time) * 1000,
                response_length=sum(len(json.dumps(m)) for m in messages)
            )
            
        except Exception as e:
            events.request_failure.fire(
                request_type="WebSocket",
                name="bulk_message",
                response_time=(time.time() - start_time) * 1000,
                exception=e
            )
            self.error_count += 1
    
    def on_stop(self):
        """Clean up WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        self.connected = False

class AsyncWebSocketUser(User):
    """WebSocket user for async request monitoring"""
    
    wait_time = between(2, 8)
    
    def __init__(self, environment):
        super().__init__(environment)
        self.ws = None
        self.session_id = None
        self.auth_manager = None
        self.connected = False
        self.pending_requests = {}  # Track async requests
        
    def on_start(self):
        """Initialize async WebSocket user"""
        self.session_id = data_generator.generate_session_id()
        self.connect_async_websocket()
    
    def connect_async_websocket(self):
        """Connect to async status WebSocket"""
        try:
            base_url = self.environment.host.replace('http://', 'ws://').replace('https://', 'wss://')
            
            # Generate a mock request ID for testing
            request_id = data_generator.generate_qa_id()
            ws_url = f"{base_url}/ws/async/{request_id}"
            
            headers = {}
            
            connection_start_time = time.time()
            
            self.ws = websocket.WebSocketApp(
                ws_url,
                header=list(headers.items()) if headers else None,
                on_open=lambda ws: self.on_async_websocket_open(ws, connection_start_time),
                on_message=self.on_async_websocket_message,
                on_error=self.on_async_websocket_error,
                on_close=self.on_async_websocket_close
            )
            
            # Start WebSocket in a separate thread
            self.ws_thread = threading.Thread(target=self.ws.run_forever)
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            # Wait for connection
            timeout = 10
            start_wait = time.time()
            while not self.connected and (time.time() - start_wait) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise Exception("Async WebSocket connection timeout")
                
        except Exception as e:
            events.request_failure.fire(
                request_type="AsyncWebSocket",
                name="connect",
                response_time=0,
                exception=e
            )
            raise StopUser()
    
    def on_async_websocket_open(self, ws, connection_start_time):
        """Handle async WebSocket connection open"""
        connection_time = time.time() - connection_start_time
        self.connected = True
        
        events.request_success.fire(
            request_type="AsyncWebSocket",
            name="connect",
            response_time=connection_time * 1000,
            response_length=0
        )
    
    def on_async_websocket_message(self, ws, message):
        """Handle async status messages"""
        try:
            data = json.loads(message)
            status = data.get('status', 'unknown')
            request_id = data.get('request_id')
            
            if request_id in self.pending_requests:
                start_time = self.pending_requests[request_id]
                processing_time = time.time() - start_time
                
                if status in ['completed', 'failed']:
                    # Request finished
                    del self.pending_requests[request_id]
                    metrics_collector.record_redis_metrics(0, processing_time)
                
                events.request_success.fire(
                    request_type="AsyncWebSocket",
                    name=f"status_{status}",
                    response_time=0,
                    response_length=len(message)
                )
            
        except json.JSONDecodeError:
            events.request_failure.fire(
                request_type="AsyncWebSocket",
                name="message_decode",
                response_time=0,
                exception=Exception("Invalid JSON in async WebSocket message")
            )
    
    def on_async_websocket_error(self, ws, error):
        """Handle async WebSocket error"""
        events.request_failure.fire(
            request_type="AsyncWebSocket",
            name="error",
            response_time=0,
            exception=error
        )
    
    def on_async_websocket_close(self, ws, close_status_code, close_msg):
        """Handle async WebSocket connection close"""
        self.connected = False
    
    @task(50)
    def monitor_async_request(self):
        """Monitor async request status"""
        if not self.connected:
            self.connect_async_websocket()
            return
        
        # Simulate monitoring an async request
        request_id = data_generator.generate_qa_id()
        self.pending_requests[request_id] = time.time()
        
        # In a real scenario, this would be triggered by an actual async request
        # For testing, we simulate the status updates
        time.sleep(random.uniform(1, 3))
    
    def on_stop(self):
        """Clean up async WebSocket connection"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
        
        self.connected = False