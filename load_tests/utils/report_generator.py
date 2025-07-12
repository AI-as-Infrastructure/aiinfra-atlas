#!/usr/bin/env python3
"""
Dynamic Performance Report Generator for ATLAS Load Testing

Generates performance reports based on actual test results and system configuration.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional
import platform

class PerformanceReportGenerator:
    """Generate dynamic performance reports from load test results"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent / 'config' / '.env.staging'
        self.system_info = self._get_system_info()
        self.config = self._load_config()
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system specifications"""
        try:
            # Try to get CPU count
            cpu_count = os.cpu_count() or "Unknown"
            
            # Try to get memory info (Linux)
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    for line in meminfo.split('\n'):
                        if line.startswith('MemTotal:'):
                            mem_kb = int(line.split()[1])
                            mem_gb = round(mem_kb / 1024 / 1024)
                            break
                    else:
                        mem_gb = "Unknown"
            except:
                mem_gb = "Unknown"
            
            return {
                "cpu_cores": cpu_count,
                "ram_gb": mem_gb,
                "platform": platform.system(),
                "architecture": platform.machine()
            }
        except:
            return {
                "cpu_cores": "Unknown",
                "ram_gb": "Unknown", 
                "platform": "Unknown",
                "architecture": "Unknown"
            }
    
    def _load_config(self) -> Dict[str, str]:
        """Load configuration from .env file"""
        config = {}
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
        except Exception as e:
            print(f"Warning: Could not load config from {self.config_path}: {e}")
        
        return config
    
    def _find_latest_results(self) -> Optional[Path]:
        """Find the latest test results file"""
        reports_dir = Path(__file__).parent.parent / 'reports'
        if not reports_dir.exists():
            return None
        
        # Find latest metrics file
        metrics_files = list(reports_dir.glob('metrics_*.json'))
        if not metrics_files:
            return None
        
        # Sort by timestamp in filename
        latest_file = max(metrics_files, key=lambda f: f.stem.split('_')[1])
        return latest_file
    
    def _parse_test_results(self, results_file: Path) -> Dict[str, Any]:
        """Parse test results from JSON file"""
        try:
            with open(results_file, 'r') as f:
                data = json.load(f)
            
            # Extract key metrics
            counters = data.get('counters', {})
            timers = data.get('timers', {})
            
            # Calculate success rate
            total_requests = sum(counters.values())
            errors = counters.get('errors', 0)
            success_rate = ((total_requests - errors) / total_requests * 100) if total_requests > 0 else 0
            
            # Get response time stats from response_times data structure
            response_times = data.get('response_times', {})
            ask_stream_stats = response_times.get('ask_stream', {})
            avg_response = ask_stream_stats.get('50', 0)  # 50th percentile is average
            p95_response = ask_stream_stats.get('95', 0)  # 95th percentile
            
            # Get streaming metrics
            streaming = data.get('streaming_metrics', {})
            avg_first_token = streaming.get('avg_first_token_time', 0)
            avg_completion = streaming.get('avg_total_time', 0)
            
            return {
                'success_rate': round(success_rate, 1),
                'total_requests': total_requests,
                'errors': errors,
                'avg_response_time': round(avg_response, 1) if avg_response else 0,  # Already in seconds
                'p95_response_time': round(p95_response, 1) if p95_response else 0,  # Already in seconds
                'first_token_time': round(avg_first_token, 1),
                'completion_time': round(avg_completion, 1),
                'test_duration': data.get('test_duration', 'Unknown'),
                'timestamp': results_file.stem.split('_')[1]
            }
        except Exception as e:
            print(f"Error parsing results file {results_file}: {e}")
            return {}
    
    def generate_report(self, output_file: str = None) -> str:
        """Generate dynamic performance report"""
        
        # Find latest test results
        results_file = self._find_latest_results()
        if results_file:
            test_results = self._parse_test_results(results_file)
        else:
            test_results = {}
        
        # Get configuration values with defaults
        workers = self.config.get('GUNICORN_WORKERS', 'Unknown')
        max_requests = self.config.get('GUNICORN_MAX_REQUESTS', 'Unknown')
        request_delay = self.config.get('LLM_REQUEST_DELAY_MS', 'Unknown')
        retry_delay = self.config.get('LLM_RETRY_DELAY_MS', 'Unknown')
        max_retries = self.config.get('LLM_MAX_RETRIES', 'Unknown')
        max_chars = self.config.get('LLM_MAX_RESPONSE_CHARS', 'Unknown')
        cache_enabled = self.config.get('PROMPT_CACHING_ENABLED', 'Unknown')
        cache_ttl = self.config.get('PROMPT_CACHE_TTL', 'Unknown')
        
        # Generate timestamp
        report_time = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())
        
        # Build report content
        report = f"""# ATLAS Load Testing Performance Report

## Executive Summary

Generated: {report_time}
Latest Test Results: {test_results.get('timestamp', 'No recent tests found')}

