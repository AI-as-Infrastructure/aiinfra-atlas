#!/usr/bin/env python3
"""
Load Test Result Evaluator

Provides pass/fail/borderline evaluation of load test results based on
configurable thresholds for performance, reliability, and user experience.
"""

import json
import time
from typing import Dict, List, Tuple, Any
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

class TestResult(Enum):
    PASS = "PASS"
    BORDERLINE = "BORDERLINE" 
    FAIL = "FAIL"

@dataclass
class Threshold:
    """Performance threshold definition"""
    pass_value: float
    borderline_value: float
    unit: str = ""
    higher_is_better: bool = True
    
    def evaluate(self, value: float) -> TestResult:
        """Evaluate a value against this threshold"""
        if self.higher_is_better:
            if value >= self.pass_value:
                return TestResult.PASS
            elif value >= self.borderline_value:
                return TestResult.BORDERLINE
            else:
                return TestResult.FAIL
        else:
            if value <= self.pass_value:
                return TestResult.PASS
            elif value <= self.borderline_value:
                return TestResult.BORDERLINE
            else:
                return TestResult.FAIL

@dataclass
class EvaluationResult:
    """Result of evaluating a single metric"""
    metric_name: str
    value: float
    result: TestResult
    threshold: Threshold
    message: str

class LoadTestEvaluator:
    """Evaluates load test results against performance thresholds"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize evaluator with configuration"""
        self.config = config or {}
        self.thresholds = self._load_thresholds()
        
    def _load_thresholds(self) -> Dict[str, Threshold]:
        """Load performance thresholds from configuration"""
        # Default thresholds - can be overridden by config
        defaults = {
            # Reliability Metrics
            'success_rate': Threshold(
                pass_value=95.0,      # 95%+ success rate is excellent
                borderline_value=80.0, # 80-95% is acceptable but needs attention
                unit="%",
                higher_is_better=True
            ),
            'error_rate': Threshold(
                pass_value=5.0,       # <5% error rate is excellent
                borderline_value=20.0, # 5-20% needs attention
                unit="%",
                higher_is_better=False
            ),
            
            # Performance Metrics (response times in milliseconds) - Realistic for research tool
            'avg_response_time': Threshold(
                pass_value=20000,     # <20s average is excellent for complex LLM queries
                borderline_value=30000, # 20-30s is acceptable for research
                unit="ms",
                higher_is_better=False
            ),
            'p95_response_time': Threshold(
                pass_value=25000,     # <25s P95 is excellent for research queries
                borderline_value=40000, # 25-40s is acceptable for complex research
                unit="ms",
                higher_is_better=False
            ),
            'p99_response_time': Threshold(
                pass_value=35000,     # <35s P99 is excellent for research
                borderline_value=60000, # 35-60s is acceptable for very complex queries
                unit="ms",
                higher_is_better=False
            ),
            
            # Success-only Performance Metrics
            'avg_success_response_time': Threshold(
                pass_value=20000,     # <20s average for successful requests
                borderline_value=30000, # 20-30s is acceptable for research
                unit="ms",
                higher_is_better=False
            ),
            'p95_success_response_time': Threshold(
                pass_value=25000,     # <25s P95 for successful requests
                borderline_value=40000, # 25-40s is acceptable for research
                unit="ms",
                higher_is_better=False
            ),
            
            # Throughput Metrics - Realistic for research tool with thinking time
            'requests_per_second': Threshold(
                pass_value=0.5,       # >0.5 RPS is excellent for research (realistic thinking time)
                borderline_value=0.2,  # 0.2-0.5 RPS is acceptable for thoughtful research
                unit="req/s",
                higher_is_better=True
            ),
            
            # LLM-Specific Metrics (for streaming responses)
            'first_token_time': Threshold(
                pass_value=5000,      # <5s to first token is excellent
                borderline_value=8000, # 5-8s is acceptable
                unit="ms",
                higher_is_better=False
            ),
            'streaming_completion_time': Threshold(
                pass_value=15000,     # <15s total streaming is excellent
                borderline_value=30000, # 15-30s is acceptable
                unit="ms", 
                higher_is_better=False
            ),
            
            # Infrastructure Metrics
            'websocket_connection_rate': Threshold(
                pass_value=95.0,      # >95% WS connections succeed
                borderline_value=80.0, # 80-95% is acceptable
                unit="%",
                higher_is_better=True
            ),
            'redis_queue_depth': Threshold(
                pass_value=10,        # <10 items in queue is excellent
                borderline_value=50,  # 10-50 items is acceptable
                unit="items",
                higher_is_better=False
            )
        }
        
        # Override with config values if provided
        config_thresholds = self.config.get('performance_targets', {})
        for key, config_threshold in config_thresholds.items():
            if key in defaults:
                # Update threshold values from config
                if 'pass_threshold' in config_threshold:
                    defaults[key].pass_value = config_threshold['pass_threshold']
                if 'borderline_threshold' in config_threshold:
                    defaults[key].borderline_value = config_threshold['borderline_threshold']
                    
        return defaults
    
    def evaluate_locust_stats(self, stats_data: Dict[str, Any]) -> List[EvaluationResult]:
        """Evaluate Locust statistics data"""
        results = []
        
        # Calculate overall metrics from Locust stats
        total_requests = stats_data.get('num_requests', 0)
        total_failures = stats_data.get('num_failures', 0)
        
        if total_requests > 0:
            # Success Rate
            success_rate = ((total_requests - total_failures) / total_requests) * 100
            results.append(self._evaluate_metric('success_rate', success_rate))
            
            # Error Rate
            error_rate = (total_failures / total_requests) * 100
            results.append(self._evaluate_metric('error_rate', error_rate))
            
            # Response Times
            avg_response_time = stats_data.get('avg_response_time', 0)
            if avg_response_time > 0:
                results.append(self._evaluate_metric('avg_response_time', avg_response_time))
            
            # Percentiles
            p95_time = stats_data.get('response_time_percentiles', {}).get('95', 0)
            if p95_time > 0:
                results.append(self._evaluate_metric('p95_response_time', p95_time))
                
            p99_time = stats_data.get('response_time_percentiles', {}).get('99', 0)
            if p99_time > 0:
                results.append(self._evaluate_metric('p99_response_time', p99_time))
            
            # Throughput
            rps = stats_data.get('total_rps', 0)
            if rps > 0:
                results.append(self._evaluate_metric('requests_per_second', rps))
        
        return results
    
    def evaluate_custom_metrics(self, metrics_data: Dict[str, Any]) -> List[EvaluationResult]:
        """Evaluate custom application metrics"""
        results = []
        
        # Calculate overall success/error rates from counters
        counters = metrics_data.get('counters', {})
        if counters:
            total_requests = 0
            total_errors = 0
            
            # Sum up all requests and errors
            for key, value in counters.items():
                if key.endswith('_total'):
                    total_requests += value
                elif key.endswith('_server_error') or key.endswith('_client_error'):
                    total_errors += value
            
            if total_requests > 0:
                success_rate = ((total_requests - total_errors) / total_requests) * 100
                error_rate = (total_errors / total_requests) * 100
                
                results.append(self._evaluate_metric('success_rate', success_rate))
                results.append(self._evaluate_metric('error_rate', error_rate))
        
        # Calculate average response times from response_times data (ALL REQUESTS)
        response_times = metrics_data.get('response_times', {})
        if response_times:
            # Calculate weighted average across all endpoints
            total_weighted_time = 0
            total_requests = 0
            p95_times = []
            
            for endpoint, times in response_times.items():
                if isinstance(times, dict) and '50' in times:
                    # Get request count for this endpoint
                    endpoint_total = counters.get(f"{endpoint}_total", 0)
                    if endpoint_total > 0:
                        # Convert from seconds to milliseconds
                        avg_time_ms = times['50'] * 1000
                        total_weighted_time += avg_time_ms * endpoint_total
                        total_requests += endpoint_total
                        
                        # Collect P95 times
                        if '95' in times:
                            p95_times.append(times['95'] * 1000)
            
            if total_requests > 0:
                avg_response_time = total_weighted_time / total_requests
                results.append(self._evaluate_metric('avg_response_time', avg_response_time))
                
                if p95_times:
                    # Use the worst P95 time (most conservative)
                    max_p95 = max(p95_times)
                    results.append(self._evaluate_metric('p95_response_time', max_p95))
        
        # Calculate success-only response time metrics
        success_response_times = metrics_data.get('success_response_times', {})
        if success_response_times:
            total_weighted_success_time = 0
            total_success_requests = 0
            success_p95_times = []
            
            for endpoint, times in success_response_times.items():
                if isinstance(times, dict) and '50' in times:
                    # Get success count for this endpoint
                    endpoint_success = counters.get(f"{endpoint}_success", 0)
                    if endpoint_success > 0:
                        # Convert from seconds to milliseconds
                        avg_time_ms = times['50'] * 1000
                        total_weighted_success_time += avg_time_ms * endpoint_success
                        total_success_requests += endpoint_success
                        
                        # Collect P95 times
                        if '95' in times:
                            success_p95_times.append(times['95'] * 1000)
            
            if total_success_requests > 0:
                avg_success_response_time = total_weighted_success_time / total_success_requests
                results.append(self._evaluate_metric('avg_success_response_time', avg_success_response_time))
                
                if success_p95_times:
                    max_success_p95 = max(success_p95_times)
                    results.append(self._evaluate_metric('p95_success_response_time', max_success_p95))
        
        # Calculate throughput (RPS)
        throughput_data = metrics_data.get('throughput', {})
        if throughput_data:
            total_rps = sum(throughput_data.values())
            if total_rps > 0:
                results.append(self._evaluate_metric('requests_per_second', total_rps))
        
        # Streaming metrics
        streaming_metrics = metrics_data.get('streaming_metrics', {})
        if streaming_metrics:
            first_token_time = streaming_metrics.get('avg_first_token_time', 0) * 1000  # Convert to ms
            if first_token_time > 0:
                results.append(self._evaluate_metric('first_token_time', first_token_time))
                
            total_streaming_time = streaming_metrics.get('avg_total_time', 0) * 1000  # Convert to ms
            if total_streaming_time > 0:
                results.append(self._evaluate_metric('streaming_completion_time', total_streaming_time))
        
        # WebSocket metrics
        websocket_metrics = metrics_data.get('websocket_metrics', {})
        if websocket_metrics:
            total_connections = websocket_metrics.get('total_connections', 0)
            successful_connections = websocket_metrics.get('successful_connections', 0)
            if total_connections > 0:
                ws_success_rate = (successful_connections / total_connections) * 100
                results.append(self._evaluate_metric('websocket_connection_rate', ws_success_rate))
        
        # Redis metrics
        redis_metrics = metrics_data.get('redis_metrics', {})
        if redis_metrics:
            queue_depth = redis_metrics.get('max_queue_depth', 0)
            if queue_depth >= 0:
                results.append(self._evaluate_metric('redis_queue_depth', queue_depth))
        
        return results
    
    def _evaluate_metric(self, metric_name: str, value: float) -> EvaluationResult:
        """Evaluate a single metric against its threshold"""
        threshold = self.thresholds.get(metric_name)
        if not threshold:
            # Unknown metric - return neutral result
            return EvaluationResult(
                metric_name=metric_name,
                value=value,
                result=TestResult.BORDERLINE,
                threshold=None,
                message=f"No threshold defined for {metric_name}"
            )
        
        result = threshold.evaluate(value)
        message = self._generate_message(metric_name, value, result, threshold)
        
        return EvaluationResult(
            metric_name=metric_name,
            value=value,
            result=result,
            threshold=threshold,
            message=message
        )
    
    def _generate_message(self, metric_name: str, value: float, result: TestResult, threshold: Threshold) -> str:
        """Generate human-readable message for evaluation result"""
        unit = threshold.unit
        
        if result == TestResult.PASS:
            return f"✅ {metric_name}: {value:.1f}{unit} (Excellent)"
        elif result == TestResult.BORDERLINE:
            return f"⚠️  {metric_name}: {value:.1f}{unit} (Needs attention)"
        else:
            return f"❌ {metric_name}: {value:.1f}{unit} (Poor - requires action)"
    
    def evaluate_full_report(self, metrics_file: str) -> Dict[str, Any]:
        """Evaluate a complete load test report"""
        try:
            with open(metrics_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            return {
                'overall_result': TestResult.FAIL,
                'error': f"Failed to load metrics file: {e}",
                'evaluations': []
            }
        
        # Evaluate all metrics
        all_evaluations = []
        
        # Evaluate Locust stats if available
        if 'locust_stats' in data:
            all_evaluations.extend(self.evaluate_locust_stats(data['locust_stats']))
        
        # Evaluate custom metrics
        all_evaluations.extend(self.evaluate_custom_metrics(data))
        
        # Calculate overall result
        overall_result = self._calculate_overall_result(all_evaluations)
        
        # Generate summary
        summary = self._generate_summary(all_evaluations, overall_result)
        
        return {
            'overall_result': overall_result,
            'summary': summary,
            'evaluations': all_evaluations,
            'timestamp': time.time(),
            'metrics_file': metrics_file
        }
    
    def _calculate_overall_result(self, evaluations: List[EvaluationResult]) -> TestResult:
        """Calculate overall test result from individual evaluations"""
        if not evaluations:
            return TestResult.FAIL
        
        # Count results by type
        counts = {result: 0 for result in TestResult}
        for eval_result in evaluations:
            counts[eval_result.result] += 1
        
        total = len(evaluations)
        
        # Weighted scoring system
        pass_weight = 3
        borderline_weight = 1
        fail_weight = -2
        
        score = (counts[TestResult.PASS] * pass_weight + 
                counts[TestResult.BORDERLINE] * borderline_weight + 
                counts[TestResult.FAIL] * fail_weight)
        
        max_score = total * pass_weight
        score_percentage = (score / max_score) * 100 if max_score > 0 else 0
        
        # Determine overall result based on score
        if score_percentage >= 70:
            return TestResult.PASS
        elif score_percentage >= 40:
            return TestResult.BORDERLINE
        else:
            return TestResult.FAIL
    
    def _generate_summary(self, evaluations: List[EvaluationResult], overall_result: TestResult) -> Dict[str, Any]:
        """Generate summary of evaluation results"""
        counts = {result: 0 for result in TestResult}
        for eval_result in evaluations:
            counts[eval_result.result] += 1
        
        # Identify critical issues
        critical_issues = [
            eval_result for eval_result in evaluations 
            if eval_result.result == TestResult.FAIL and 
            eval_result.metric_name in ['success_rate', 'error_rate', 'avg_response_time']
        ]
        
        # Generate recommendations
        recommendations = self._generate_recommendations(evaluations, overall_result)
        
        return {
            'overall_status': overall_result.value,
            'total_metrics': len(evaluations),
            'pass_count': counts[TestResult.PASS],
            'borderline_count': counts[TestResult.BORDERLINE],
            'fail_count': counts[TestResult.FAIL],
            'critical_issues': len(critical_issues),
            'recommendations': recommendations
        }
    
    def _generate_recommendations(self, evaluations: List[EvaluationResult], overall_result: TestResult) -> List[str]:
        """Generate actionable recommendations based on results"""
        recommendations = []
        
        # Check for specific issues
        for eval_result in evaluations:
            if eval_result.result == TestResult.FAIL:
                metric = eval_result.metric_name
                if metric == 'success_rate':
                    recommendations.append("🔴 CRITICAL: High failure rate detected. Check server logs and error responses.")
                elif metric == 'avg_response_time':
                    recommendations.append("🔴 CRITICAL: Slow response times. Consider optimizing database queries and LLM inference.")
                elif metric == 'first_token_time':
                    recommendations.append("⚡ LLM inference is slow. Check model loading and API rate limits.")
                elif metric == 'redis_queue_depth':
                    recommendations.append("🔄 Redis queue is backing up. Scale workers or optimize processing.")
            
            elif eval_result.result == TestResult.BORDERLINE:
                metric = eval_result.metric_name
                if metric == 'success_rate':
                    recommendations.append("⚠️  Monitor error rates closely. Consider implementing retry logic.")
                elif metric == 'p95_response_time':
                    recommendations.append("⚠️  Some requests are slow. Monitor P95/P99 response times.")
        
        # Overall recommendations
        if overall_result == TestResult.FAIL:
            recommendations.append("🚨 Overall test FAILED. Address critical issues before production deployment.")
        elif overall_result == TestResult.BORDERLINE:
            recommendations.append("⚠️  Test results are borderline. Monitor closely and consider optimizations.")
        else:
            recommendations.append("✅ Test passed! System is performing within acceptable limits.")
        
        return recommendations[:10]  # Limit to top 10 recommendations

def format_evaluation_report(evaluation: Dict[str, Any]) -> str:
    """Format evaluation results as human-readable report"""
    lines = []
    lines.append("=" * 80)
    lines.append("🧪 LOAD TEST EVALUATION REPORT")
    lines.append("=" * 80)
    
    # Overall status
    overall = evaluation['summary']['overall_status']
    if overall == "PASS":
        status_emoji = "✅"
        status_color = "PASSED"
    elif overall == "BORDERLINE":
        status_emoji = "⚠️"
        status_color = "BORDERLINE"
    else:
        status_emoji = "❌"
        status_color = "FAILED"
    
    lines.append(f"\n{status_emoji} OVERALL RESULT: {status_color}")
    lines.append("")
    
    # Summary stats
    summary = evaluation['summary']
    lines.append("📊 SUMMARY:")
    lines.append(f"   Total Metrics Evaluated: {summary['total_metrics']}")
    lines.append(f"   ✅ Passed: {summary['pass_count']}")
    lines.append(f"   ⚠️  Borderline: {summary['borderline_count']}")
    lines.append(f"   ❌ Failed: {summary['fail_count']}")
    if summary['critical_issues'] > 0:
        lines.append(f"   🔴 Critical Issues: {summary['critical_issues']}")
    lines.append("")
    
    # Individual results
    lines.append("📈 DETAILED RESULTS:")
    for eval_result in evaluation['evaluations']:
        lines.append(f"   {eval_result.message}")
    lines.append("")
    
    # Recommendations
    if evaluation['summary']['recommendations']:
        lines.append("💡 RECOMMENDATIONS:")
        for rec in evaluation['summary']['recommendations']:
            lines.append(f"   {rec}")
    lines.append("")
    
    lines.append("=" * 80)
    return "\n".join(lines)