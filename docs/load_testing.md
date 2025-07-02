# ATLAS Load Testing Framework

A comprehensive load testing framework for the ATLAS application using Locust, designed to test question submission, feedback collection, WebSocket connections, and async processing capabilities.

## Quick Start

```bash
# Install dependencies (from project root - uses main requirements.txt)
pip install -r config/requirements.txt

# Run basic load test against staging
cd load_tests
LOAD_TEST_CONFIG=staging locust -f locustfile.py --users=30 --spawn-rate=2 --run-time=15m

# Run specific scenario  
LOAD_TEST_CONFIG=staging locust -f locustfile.py --tags=streaming --users=20 --run-time=10m
```

## Architecture

```
load_tests/
├── locustfile.py           # Main Locust configuration
├── config/                 # Environment configurations
│   ├── staging.yaml       # Staging environment settings
│   ├── production.yaml    # Production environment settings
│   └── scenarios.yaml     # Test scenario definitions
├── tasks/                 # User behavior definitions
│   ├── question_tasks.py  # Q&A endpoint testing
│   ├── feedback_tasks.py  # Feedback submission testing
│   ├── websocket_tasks.py # WebSocket connection testing
│   └── async_tasks.py     # Async processing and Redis testing
├── utils/                 # Utility modules
│   ├── auth.py           # Authentication handling
│   ├── data_generators.py # Test data generation
│   └── metrics.py        # Custom metrics collection
└── reports/              # Test results and metrics

# Dependencies are managed in the main config/requirements.txt
```

## User Types

### 1. QuestionSubmissionUser (Primary Load)
- **Weight:** 60% of total users
- **Behavior:** Submits parliamentary questions via streaming and sync endpoints
- **Key Tasks:**
  - `POST /api/ask/stream` (40% of requests) - Streaming Q&A
  - `POST /api/ask` (20% of requests) - Synchronous Q&A
  - `POST /api/query` (10% of requests) - Document search
  - Health checks and diagnostics (remaining)

### 2. FeedbackUser & MixedFeedbackUser
- **Weight:** 35% combined
- **Behavior:** Submits feedback on Q&A interactions
- **Key Tasks:**
  - `POST /api/feedback` - HTTP feedback submission
  - WebSocket feedback via `/ws/{session_id}`
  - Bulk feedback operations
  - Mixed users combine questions with feedback

### 3. WebSocketUser & AsyncWebSocketUser
- **Weight:** 4% combined
- **Behavior:** Tests real-time connections and async status monitoring
- **Key Tasks:**
  - WebSocket connection establishment
  - Real-time feedback submission
  - Async request status monitoring
  - Connection stability testing

### 4. AsyncProcessingUser & RedisMonitorUser
- **Weight:** 3% combined
- **Behavior:** Tests async processing pipeline and Redis queue
- **Key Tasks:**
  - `POST /api/ask/async` - Async request submission
  - `GET /api/ask/async/{request_id}` - Status checking
  - Redis queue monitoring
  - Queue performance analysis

## Test Scenarios

### Basic Scenarios
- **quick_smoke_test**: 5 users, 3 minutes - Basic functionality verification
- **basic_load_test**: 20 users, 15 minutes - Standard mixed workload
- **realistic_usage**: 30 users, 25 minutes - Production-like patterns

### Performance Testing
- **streaming_performance**: Focus on streaming endpoint latency
- **high_concurrency**: 40 users testing concurrent load handling
- **websocket_stress**: WebSocket connection and message throughput

### Specialized Testing
- **async_processing**: Redis queue and async endpoint performance
- **queue_saturation**: Push Redis queue to capacity limits
- **auth_performance**: Authentication system load testing

### Stress Testing
- **stress_test**: 60 users pushing beyond normal capacity
- **spike_test**: Sudden traffic spikes with recovery monitoring
- **endurance_test**: 60-minute test for memory leaks and degradation

