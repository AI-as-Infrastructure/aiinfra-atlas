# ATLAS Load Testing Framework

A load testing framework for the ATLAS application using Locust, designed to test question submission, feedback collection, and realistic user behavior patterns.

## Quick Start

```bash
# Install dependencies (from project root - uses main requirements.txt)
pip install -r config/requirements.txt

# Run realistic load test against staging
make lts     # 15 users, 30min, realistic for 8vCPU/16GB
```

## Architecture

```
load_tests/
├── locustfile.py                  # Main Locust configuration
├── config/
│   └── staging.yaml              # Staging environment settings
├── tasks/
│   └── question_tasks.py         # Q&A endpoint testing tasks
├── utils/
│   ├── data_generators.py        # Test data generation with country-specific questions
│   ├── metrics.py                # Custom metrics collection with semantic failure tracking
│   ├── evaluator.py              # Performance evaluation
│   └── report_generator.py       # Test results reporting with HTTP and semantic success rates
└── reports/                      # Test results and metrics output
```

## User Types

The load testing framework implements realistic user behavior patterns through specialized user classes in `tasks/question_tasks.py`:

### QuestionSubmissionUser (Primary - 60%)
- **Behavior:** Submits parliamentary questions via streaming endpoints with realistic human timing
- **Timing:** 30-120 seconds between tasks (mimics real user thinking time)
- **Startup:** 5-30 second staggered delays to avoid thundering herd
- **Reading Time:** 15 seconds to 3 minutes based on content length
- **Key Tasks:**
  - `POST /api/ask/stream` (60% of requests)
  - `POST /api/query` (10% of requests)
  - Health checks and diagnostics

### FeedbackUser & MixedFeedbackUser (35%)
- **Behavior:** Submits feedback on Q&A interactions
- **Key Tasks:**
  - `POST /api/feedback` - HTTP feedback submission
  - WebSocket feedback via `/ws/{session_id}`

### WebSocketUser & AsyncWebSocketUser (4%)
- **Behavior:** Tests real-time connections
- **Key Tasks:**
  - WebSocket connection establishment
  - Real-time feedback submission

### AsyncProcessingUser & RedisMonitorUser (1%)
- **Behavior:** Tests async processing pipeline
- **Key Tasks:**
  - `POST /api/ask/async` - Async request submission
  - `GET /api/ask/async/{request_id}` - Status checking

## Question Generation Features

The framework includes sophisticated question generation capabilities in `utils/data_generators.py`:

### Country-Specific Questions
- **Australian Questions** (matches `1901_au` filter): Federation, colonial government, wool industry
- **New Zealand Questions** (matches `1901_nz` filter): Colonial administration, Māori relations, sheep farming
- **UK Questions** (matches `1901_uk` filter): Imperial policy, House of Commons, industrial regulation
- **General Questions**: Multi-jurisdictional topics

### Question-Filter Optimization
- **90% Optimal Matching**: Questions designed to match their corpus filters for relevant results
- **10% Sub-optimal Questions**: Intentionally mismatched for edge case testing
- **Cache-Busting**: Timestamp and session context variations to prevent caching
- **Corpus Distribution**: 40% all, 25% AU, 20% UK, 15% NZ

## Metrics and Success Rate Tracking

### Dual Success Rate Reporting
The framework tracks both HTTP and semantic success rates:

- **HTTP Success Rate**: Traditional request/response success (network level)
- **Semantic Success Rate**: Based on meaningful content generation (excludes zero-token responses)

### Zero-Token Failure Detection
Responses with 0 tokens are classified as complete semantic failures and tracked separately for load testing evaluation.

### Custom Metrics Collection
- Real-time metric collection during test execution
- Token count tracking for semantic analysis
- Memory usage and performance monitoring
- Export to JSON reports with timestamp

## Configuration

### Authentication Requirement
**IMPORTANT:** Load tests assume authentication is disabled. Before running:

```bash
# In config/.env.staging, set:
VITE_USE_COGNITO_AUTH=false
```

### Environment Variables
```bash
# Standard configuration
LOAD_TEST_CONFIG=staging
BACKEND_LOG_LEVEL=warn
VITE_USE_COGNITO_AUTH=false
```