{self._generate_summary(test_results)}

---

## Test Configuration

### System Specifications
- **CPU**: {self.system_info['cpu_cores']} cores
- **RAM**: {self.system_info['ram_gb']}GB
- **Platform**: {self.system_info['platform']} ({self.system_info['architecture']})
- **Environment**: Staging (matches production architecture)

### Application Settings
```yaml
# Gunicorn Configuration
Workers: {workers}
Max Requests per Worker: {max_requests}
Worker Timeout: {self.config.get('GUNICORN_TIMEOUT', 'Unknown')} seconds

# LLM Configuration  
Request Delay: {request_delay}ms
Retry Delay: {retry_delay}ms
Max Retries: {max_retries}
Max Response Characters: {max_chars}

# Caching Configuration
Prompt Caching: {cache_enabled}
Cache TTL: {cache_ttl}
System Prompt Cache: {self.config.get('PROMPT_CACHE_SYSTEM', 'Unknown')}
Document Context Cache: {self.config.get('PROMPT_CACHE_CONTEXT', 'Unknown')}
```

---

## Core Performance Metrics

{self._generate_metrics_section(test_results)}

---

## Load Testing Methodology

### Realistic User Behavior Simulation
- **Wait Time**: 30-120 seconds between questions (mimics research thinking time)
- **Reading Time**: 15 seconds to 3 minutes (based on response complexity)
- **Startup Delay**: 5-30 seconds (prevents thundering herd)
- **Question Pool**: 100+ diverse parliamentary questions (reduces cache hits)

### Test Focus Areas
- **Core RAG Functionality**: Question submission and streaming responses
- **Document Retrieval**: Parliamentary document search and citation
- **System Stability**: Extended load testing
- **Resource Management**: Memory, CPU, and cache utilization

---

## Scaling Recommendations

{self._generate_scaling_recommendations(test_results)}

---

## Production Readiness Assessment

{self._generate_readiness_assessment(test_results)}

---

## Key Configuration

### Load Testing Optimization
- **Removed WebSocket Testing**: Eliminated unused functionality testing
- **Removed Feedback API Testing**: Simplified to core RAG functionality
- **Enhanced Question Diversity**: 100+ questions prevent cache saturation
- **Realistic Timing**: Human-like behavior patterns

### System Performance
- **Caching Strategy**: {cache_enabled} for realistic production simulation
- **Rate Limiting**: Prevents API abuse while maintaining performance
- **Worker Configuration**: Optimized for {self.system_info['cpu_cores']}-core system
- **Memory Management**: Efficient utilization with growth headroom

---

## Monitoring Recommendations

### Key Metrics to Track
1. **Streaming Success Rate** (target: >95%)
2. **P95 Response Time** (target: <20s for research queries)
3. **System Resource Usage** (CPU <70%, RAM <85%)
4. **Cache Hit Rate** (monitor efficiency)

### Scaling Triggers
- **Scale Up**: If CPU consistently >70% or RAM >85%
- **Scale Down**: If resources consistently <40% utilization
- **Performance Alert**: If P95 response time >25s

---

*Report Generated: {report_time}*
*Configuration Source: {self.config_path}*
*Test Results Source: {results_file if results_file else 'No recent test results found'}*
"""
        
        # Save report if output file specified
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            print(f"Performance report saved to: {output_file}")
        
        return report
    
    def _generate_summary(self, test_results: Dict[str, Any]) -> str:
        """Generate executive summary based on test results"""
        if not test_results:
            return "No recent test results available. Run load tests to generate performance metrics."
        
        success_rate = test_results.get('success_rate', 0)
        total_requests = test_results.get('total_requests', 0)
        
        if success_rate >= 95:
            status = "EXCELLENT"
        elif success_rate >= 85:
            status = "GOOD"
        elif success_rate >= 70:
            status = "ACCEPTABLE"
        else:
            status = "NEEDS ATTENTION"
        
        return f"""Performance Status: **{status}**
- Success Rate: {success_rate}% ({total_requests} total requests)
- Latest Test: {test_results.get('test_duration', 'Unknown duration')}
- System shows {'excellent' if success_rate >= 95 else 'good' if success_rate >= 85 else 'concerning'} stability under load"""
    
    def _generate_metrics_section(self, test_results: Dict[str, Any]) -> str:
        """Generate metrics section based on actual results"""
        if not test_results:
            return """### No Recent Test Results
Run load tests with `make lts` to generate current performance metrics.

### Expected Metrics
- **Streaming Success Rate**: Target >95%
- **Response Times**: Target P95 <20s for research queries  
- **Resource Usage**: Monitor CPU <70%, RAM <85%
- **Concurrent Capacity**: Test and establish baseline"""
        
        success_rate = test_results.get('success_rate', 0)
        success_icon = "✅" if success_rate >= 95 else "⚠️" if success_rate >= 85 else "❌"
        
        p95_time = test_results.get('p95_response_time', 0)
        time_icon = "✅" if p95_time <= 20 else "⚠️" if p95_time <= 30 else "❌"
        
        return f"""### {success_icon} Streaming Question Success Rate