## Configuration

### Authentication Requirement
**IMPORTANT:** Load tests assume authentication is disabled. Before running load tests:

**For Staging:**
```bash
# In config/.env.staging, set:
VITE_USE_COGNITO_AUTH=false
```

**For Production:**
```bash
# Temporarily in config/.env.production, set:
VITE_USE_COGNITO_AUTH=false
# Remember to change back to true after testing!
```

### Environment Variables
```bash
# Configuration selection
LOAD_TEST_CONFIG=staging|production

# Redis connection (from .env files)
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your_redis_password
```

### Staging Configuration
- **Host:** Uses `VITE_API_URL` from `.env.staging`
- **Authentication:** Requires `VITE_USE_COGNITO_AUTH=false`
- **Target Users:** 20-30 concurrent
- **Performance Targets:**
  - P95 Response Time: <3s
  - Error Rate: <5%
  - Streaming First Token: <2s

### Production Configuration
- **Host:** Uses `VITE_API_URL` from `.env.production`
- **Authentication:** Temporarily set `VITE_USE_COGNITO_AUTH=false` for testing
- **Target Users:** 20-25 concurrent (conservative)
- **Performance Targets:**
  - P95 Response Time: <2.5s
  - Error Rate: <2%
  - Streaming First Token: <1.5s

## Running Tests

### Basic Commands
```bash
# Standard staging load test (uses VITE_API_URL from .env.staging)
LOAD_TEST_CONFIG=staging locust -f locustfile.py --users=30 --spawn-rate=2 --run-time=15m

# Web UI mode (for interactive monitoring)
LOAD_TEST_CONFIG=staging locust -f locustfile.py

# Headless mode with specific scenario
LOAD_TEST_CONFIG=staging locust -f locustfile.py --tags=streaming --users=20 --spawn-rate=2 --run-time=10m --headless

# Production testing (uses VITE_API_URL from .env.production)
LOAD_TEST_CONFIG=production locust -f locustfile.py --users=20 --spawn-rate=1 --run-time=15m
```

### Tag-Based Testing
```bash
# Focus on specific functionality
--tags=streaming          # Streaming performance
--tags=websocket          # WebSocket connections  
--tags=async             # Async processing
--tags=feedback          # Feedback submission
--tags=stress            # Stress testing
--tags=realistic         # Production-like scenarios
```

### Advanced Options
```bash
# Custom spawn rates and patterns
--spawn-rate=1           # Users per second (conservative)
--spawn-rate=5           # Users per second (aggressive)

# Duration options
--run-time=10m           # 10 minutes
--run-time=1h            # 1 hour
--run-time=30s           # 30 seconds (smoke test)

# Distributed testing
--master                 # Run as master node
--worker --master-host=192.168.1.100  # Worker node
```

## Monitoring and Metrics

### Built-in Locust Metrics
- Request rates and response times
- Error rates and failure types
- User count and spawn rates
- Resource utilization

### Custom ATLAS Metrics
- **Streaming Performance:**
  - First token time (target: <2s)
  - Total streaming time
  - Tokens per second rate

- **WebSocket Metrics:**
  - Connection establishment time
  - Message throughput
  - Connection stability

- **Redis Queue Metrics:**
  - Queue depth monitoring
  - Processing time analysis
  - Worker utilization

- **User Journey Metrics:**
  - Session completion rates
  - Question→Feedback conversion
  - Multi-step interaction success

### Real-time Monitoring
```bash
# Web UI (default: http://localhost:8089)
locust -f locustfile.py --host=https://192.168.20.17

# Command line stats
locust -f locustfile.py --host=https://192.168.20.17 --headless --print-stats

# Custom metrics export
# Metrics automatically exported to reports/ directory
```

## Performance Targets

### Response Time Targets
- **P50:** <1s (median response)
- **P95:** <3s (95th percentile)
- **P99:** <5s (99th percentile)
- **Streaming First Token:** <2s
- **WebSocket Connection:** <1s

