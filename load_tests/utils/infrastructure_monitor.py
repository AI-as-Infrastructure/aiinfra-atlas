#!/usr/bin/env python3
"""
Infrastructure Monitoring Thread for Load Tests

Continuously monitors system resources during load testing to track
infrastructure utilization and identify bottlenecks.
"""

import threading
import time
from .metrics import metrics_collector

class InfrastructureMonitor(threading.Thread):
    """Background thread to monitor infrastructure metrics during load tests"""
    
    def __init__(self, interval_seconds=5):
        super().__init__(daemon=True)
        self.interval = interval_seconds
        self.running = False
        self._stop_event = threading.Event()
    
    def start_monitoring(self):
        """Start infrastructure monitoring"""
        if not self.running:
            self.running = True
            self.start()
            print(f"🔍 Infrastructure monitoring started (sampling every {self.interval}s)")
    
    def stop_monitoring(self):
        """Stop infrastructure monitoring"""
        if self.running:
            self.running = False
            self._stop_event.set()
            print("🛑 Infrastructure monitoring stopped")
    
    def run(self):
        """Main monitoring loop"""
        while self.running and not self._stop_event.is_set():
            try:
                # Record infrastructure metrics
                metrics_collector.record_infrastructure_metrics()
                
                # Wait for next interval
                self._stop_event.wait(self.interval)
                
            except Exception as e:
                print(f"Warning: Infrastructure monitoring error: {e}")
                # Continue monitoring despite errors
                self._stop_event.wait(self.interval)

# Global infrastructure monitor instance
infrastructure_monitor = InfrastructureMonitor()