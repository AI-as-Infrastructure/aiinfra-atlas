import time
import json
from typing import Dict, Any, List
from collections import defaultdict, deque
import threading

class MetricsCollector:
    """Custom metrics collection for ATLAS load testing"""
    
    def __init__(self):
        self.metrics = defaultdict(list)
        self.counters = defaultdict(int)
        self.timers = defaultdict(deque)
        self.errors = defaultdict(list)
        self._lock = threading.Lock()
        
        # Response time windows for percentile calculation
        self.response_times = {
            'ask_stream': deque(maxlen=1000),
            'ask_sync': deque(maxlen=1000),
            'feedback': deque(maxlen=1000),
            'async_submit': deque(maxlen=1000),
            'async_status': deque(maxlen=1000),
            'websocket': deque(maxlen=1000)
        }
        
        # Separate tracking for successful requests only
        self.success_response_times = {
            'ask_stream': deque(maxlen=1000),
            'ask_sync': deque(maxlen=1000),
            'feedback': deque(maxlen=1000),
            'async_submit': deque(maxlen=1000),
            'async_status': deque(maxlen=1000),
            'websocket': deque(maxlen=1000)
        }
    
    def record_request(self, endpoint: str, response_time: float, status_code: int, error: str = None):
        """Record request metrics"""
        with self._lock:
            timestamp = time.time()
            
            # Record response time (all requests)
            if endpoint in self.response_times:
                self.response_times[endpoint].append(response_time)
            
            # Record response time for successful requests only
            if 200 <= status_code < 300 and endpoint in self.success_response_times:
                self.success_response_times[endpoint].append(response_time)
            
            # Record general metrics
            self.metrics[f"{endpoint}_response_times"].append({
                'timestamp': timestamp,
                'response_time': response_time,
                'status_code': status_code
            })
            
            # Count requests
            self.counters[f"{endpoint}_total"] += 1
            
            # Count by status
            if 200 <= status_code < 300:
                self.counters[f"{endpoint}_success"] += 1
            elif 400 <= status_code < 500:
                self.counters[f"{endpoint}_client_error"] += 1
            elif 500 <= status_code < 600:
                self.counters[f"{endpoint}_server_error"] += 1
            
            # Record errors
            if error:
                self.errors[endpoint].append({
                    'timestamp': timestamp,
                    'error': error,
                    'status_code': status_code
                })
    
    def record_streaming_metrics(self, session_id: str, first_token_time: float, total_time: float, token_count: int):
        """Record streaming-specific metrics"""
        with self._lock:
            self.metrics['streaming_first_token'].append(first_token_time)
            self.metrics['streaming_total_time'].append(total_time)
            self.metrics['streaming_tokens_per_second'].append(token_count / total_time if total_time > 0 else 0)
            self.metrics['streaming_token_counts'].append(token_count)
            self.counters['streaming_sessions'] += 1
            
            # Track zero-token responses as complete failures (no answer generated)
            if token_count == 0:
                self.counters['streaming_zero_token_failures'] += 1
    
    def record_websocket_metrics(self, connection_time: float, message_count: int, errors: int):
        """Record WebSocket-specific metrics"""
        with self._lock:
            self.metrics['websocket_connection_time'].append(connection_time)
            self.metrics['websocket_messages'].append(message_count)
            self.counters['websocket_connections'] += 1
            self.counters['websocket_errors'] += errors
    
    def record_redis_metrics(self, queue_depth: int, processing_time: float):
        """Record Redis queue metrics"""
        with self._lock:
            self.metrics['redis_queue_depth'].append({
                'timestamp': time.time(),
                'depth': queue_depth
            })
            self.metrics['redis_processing_time'].append(processing_time)
    
    def get_percentiles(self, endpoint: str, percentiles: List[int] = [50, 95, 99]) -> Dict[int, float]:
        """Calculate response time percentiles (all requests)"""
        if endpoint not in self.response_times:
            return {}
        
        times = sorted(list(self.response_times[endpoint]))
        if not times:
            return {}
        
        result = {}
        for p in percentiles:
            index = int((p / 100.0) * len(times))
            if index >= len(times):
                index = len(times) - 1
            result[p] = times[index]
        
        return result
    
    def get_success_percentiles(self, endpoint: str, percentiles: List[int] = [50, 95, 99]) -> Dict[int, float]:
        """Calculate response time percentiles for successful requests only"""
        if endpoint not in self.success_response_times:
            return {}
        
        times = sorted(list(self.success_response_times[endpoint]))
        if not times:
            return {}
        
        result = {}
        for p in percentiles:
            index = int((p / 100.0) * len(times))
            if index >= len(times):
                index = len(times) - 1
            result[p] = times[index]
        
        return result
    
    def get_throughput(self, endpoint: str, window_seconds: int = 60) -> float:
        """Calculate requests per second for an endpoint"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        recent_requests = [
            m for m in self.metrics.get(f"{endpoint}_response_times", [])
            if m['timestamp'] > cutoff_time
        ]
        
        return len(recent_requests) / window_seconds if recent_requests else 0
    
    def get_error_rate(self, endpoint: str) -> float:
        """Calculate error rate as percentage"""
        total = self.counters.get(f"{endpoint}_total", 0)
        errors = (
            self.counters.get(f"{endpoint}_client_error", 0) +
            self.counters.get(f"{endpoint}_server_error", 0)
        )
        
        return (errors / total * 100) if total > 0 else 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        summary = {
            'timestamp': time.time(),
            'counters': dict(self.counters),
            'response_times': {},
            'throughput': {},
            'error_rates': {},
            'streaming_metrics': {},
            'websocket_metrics': {},
            'redis_metrics': {}
        }
        
        # Response time percentiles (all requests and successful only)
        for endpoint in self.response_times.keys():
            if self.response_times[endpoint]:
                summary['response_times'][endpoint] = self.get_percentiles(endpoint)
                summary['throughput'][endpoint] = self.get_throughput(endpoint)
                summary['error_rates'][endpoint] = self.get_error_rate(endpoint)
        
        # Success-only response time percentiles
        summary['success_response_times'] = {}
        for endpoint in self.success_response_times.keys():
            if self.success_response_times[endpoint]:
                summary['success_response_times'][endpoint] = self.get_success_percentiles(endpoint)
        
        # Streaming metrics
        if self.metrics['streaming_first_token']:
            summary['streaming_metrics'] = {
                'avg_first_token_time': sum(self.metrics['streaming_first_token']) / len(self.metrics['streaming_first_token']),
                'avg_total_time': sum(self.metrics['streaming_total_time']) / len(self.metrics['streaming_total_time']),
                'avg_tokens_per_second': sum(self.metrics['streaming_tokens_per_second']) / len(self.metrics['streaming_tokens_per_second']),
                'total_sessions': self.counters['streaming_sessions']
            }
        
        # WebSocket metrics
        if self.metrics['websocket_connection_time']:
            summary['websocket_metrics'] = {
                'avg_connection_time': sum(self.metrics['websocket_connection_time']) / len(self.metrics['websocket_connection_time']),
                'total_connections': self.counters['websocket_connections'],
                'total_errors': self.counters['websocket_errors']
            }
        
        # Redis metrics
        if self.metrics['redis_queue_depth']:
            recent_depths = [m['depth'] for m in self.metrics['redis_queue_depth'][-10:]]  # Last 10 readings
            summary['redis_metrics'] = {
                'current_queue_depth': recent_depths[-1] if recent_depths else 0,
                'avg_queue_depth': sum(recent_depths) / len(recent_depths) if recent_depths else 0,
                'avg_processing_time': sum(self.metrics['redis_processing_time']) / len(self.metrics['redis_processing_time']) if self.metrics['redis_processing_time'] else 0
            }
        
        return summary
    
    def export_to_file(self, filename: str):
        """Export metrics to JSON file"""
        summary = self.get_summary()
        with open(filename, 'w') as f:
            json.dump(summary, f, indent=2)
    
    def reset(self):
        """Reset all metrics"""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.timers.clear()
            self.errors.clear()
            for endpoint in self.response_times:
                self.response_times[endpoint].clear()

# Global metrics collector instance
metrics_collector = MetricsCollector()