### Throughput Targets
- **Minimum:** 10 requests/second sustained
- **Target:** 15-20 requests/second
- **Peak:** 30+ requests/second (short bursts)

### Error Rate Targets
- **Maximum:** 5% overall error rate
- **Streaming:** <3% error rate
- **WebSocket:** <2% connection failures
- **Authentication:** <1% auth failures

### Infrastructure Targets
- **Redis Queue Depth:** <100 pending requests
- **Async Processing:** <30s total time
- **Memory Growth:** <10% over test duration

## Results Analysis

### Automated Reports
Test results are automatically exported to `reports/` directory:
- `metrics_<timestamp>.json` - Detailed metrics
- Locust HTML reports
- Custom performance analysis

### Key Metrics to Monitor
1. **Response Time Distribution**
   - Look for P95/P99 response times
   - Identify slow endpoints
   - Check for degradation over time

2. **Error Patterns**
   - HTTP error codes
   - Timeout patterns
   - WebSocket connection failures

3. **Streaming Performance**
   - First token latency trends
   - Streaming completion rates
   - Token generation speeds

4. **Queue Performance**
   - Redis queue depth patterns
   - Processing time distribution
   - Worker utilization rates

5. **Resource Utilization**
   - CPU and memory trends
   - Network throughput
   - Database connection pools

### Success Criteria
✅ **Pass Conditions:**
- P95 response time < target thresholds
- Error rate < maximum thresholds  
- All user scenarios complete successfully
- No memory leaks or resource exhaustion
- WebSocket connections remain stable

❌ **Fail Conditions:**
- Response times exceed thresholds
- Error rate above acceptable limits
- System becomes unresponsive
- Queue depth grows unbounded
- Memory usage grows continuously

## Troubleshooting

### Common Issues

**High Response Times:**
```bash
# Check if streaming is the bottleneck
--tags=streaming --users=10

# Test sync endpoints only
--tags=basic --users=20
```

**WebSocket Connection Failures:**
```bash
# Test WebSocket connectivity
--tags=websocket --users=5 --run-time=2m
```

**Redis Queue Backup:**
```bash
# Monitor queue specifically
--tags=async --users=5
```

**Authentication Issues:**
```bash
# Test with auth disabled
USE_AUTH=false locust -f locustfile.py ...

# Test auth performance specifically
--tags=auth --users=10
```

### Performance Tuning
- Adjust spawn rates for gradual load increase
- Use distributed testing for higher load
- Monitor system resources during tests
- Tune Redis and database connections
- Scale worker processes as needed

## Safety Guidelines

### Staging Testing
- Maximum 50 concurrent users
- Monitor resource usage
- Test during off-peak hours
- Have rollback plan ready

### Production Testing
- Maximum 25 concurrent users
- Get approval before testing
- Monitor business impact
- Use dedicated test accounts
- Schedule during low-traffic periods
- Have incident response ready

### Emergency Procedures
```bash
# Stop test immediately
Ctrl+C (or kill process)

# Check system health
curl https://192.168.20.17/api/health

# Monitor recovery
watch -n 5 'curl -s https://192.168.20.17/api/health | jq'
```

## Development

### Adding New User Types
1. Create new class in `tasks/` directory
2. Inherit from `HttpUser` or `User`
3. Add `@task` decorated methods
4. Import in `locustfile.py`
5. Add to user weight configuration

### Custom Metrics
1. Use `metrics_collector.record_request()`
2. Add custom metric types in `utils/metrics.py`
3. Export in test reports

### New Test Scenarios
1. Add to `config/scenarios.yaml`
2. Define user distribution and duration
3. Set performance targets
4. Add tags for easy selection

## Contributing

1. Test changes against staging first
2. Update documentation for new features
3. Add performance targets for new scenarios
4. Ensure backward compatibility
5. Follow existing code patterns