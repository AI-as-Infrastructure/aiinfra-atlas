#!/usr/bin/env python3
"""
Optimized ATLAS Load Testing for 15 Concurrent Users
Enhanced with cache-busting, expanded question pool, and realistic user behavior patterns
"""

import os
import sys
import json
import yaml
import time
import signal
import urllib3
from pathlib import Path

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from locust import events
from locust.env import Environment
from utils.metrics import metrics_collector
from utils.evaluator import LoadTestEvaluator, format_evaluation_report

# Import optimized user classes
from tasks.optimized_question_tasks import OptimizedQuestionUser
from tasks.feedback_tasks import FeedbackUser
from tasks.websocket_tasks import WebSocketUser

# Configuration loading
def load_config():
    """Load optimized configuration"""
    config_name = os.getenv('LOAD_TEST_CONFIG', 'optimized_staging')
    config_path = Path(__file__).parent / 'config' / f'{config_name}.yaml'
    
    # Load corresponding .env file
    env_file = Path(__file__).parent.parent / 'config' / f'.env.staging'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"📁 Loaded environment from: {env_file}")
    
    if not config_path.exists():
        print(f"⚠️  Config file {config_path} not found, using defaults")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            # Environment variable substitution
            for key, value in os.environ.items():
                content = content.replace(f"${{{key}}}", value)
            return yaml.safe_load(content)
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        return {}

# Load configuration
config = load_config()

