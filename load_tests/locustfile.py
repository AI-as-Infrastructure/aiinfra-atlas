#!/usr/bin/env python3
"""
ATLAS Load Testing with Locust

Main entry point for running load tests against ATLAS application.
Supports multiple user types, scenarios, and environments.

Usage:
    # Basic load test
    locust -f locustfile.py --host=http://localhost:5173

    # Staging environment
    locust -f locustfile.py --host=https://192.168.20.17 --users=30 --spawn-rate=2 --run-time=15m

    # Specific scenario
    locust -f locustfile.py --host=https://192.168.20.17 --tags=streaming --users=20 --run-time=10m

    # With custom configuration
    LOAD_TEST_CONFIG=staging locust -f locustfile.py --host=https://192.168.20.17
"""

import os
import sys
import json
import yaml
import time
import signal
import urllib3
from pathlib import Path

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from locust import events
from locust.env import Environment
from utils.metrics import metrics_collector
from utils.evaluator import LoadTestEvaluator, format_evaluation_report

# Import core user classes (removed WebSocket and feedback testing)
from tasks.question_tasks import QuestionSubmissionUser

# Configuration loading
def load_config():
    """Load configuration based on environment"""
    config_name = os.getenv('LOAD_TEST_CONFIG', 'staging')
    config_path = Path(__file__).parent / 'config' / f'{config_name}.yaml'
    
    # Load corresponding .env file
    env_file = Path(__file__).parent.parent / 'config' / f'.env.{config_name}'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"Loaded environment from: {env_file}")
    
    if not config_path.exists():
        print(f"Warning: Config file {config_path} not found, using defaults")
        return {}
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            # Simple environment variable substitution
            for key, value in os.environ.items():
                content = content.replace(f"${{{key}}}", value)
            return yaml.safe_load(content)
    except Exception as e:
        print(f"Error loading config: {e}")
        return {}

# Load configuration
config = load_config()

# Event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test environment"""
    print("🚀 Starting ATLAS Load Test")
    print(f"Environment: {config.get('environment', {}).get('name', 'default')}")
    print(f"Host: {environment.host}")
    print(f"Users: {environment.runner.target_user_count if hasattr(environment.runner, 'target_user_count') else 'N/A'}")
    
    # Check authentication setting
    auth_enabled = os.getenv('VITE_USE_COGNITO_AUTH', 'true').lower()
    if auth_enabled == 'true':
        print("\n❌ ERROR: Authentication is enabled!")
        print("Load tests require VITE_USE_COGNITO_AUTH=false in your .env file.")
        print("\nTo fix this:")
        config_name = os.getenv('LOAD_TEST_CONFIG', 'staging')
        print(f"1. Edit config/.env.{config_name}")
        print("2. Set VITE_USE_COGNITO_AUTH=false")
        print("3. Restart your application")
        print("4. Re-run the load test")
        print("\n⚠️  Remember to change it back to true after testing in production!")
        raise SystemExit(1)
    else:
        print("✅ Authentication disabled - ready for load testing")
    
    # Reset metrics collector
    metrics_collector.reset()
    
    # Set up environment variables based on config
    if config.get('env_vars'):
        for key, value in config['env_vars'].items():
            if not os.getenv(key):  # Don't override existing env vars
                os.environ[key] = str(value)

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Clean up and export results"""
    print("🛑 Load Test Completed")
    
    # Export metrics
    timestamp = int(time.time())
    report_dir = Path(__file__).parent / 'reports'
    report_dir.mkdir(exist_ok=True)
    
    # Export detailed metrics
    metrics_file = report_dir / f'metrics_{timestamp}.json'
    metrics_collector.export_to_file(str(metrics_file))
    print(f"📊 Metrics exported to: {metrics_file}")
    
    # Print basic summary
    summary = metrics_collector.get_summary()
    print(f"\n📈 Basic Summary: {sum(summary['counters'].values())} total requests")
    
    # Evaluate results and generate actionable report
    try:
        evaluator = LoadTestEvaluator(config)
        evaluation = evaluator.evaluate_full_report(str(metrics_file))
        
        # Print formatted evaluation report
        print("\n" + format_evaluation_report(evaluation))
        
        # Export evaluation report
        eval_file = report_dir / f'evaluation_{timestamp}.json'
        with open(eval_file, 'w') as f:
            # Convert TestResult enums to strings for JSON serialization
            eval_data = evaluation.copy()
            eval_data['overall_result'] = evaluation['overall_result'].value
            for eval_result in eval_data['evaluations']:
                eval_result.result = eval_result.result.value
            json.dump(eval_data, f, indent=2, default=str)
        
        print(f"📋 Evaluation report saved to: {eval_file}")
        
        # Generate comprehensive performance report
        try:
            from utils.report_generator import PerformanceReportGenerator
            report_generator = PerformanceReportGenerator()
            perf_report_file = report_dir / f'performance_report_{timestamp}.md'
            report_generator.generate_report(str(perf_report_file))
            print(f"📄 Performance report saved to: {perf_report_file}")
        except Exception as report_error:
            print(f"⚠️  Failed to generate performance report: {report_error}")
        
        # Set exit code based on results
        if evaluation['overall_result'].value == 'FAIL':
            print("\n🚨 Load test FAILED - exiting with error code")
            sys.exit(1)
        elif evaluation['overall_result'].value == 'BORDERLINE':
            print("\n⚠️  Load test results are BORDERLINE - monitor closely")
            
    except Exception as e:
        print(f"\n❌ Error during evaluation: {e}")
        print("Raw metrics are still available in the metrics file.")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Handle all requests (success and failure)"""
    if exception:
        # Handle failed requests
        if hasattr(exception, '__str__'):
            error_msg = str(exception)
            # Could log to file or send to monitoring system
            pass
    else:
        # Handle successful requests
        # Custom success handling if needed
        pass