## Running Tests

### Primary Load Test
```bash
# Realistic load test (recommended for 8vCPU/16GB)
make lts     # 15 users, 30min, realistic human behavior
```

### Manual Commands
```bash
# Run test manually with custom parameters
cd load_tests
source ../config/.env.staging
LOAD_TEST_CONFIG=staging locust -f locustfile.py \
  --host=$VITE_API_URL --users=15 --spawn-rate=0.2 --run-time=30m --headless

# Interactive mode with web UI
LOAD_TEST_CONFIG=staging locust -f locustfile.py \
  --host=$VITE_API_URL
```

## Performance Targets

### Realistic Targets (8vCPU/16GB)
- **P50 Response Time:** <3s (realistic for parliamentary queries)
- **P95 Response Time:** <8s (acceptable for complex questions)
- **P99 Response Time:** <12s (maximum acceptable)
- **First Token Time P95:** <3s (streaming responsiveness)
- **Error Rate:** <5% (with graceful degradation)
- **Semantic Success Rate:** >95% (meaningful content generation)

### System Resource Targets
- **Memory Usage:** <85% peak utilization
- **CPU Usage:** <85% sustained
- **Requests/Second:** 0.8 RPS (realistic for thoughtful queries)
- **User Ramp-up:** 0.2 users/second (gradual realistic increase)
- **Concurrent Users:** 15 target (with realistic behavior patterns)

## Monitoring and Metrics

### Real-time Monitoring
```bash
# Web UI monitoring (recommended)
# Start locust without --headless flag to access http://localhost:8089

# Command line monitoring
make lts    # Automated reporting to reports/
```

### Report Generation
Results are automatically exported to `reports/` directory:
- `metrics_<timestamp>.json` - Detailed metrics with HTTP and semantic success rates
- `evaluation_<timestamp>.json` - Pass/fail analysis
- Performance analysis with token count statistics

## Memory Performance Features

### Optimization Techniques
1. **Realistic User Timing**: 30-120 second delays between requests
2. **Staggered Startup**: 5-30 second delays to prevent thundering herd
3. **Gradual Ramp-up**: 0.2 users/second spawn rate
4. **Country-Specific Questions**: Optimized for corpus relevance
5. **Semantic Failure Tracking**: Zero-token response detection

## Troubleshooting

### Memory Issues
```bash
# Monitor memory usage during test
htop        # Watch memory consumption
free -h     # Check swap usage
```

### Performance Issues
```bash
# Test with reduced load
make lts    # Start with 15 users

# Check semantic success rates in reports
cat reports/metrics_*.json | jq '.semantic_success_rate'
```

### Question Relevance Issues
The framework automatically generates country-specific questions that match corpus filters. If you see poor response quality:
1. Check the semantic success rate in reports
2. Verify corpus filters are being applied correctly
3. Review question-filter matching in `data_generators.py`

## Hardware Recommendations

### Staging Environment
- **8vCPU/16GB RAM**: Recommended for 15 concurrent users
- **4vCPU/8GB RAM**: Limited to 8-10 concurrent users

### Production Environment
- **16vCPU/32GB RAM**: Recommended for 30-40 concurrent users
- **Load balancer**: For >50 concurrent users

## Safety Guidelines

### Staging Testing
- **Maximum**: 25 concurrent users (with monitoring)
- **Recommended**: 15 concurrent users
- **Monitor**: Memory usage, semantic success rates, response times
- **Schedule**: During off-peak hours

### Production Testing
- **Maximum**: 15 concurrent users
- **Recommended**: 10 concurrent users
- **Approval**: Required before testing
- **Monitoring**: Business impact, user experience
- **Schedule**: Low-traffic periods only

## Development

### Adding New User Types
Extend the user classes in `tasks/question_tasks.py` following existing patterns for realistic timing and behavior.

### Customizing Questions
Add new question types to `utils/data_generators.py` with appropriate corpus filter matching.

### Extending Metrics
Add new metric collection in `utils/metrics.py` and update report generation in `utils/report_generator.py`.

---

The load testing framework provides realistic user simulation with sophisticated question generation, dual success rate tracking, and comprehensive performance analysis while maintaining system stability and meaningful test results.