# Event handlers
@events.test_start.add_listener
def on_optimized_test_start(environment, **kwargs):
    """Initialize optimized test environment"""
    print("🚀 Starting Optimized ATLAS Load Test")
    print(f"📊 Config: {config.get('environment', {}).get('name', 'optimized-staging')}")
    print(f"🎯 Target: {environment.host}")
    print(f"👥 Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    
    # Enhanced configuration display
    load_test_config = config.get('load_test', {})
    print(f"⏱️  Duration: {load_test_config.get('duration', 'N/A')}")
    print(f"📈 Spawn Rate: {load_test_config.get('spawn_rate', 'N/A')}")
    print(f"🎯 Target RPS: {load_test_config.get('performance_targets', {}).get('requests_per_second', 'N/A')}")
    
    # Cache-busting configuration
    cache_config = config.get('cache_busting', {})
    if cache_config.get('enabled', False):
        print(f"🔄 Cache-busting: Enabled")
        print(f"   Question pool: {cache_config.get('question_pool_size', 'N/A')}")
        print(f"   Variation rate: {cache_config.get('variation_rate', 'N/A')}%")
        print(f"   Cache-bust rate: {cache_config.get('cache_bust_rate', 'N/A')}%")
    
    # Authentication check
    auth_enabled = os.getenv('VITE_USE_COGNITO_AUTH', 'true').lower()
    if auth_enabled == 'true':
        print("\n❌ ERROR: Authentication is enabled!")
        print("Optimized load tests require VITE_USE_COGNITO_AUTH=false")
        print("\nTo fix this:")
        print("1. Edit config/.env.staging")
        print("2. Set VITE_USE_COGNITO_AUTH=false")
        print("3. Restart your application")
        raise SystemExit(1)
    else:
        print("✅ Authentication disabled - ready for optimized load testing")
    
    # Reset metrics
    metrics_collector.reset()
    
    # Set environment variables
    env_vars = config.get('env_vars', {})
    for key, value in env_vars.items():
        if not os.getenv(key):
            os.environ[key] = str(value)
    
    print("\n🔥 Optimized load test starting...")

@events.test_stop.add_listener
def on_optimized_test_stop(environment, **kwargs):
    """Enhanced cleanup and reporting"""
    print("\n🛑 Optimized Load Test Completed")
    
    # Export enhanced metrics
    timestamp = int(time.time())
    report_dir = Path(__file__).parent / 'reports'
    report_dir.mkdir(exist_ok=True)
    
    # Export detailed metrics
    metrics_file = report_dir / f'optimized_metrics_{timestamp}.json'
    metrics_collector.export_to_file(str(metrics_file))
    print(f"📊 Detailed metrics exported to: {metrics_file}")
    
    # Enhanced summary
    summary = metrics_collector.get_summary()
    total_requests = sum(summary['counters'].values())
    print(f"\n📈 Test Summary:")
    print(f"   Total Requests: {total_requests}")
    print(f"   Duration: {summary.get('duration', 'N/A')}s")
    print(f"   Average RPS: {total_requests / summary.get('duration', 1):.2f}")
    
    # Performance targets evaluation
    try:
        evaluator = LoadTestEvaluator(config)
        evaluation = evaluator.evaluate_full_report(str(metrics_file))
        
        # Enhanced evaluation report
        print("\n" + "="*60)
        print("🎯 OPTIMIZED LOAD TEST EVALUATION REPORT")
        print("="*60)
        print(format_evaluation_report(evaluation))
        
        # Export evaluation
        eval_file = report_dir / f'optimized_evaluation_{timestamp}.json'
        with open(eval_file, 'w') as f:
            eval_data = evaluation.copy()
            eval_data['overall_result'] = evaluation['overall_result'].value
            for eval_result in eval_data['evaluations']:
                eval_result.result = eval_result.result.value
            json.dump(eval_data, f, indent=2, default=str)
        
        print(f"\n📋 Evaluation report saved to: {eval_file}")
        
        # Memory optimization results
        memory_info = summary.get('memory_info', {})
        if memory_info:
            print(f"\n💾 Memory Optimization Results:")
            print(f"   Peak Memory: {memory_info.get('peak_memory', 'N/A')}%")
            print(f"   Cache Hit Rate: {memory_info.get('cache_hit_rate', 'N/A')}%")
            print(f"   GC Collections: {memory_info.get('gc_collections', 'N/A')}")
        
        # Cache-busting effectiveness
        cache_info = summary.get('cache_info', {})
        if cache_info:
            print(f"\n🔄 Cache-busting Effectiveness:")
            print(f"   Unique Questions: {cache_info.get('unique_questions', 'N/A')}")
            print(f"   Cache Misses: {cache_info.get('cache_misses', 'N/A')}%")
            print(f"   Parameter Variations: {cache_info.get('parameter_variations', 'N/A')}")
        
        # Set exit code based on results
        if evaluation['overall_result'].value == 'FAIL':
            print("\n🚨 OPTIMIZED LOAD TEST FAILED")
            print("   Check the evaluation report for detailed failure analysis")
            sys.exit(1)
        elif evaluation['overall_result'].value == 'BORDERLINE':
            print("\n⚠️  OPTIMIZED LOAD TEST RESULTS ARE BORDERLINE")
            print("   Performance is acceptable but monitor closely")
        else:
            print("\n✅ OPTIMIZED LOAD TEST PASSED")
            print("   System performance meets all targets")
            
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        print("Raw metrics are available in the metrics file")

@events.request.add_listener
def on_optimized_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Enhanced request monitoring"""
    # Track cache-busting effectiveness
    if 'cache-bust' in name.lower():
        metrics_collector.record_custom_metric('cache_busting_requests', 1)
    
    # Track user behavior patterns
    if hasattr(kwargs, 'user_type'):
        user_type = kwargs.get('user_type', 'unknown')
        metrics_collector.record_custom_metric(f'user_type_{user_type}', 1)
    
    # Track response time distributions
    if response_time:
        if response_time < 1000:
            metrics_collector.record_custom_metric('fast_responses', 1)
        elif response_time < 5000:
            metrics_collector.record_custom_metric('medium_responses', 1)
        else:
            metrics_collector.record_custom_metric('slow_responses', 1)

# Set optimized user class weights
OptimizedQuestionUser.weight = 80  # Primary optimized user
FeedbackUser.weight = 15           # Realistic feedback rate
WebSocketUser.weight = 5           # Light WebSocket testing

# Configuration validation
def validate_optimized_config():
    """Validate optimized configuration"""
    warnings = []
    
    # Check load test parameters
    load_test = config.get('load_test', {})
    target_users = load_test.get('target_users', 15)
    
    if target_users > 25:
        warnings.append(f"Target users ({target_users}) is high for optimization testing")
    
    # Check performance targets
    perf_targets = load_test.get('performance_targets', {})
    p95_target = perf_targets.get('response_time_p95', 10000)
    
    if p95_target > 15000:
        warnings.append(f"P95 response time target ({p95_target}ms) may be too lenient")
    
    # Check cache-busting configuration
    cache_config = config.get('cache_busting', {})
    if not cache_config.get('enabled', False):
        warnings.append("Cache-busting is disabled - may not test realistic scenarios")
    
    if warnings:
        print("⚠️  Optimized Configuration Warnings:")
        for warning in warnings:
            print(f"   - {warning}")

# Validate configuration
validate_optimized_config()

# Graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print("\n🛑 Received shutdown signal, stopping optimized test gracefully...")

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Helper functions
def print_optimized_scenarios():
    """Print available optimized scenarios"""
    scenarios = config.get('scenarios', {})
    if scenarios:
        print("\n📋 Available Optimized Scenarios:")
        for name, details in scenarios.items():
            print(f"   🎯 {name}:")
            print(f"      Description: {details.get('description', 'No description')}")
            print(f"      Duration: {details.get('duration', 'N/A')}")
            print(f"      Users: {details.get('users', 'N/A')}")
            print(f"      Spawn Rate: {details.get('spawn_rate', 'N/A')}")
            if 'tags' in details:
                print(f"      Tags: {', '.join(details['tags'])}")
            print()

def print_optimization_summary():
    """Print optimization summary"""
    print("\n🔧 Optimization Summary:")
    print("   ✅ Enhanced data generators with 100+ diverse questions")
    print("   ✅ Cache-busting with timestamp and parameter variations")
    print("   ✅ Realistic user behavior patterns (5 user types)")
    print("   ✅ Optimized for k20 fetch-k (33% memory reduction)")
    print("   ✅ Enhanced metrics collection and evaluation")
    print("   ✅ Weighted corpus filter distribution")
    print("   ✅ Follow-up question patterns")
    print("   ✅ Variable response time targets")

if __name__ == "__main__":
    print("🔍 Optimized ATLAS Load Testing Configuration")
    print(f"📊 Config: {os.getenv('LOAD_TEST_CONFIG', 'optimized_staging')}")
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        print_optimized_scenarios()
        print_optimization_summary()
        sys.exit(0)
    
    print("\n🚀 Ready for optimized load testing!")
    print("Usage: locust -f optimized_locustfile.py --host=<target_host>")
    print_optimized_scenarios()
    print_optimization_summary()