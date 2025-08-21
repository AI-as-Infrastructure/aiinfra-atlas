import time
import json
import psutil
import os
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
        
        # Infrastructure metrics
        self.infrastructure_metrics = {
            'memory_usage': deque(maxlen=500),
            'cpu_usage': deque(maxlen=500),
            'disk_io': deque(maxlen=500),
            'network_io': deque(maxlen=500),
            'process_count': deque(maxlen=500),
            'file_descriptors': deque(maxlen=500)
        }
        self.infrastructure_start_time = time.time()
        self.baseline_memory = None
        self.baseline_cpu = None
        
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
            
            # Track completion success vs failures
            if token_count > 0:
                self.counters['streaming_successful_completions'] = self.counters.get('streaming_successful_completions', 0) + 1
            else:
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
    
    def _find_gunicorn_workers(self):
        """Find all Gunicorn worker processes"""
        workers = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info['cmdline'] or []
                    # Look for processes running gunicorn with backend.app:app
                    if any('gunicorn' in str(arg) for arg in cmdline):
                        # Check if it's a worker process (not master)
                        if any('backend.app:app' in arg or 'uvicorn.workers' in arg for arg in cmdline):
                            workers.append(psutil.Process(proc.info['pid']))
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception as e:
            print(f"Warning: Error finding Gunicorn workers: {e}")
        return workers

    def record_infrastructure_metrics(self):
        """Record current infrastructure metrics for Gunicorn workers only"""
        try:
            timestamp = time.time()
            
            # Find Gunicorn worker processes
            workers = self._find_gunicorn_workers()
            
            if not workers:
                print("Warning: No Gunicorn workers found, falling back to system metrics")
                # Fallback to system-wide metrics if no workers found
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                memory_available_gb = memory.available / (1024**3)
                memory_used_gb = memory.used / (1024**3)
                cpu_percent = psutil.cpu_percent(interval=0.1)
                cpu_count = int(os.environ.get('GUNICORN_WORKERS', psutil.cpu_count()))
                worker_count = 0
                worker_memory_mb = 0
            else:
                # Calculate metrics for Gunicorn workers only
                total_worker_memory = 0
                total_cpu_percent = 0
                worker_count = len(workers)
                
                for worker in workers:
                    try:
                        # Worker memory usage
                        worker_memory_info = worker.memory_info()
                        total_worker_memory += worker_memory_info.rss
                        
                        # Worker CPU usage
                        worker_cpu = worker.cpu_percent()
                        total_cpu_percent += worker_cpu
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        worker_count -= 1  # Reduce count if worker is no longer accessible
                        continue
                
                # Convert metrics
                worker_memory_mb = total_worker_memory / (1024**2)
                memory_used_gb = total_worker_memory / (1024**3)
                
                # Calculate memory percentage based on configured worker memory limits
                max_worker_memory_mb = int(os.environ.get('GUNICORN_MAX_WORKER_MEMORY_MB', 1800))
                max_total_memory_mb = max_worker_memory_mb * worker_count
                memory_percent = (worker_memory_mb / max_total_memory_mb * 100) if max_total_memory_mb > 0 else 0
                
                # Memory available is remaining allocated memory
                memory_available_gb = (max_total_memory_mb - worker_memory_mb) / 1024
                
                # CPU metrics
                cpu_percent = total_cpu_percent  # Total CPU usage across all workers
                cpu_count = int(os.environ.get('GUNICORN_WORKERS', worker_count))
            
            # Disk I/O (keep system-wide as workers share disk)
            disk_io = psutil.disk_io_counters()
            disk_read_mb = disk_io.read_bytes / (1024**2) if disk_io else 0
            disk_write_mb = disk_io.write_bytes / (1024**2) if disk_io else 0
            
            # Network I/O (keep system-wide as workers share network)
            net_io = psutil.net_io_counters()
            net_sent_mb = net_io.bytes_sent / (1024**2) if net_io else 0
            net_recv_mb = net_io.bytes_recv / (1024**2) if net_io else 0
            
            # Process count (Gunicorn workers only)
            process_count = worker_count
            
            # File descriptors (sum across all workers)
            fd_count = 0
            for worker in workers:
                try:
                    fd_count += worker.num_fds()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Set baseline on first measurement
            if self.baseline_memory is None:
                self.baseline_memory = memory_percent
                self.baseline_cpu = cpu_percent
            
            with self._lock:
                self.infrastructure_metrics['memory_usage'].append({
                    'timestamp': timestamp,
                    'percent': memory_percent,
                    'used_gb': memory_used_gb,
                    'available_gb': memory_available_gb,
                    'baseline_delta': memory_percent - self.baseline_memory
                })
                
                self.infrastructure_metrics['cpu_usage'].append({
                    'timestamp': timestamp,
                    'percent': cpu_percent,
                    'core_count': cpu_count,
                    'baseline_delta': cpu_percent - self.baseline_cpu
                })
                
                self.infrastructure_metrics['disk_io'].append({
                    'timestamp': timestamp,
                    'read_mb': disk_read_mb,
                    'write_mb': disk_write_mb
                })
                
                self.infrastructure_metrics['network_io'].append({
                    'timestamp': timestamp,
                    'sent_mb': net_sent_mb,
                    'recv_mb': net_recv_mb
                })
                
                self.infrastructure_metrics['process_count'].append({
                    'timestamp': timestamp,
                    'count': process_count
                })
                
                self.infrastructure_metrics['file_descriptors'].append({
                    'timestamp': timestamp,
                    'count': fd_count
                })
                
        except Exception as e:
            # Don't let infrastructure monitoring break the test
            print(f"Warning: Infrastructure monitoring failed: {e}")
    
    def get_infrastructure_summary(self) -> Dict[str, Any]:
        """Get infrastructure metrics summary"""
        if not self.infrastructure_metrics['memory_usage']:
            return {}
        
        # Get latest readings
        latest_memory = list(self.infrastructure_metrics['memory_usage'])[-1]
        latest_cpu = list(self.infrastructure_metrics['cpu_usage'])[-1]
        
        # Calculate averages over the test
        memory_readings = [m['percent'] for m in self.infrastructure_metrics['memory_usage']]
        cpu_readings = [c['percent'] for c in self.infrastructure_metrics['cpu_usage']]
        
        # Calculate peak usage
        peak_memory = max(memory_readings) if memory_readings else 0
        peak_cpu = max(cpu_readings) if cpu_readings else 0
        
        # Calculate infrastructure load percentage based on worker allocation
        # Memory load based on configured worker memory limits
        max_worker_memory_mb = int(os.environ.get('GUNICORN_MAX_WORKER_MEMORY_MB', 1800))
        worker_count = int(os.environ.get('GUNICORN_WORKERS', 8))
        max_total_memory_mb = max_worker_memory_mb * worker_count
        
        # For memory, peak_memory is already calculated as percentage of allocated memory
        memory_load_percent = min(peak_memory, 100)  # Already a percentage of allocated memory
        
        # For CPU, calculate based on worker capacity (each worker can use 100% of one core)
        max_cpu_percent = worker_count * 100  # Each worker can use 100% of a core
        cpu_load_percent = (peak_cpu / max_cpu_percent * 100) if max_cpu_percent > 0 else 0
        
        return {
            'test_duration_minutes': (time.time() - self.infrastructure_start_time) / 60,
            'worker_configuration': {
                'gunicorn_workers': worker_count,
                'max_memory_per_worker_mb': max_worker_memory_mb,
                'total_allocated_memory_mb': max_total_memory_mb,
                'monitoring_mode': 'worker_specific'
            },
            'memory': {
                'current_percent': latest_memory['percent'],
                'current_used_gb': latest_memory['used_gb'],
                'peak_percent': peak_memory,
                'avg_percent': sum(memory_readings) / len(memory_readings),
                'baseline_delta': latest_memory['baseline_delta'],
                'load_percentage': min(memory_load_percent, 100),  # Cap at 100%
                'allocated_memory_gb': max_total_memory_mb / 1024
            },
            'cpu': {
                'current_percent': latest_cpu['percent'],
                'peak_percent': peak_cpu,
                'avg_percent': sum(cpu_readings) / len(cpu_readings),
                'baseline_delta': latest_cpu['baseline_delta'],
                'worker_count': latest_cpu['core_count'],
                'load_percentage': min(cpu_load_percent, 100),  # Cap at 100%
                'max_theoretical_cpu_percent': worker_count * 100
            },
            'overall_infrastructure_load': max(memory_load_percent, cpu_load_percent),
            'infrastructure_status': self._get_infrastructure_status(memory_load_percent, cpu_load_percent)
        }
    
    def _get_infrastructure_status(self, memory_load: float, cpu_load: float) -> str:
        """Determine infrastructure status based on load percentages"""
        max_load = max(memory_load, cpu_load)
        if max_load < 50:
            return "LOW_LOAD"
        elif max_load < 75:
            return "MODERATE_LOAD" 
        elif max_load < 90:
            return "HIGH_LOAD"
        else:
            return "CRITICAL_LOAD"
    
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
            'redis_metrics': {},
            'infrastructure_metrics': self.get_infrastructure_summary()
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
            successful_completions = self.counters.get('streaming_successful_completions', 0)
            total_sessions = self.counters.get('streaming_sessions', 0)
            zero_token_failures = self.counters.get('streaming_zero_token_failures', 0)
            
            summary['streaming_metrics'] = {
                'avg_first_token_time': sum(self.metrics['streaming_first_token']) / len(self.metrics['streaming_first_token']),
                'avg_total_time': sum(self.metrics['streaming_total_time']) / len(self.metrics['streaming_total_time']),
                'avg_tokens_per_second': sum(self.metrics['streaming_tokens_per_second']) / len(self.metrics['streaming_tokens_per_second']),
                'total_sessions': total_sessions,
                'successful_completions': successful_completions,
                'zero_token_failures': zero_token_failures,
                'completion_success_rate': (successful_completions / total_sessions * 100) if total_sessions > 0 else 0,
                'avg_token_count': sum(self.metrics['streaming_token_counts']) / len(self.metrics['streaming_token_counts']) if self.metrics['streaming_token_counts'] else 0
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
            for metric in self.infrastructure_metrics:
                self.infrastructure_metrics[metric].clear()
            self.infrastructure_start_time = time.time()
            self.baseline_memory = None
            self.baseline_cpu = None

# Global metrics collector instance
metrics_collector = MetricsCollector()