# Graceful shutdown handling
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Received shutdown signal, stopping test gracefully...")
    # The test will stop naturally, cleanup will happen in on_test_stop

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Set user class weights - Focus on core RAG functionality only
QuestionSubmissionUser.weight = 100  # Only test core streaming questions

# Configuration validation
def validate_config():
    """Validate configuration and warn about issues"""
    warnings = []
    
    # Check host configuration
    if config.get('environment', {}).get('host'):
        expected_host = config['environment']['host']
        # Note: actual host will be set via command line --host parameter
        pass
    
    # Check performance targets
    targets = config.get('load_test', {}).get('performance_targets', {})
    if targets.get('response_time_p95', 0) > 10000:
        warnings.append("P95 response time target is very high (>10s)")
    
    # Check safety limits
    safety = config.get('safety', {})
    max_users = safety.get('max_concurrent_users', 100)
    if max_users > 100:
        warnings.append(f"Max concurrent users is high ({max_users}), ensure adequate resources")
    
    if warnings:
        print("⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"   - {warning}")

# Validate configuration on load
validate_config()

# Helper functions for scenario-based testing
def run_scenario(scenario_name):
    """Run a specific scenario from configuration"""
    scenarios = config.get('scenarios', {})
    if scenario_name not in scenarios:
        print(f"❌ Scenario '{scenario_name}' not found")
        return
    
    scenario = scenarios[scenario_name]
    print(f"🎯 Running scenario: {scenario.get('description', scenario_name)}")
    
    # This would be used with custom runner implementation
    # For now, scenarios are selected via command-line tags

# Print available scenarios
def print_scenarios():
    """Print available test scenarios"""
    scenarios = config.get('scenarios', {})
    if scenarios:
        print("\n📋 Available Scenarios:")
        for name, details in scenarios.items():
            print(f"   {name}: {details.get('description', 'No description')}")
            print(f"      Duration: {details.get('duration', 'N/A')}")
            print(f"      Users: {details.get('users', 'N/A')}")
            if 'tags' in details:
                print(f"      Tags: {', '.join(details['tags'])}")
            print()

if __name__ == "__main__":
    # Print information when run directly
    print("🔍 ATLAS Load Testing Configuration")
    print(f"Config: {os.getenv('LOAD_TEST_CONFIG', 'staging')}")
    
    if '--help' in sys.argv or '-h' in sys.argv:
        print(__doc__)
        print_scenarios()
        sys.exit(0)
    
    print("\n🚀 Ready to run load tests!")
    print("Use: locust -f locustfile.py --host=<target_host>")
    print_scenarios()