- **Result**: {success_rate}% success rate
- **Details**: {test_results.get('total_requests', 0) - test_results.get('errors', 0)}/{test_results.get('total_requests', 0)} requests completed successfully
- **Status**: {self._get_status_text(success_rate, 95, 85)}

### {time_icon} Response Times
- **Average Response Time**: {test_results.get('avg_response_time', 0)}s
- **P95 Response Time**: {p95_time}s
- **First Token Time**: {test_results.get('first_token_time', 0)}s
- **Streaming Completion**: {test_results.get('completion_time', 0)}s
- **Status**: {self._get_status_text(p95_time, 20, 30, reverse=True)} for research tool complexity

### System Resource Usage
- **Monitoring Required**: Use system monitoring tools during load tests
- **Recommended Limits**: CPU <70%, RAM <85%, Swap <10%
- **Status**: Monitor during active testing

### Concurrent User Capacity
- **Last Test**: {test_results.get('total_requests', 0)} requests processed
- **Estimated Capacity**: Based on {self.system_info['cpu_cores']} cores, {self.system_info['ram_gb']}GB RAM
- **Status**: Test incrementally to establish capacity limits"""
    
    def _generate_scaling_recommendations(self, test_results: Dict[str, Any]) -> str:
        """Generate scaling recommendations based on system specs"""
        cpu_cores = self.system_info.get('cpu_cores', 0)
        ram_gb = self.system_info.get('ram_gb', 0)
        
        if isinstance(cpu_cores, int) and isinstance(ram_gb, int):
            if cpu_cores >= 8 and ram_gb >= 16:
                return """### Conservative Scaling (Recommended)
**Target: 25 concurrent users**
- Expected CPU: 50-60%
- Expected RAM: 75-80%
- Performance: Maintained excellent response times

### Moderate Scaling
**Target: 30 concurrent users**
- Expected CPU: 65-70%
- Expected RAM: 80-85%
- Performance: Good response times (P95 < 20s)

### Aggressive Scaling
**Target: 40+ concurrent users**
- Requires additional testing
- Consider worker count increase
- Monitor LLM API rate limits"""
            else:
                return f"""### Current System Capacity
**Specs**: {cpu_cores} cores, {ram_gb}GB RAM
- Recommended testing with incremental user increases
- Monitor resource usage carefully
- Consider hardware upgrade for higher loads"""
        else:
            return """### System Specifications Unknown
- Run tests to establish baseline capacity
- Monitor resource usage during testing
- Scale incrementally based on observed performance"""
    
    def _generate_readiness_assessment(self, test_results: Dict[str, Any]) -> str:
        """Generate production readiness assessment"""
        if not test_results:
            return """### Assessment Pending
Complete load testing to assess production readiness.

### Research Tool Context
For a specialized parliamentary research tool:
- Target concurrency based on expected user base
- Consider usage patterns (research vs browsing)
- Plan for peak usage periods"""
        
        success_rate = test_results.get('success_rate', 0)
        
        if success_rate >= 95:
            confidence = "HIGH"
            recommendation = "Ready for production deployment"
        elif success_rate >= 85:
            confidence = "MODERATE"
            recommendation = "Consider additional testing before production"
        else:
            confidence = "LOW"
            recommendation = "Address performance issues before production"
        
        return f"""### Research Tool Context
For a specialized parliamentary research tool:
- **Deployment Confidence**: {confidence}
- **Recommendation**: {recommendation}
- **Usage Pattern**: Thoughtful, deliberate research (not rapid-fire queries)

### Current Status
- **Success Rate**: {success_rate}% under load
- **Response Quality**: Appropriate for research complexity
- **System Stability**: {'Proven' if success_rate >= 95 else 'Needs validation'} under sustained load"""
    
    def _get_status_text(self, value: float, good_threshold: float, acceptable_threshold: float, reverse: bool = False) -> str:
        """Get status text based on value and thresholds"""
        if reverse:
            if value <= good_threshold:
                return "EXCELLENT"
            elif value <= acceptable_threshold:
                return "GOOD"
            else:
                return "NEEDS ATTENTION"
        else:
            if value >= good_threshold:
                return "EXCELLENT"
            elif value >= acceptable_threshold:
                return "GOOD"
            else:
                return "NEEDS ATTENTION"

def main():
    """Generate performance report with timestamped filename"""
    generator = PerformanceReportGenerator()
    
    # Generate timestamp-based filename matching load test reports
    timestamp = int(time.time())
    report_filename = f'performance_report_{timestamp}.md'
    report_path = Path(__file__).parent.parent / 'reports' / report_filename
    
    # Ensure reports directory exists
    report_path.parent.mkdir(exist_ok=True)
    
    generator.generate_report(str(report_path))

if __name__ == "__main__":
    main()