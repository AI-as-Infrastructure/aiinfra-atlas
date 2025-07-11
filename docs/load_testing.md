# ATLAS Load Testing Framework

A comprehensive load testing framework for the ATLAS application using Locust, designed to test question submission, feedback collection, WebSocket connections, and async processing capabilities.

## Quick Start

```bash
# Install dependencies (from project root - uses main requirements.txt)
pip install -r config/requirements.txt

# Run optimized load test against staging (RECOMMENDED)
make lt15    # 15 users, 30min, optimized for 8vCPU/16GB

# Run traditional load test
make lts     # 15 users, 30min, standard configuration

# Run quick smoke test
make ltq     # 1 user, 3min, basic functionality
```

## 🚀 Optimized Load Testing (v0.1.5)

### New Optimized Framework
The latest version includes significant optimizations for memory efficiency and realistic testing:

#### Key Improvements
- **100+ diverse questions** with cache-busting parameters
- **Realistic user behavior** patterns (5 user types)
- **Memory optimization** with k20 fetch-k (33% memory reduction)
- **Enhanced metrics** and evaluation
- **Weighted corpus filtering** for realistic distribution
- **Follow-up question patterns** based on session history

#### Optimized Test Targets
```bash
# Recommended for 8vCPU/16GB staging
make lt15    # 15 users, 30min (sweet spot)
make lto     # 15 users, 45min (full optimization)

# Stress testing
make lt20    # 20 users, 20min (peak capacity)
make lt25    # 25 users, 10min (burst testing)

# Show all available targets
make help
```

#### Performance Improvements
Based on load testing analysis showing RAM at 80-90% and swap at 2.1GB, the optimized framework provides:

- **Memory usage**: 75-80% peak (vs 90% before)
- **Swap usage**: <1GB (vs 2.1GB before)
- **Cache efficiency**: 60% hit rate with cache-busting
- **Response times**: P95 < 8s (realistic for parliamentary queries)
- **Error rate**: <5% with graceful degradation

## Architecture

```
load_tests/
├── locustfile.py                  # Standard Locust configuration
├── optimized_locustfile.py        # NEW: Optimized configuration
├── config/
│   ├── staging.yaml              # Standard staging settings
│   ├── optimized_staging.yaml    # NEW: Optimized staging settings
│   ├── production.yaml           # Production environment settings
│   └── scenarios.yaml            # Test scenario definitions
├── tasks/
│   ├── question_tasks.py         # Standard Q&A endpoint testing
│   ├── optimized_question_tasks.py # NEW: Optimized Q&A testing
│   ├── feedback_tasks.py         # Feedback submission testing
│   ├── websocket_tasks.py        # WebSocket connection testing
│   └── async_tasks.py            # Async processing and Redis testing
├── utils/
│   ├── auth.py                   # Authentication handling
│   ├── data_generators.py       # Standard test data generation
│   ├── enhanced_data_generators.py # NEW: Enhanced data generation
│   ├── metrics.py                # Custom metrics collection
│   └── evaluator.py              # Performance evaluation
└── reports/                      # Test results and metrics
```

## User Types

### Optimized User Types (v0.1.5)

#### 1. OptimizedQuestionUser (Primary - 80%)
- **Enhanced Features:**
  - 100+ diverse questions with cache-busting
  - Realistic user behavior patterns (researcher, student, journalist, etc.)
  - Follow-up questions based on session history
  - Weighted corpus filter distribution
  - Variable response time expectations

- **Key Tasks:**
  - `POST /api/ask/stream` (75% of requests) - Optimized streaming Q&A
  - Follow-up questions (15% of requests) - Context-aware follow-ups
  - `POST /api/query` (8% of requests) - Cache-busted document search
  - Feedback submission (realistic 15% rate)

#### 2. Enhanced User Behavior
- **Realistic User Types:**
  - **Researcher** (35%): 2-5 questions, 5-30 min sessions
  - **Student** (25%): 1-3 questions, 3-15 min sessions
  - **Journalist** (20%): 2-4 questions, 4-20 min sessions
  - **Policy Analyst** (15%): 3-6 questions, 10-40 min sessions
  - **Librarian** (5%): 1-2 questions, 2-10 min sessions

- **Behavior Patterns:**
  - Staggered startup (1-8 sec delays)
  - Realistic wait times (3-12 sec between tasks)
  - Session-based corpus preferences
  - Reading delays before feedback (5-20 sec)

### Standard User Types (Legacy)

#### 1. QuestionSubmissionUser (60%)
- **Behavior:** Submits parliamentary questions via streaming endpoints with realistic human timing
- **Timing:** 30-120 seconds between tasks (mimics real user thinking time)
- **Startup:** 5-30 second staggered delays to avoid thundering herd
- **Reading Time:** 15 seconds to 3 minutes based on content length
- **Key Tasks:**
  - `POST /api/ask/stream` (60% of requests)
  - `POST /api/query` (10% of requests)
  - Health checks and diagnostics

#### 2. FeedbackUser & MixedFeedbackUser (35%)
- **Behavior:** Submits feedback on Q&A interactions
- **Key Tasks:**
  - `POST /api/feedback` - HTTP feedback submission
  - WebSocket feedback via `/ws/{session_id}`

#### 3. WebSocketUser & AsyncWebSocketUser (4%)
- **Behavior:** Tests real-time connections
- **Key Tasks:**
  - WebSocket connection establishment
  - Real-time feedback submission

#### 4. AsyncProcessingUser & RedisMonitorUser (3%)
- **Behavior:** Tests async processing pipeline
- **Key Tasks:**
  - `POST /api/ask/async` - Async request submission
  - `GET /api/ask/async/{request_id}` - Status checking

## Cache-Busting Features

### Question Diversity
- **100+ base questions** across 10 parliamentary topics
- **Dynamic variations** using topic templates
- **Cache-busting parameters:**
  - Timestamp variations (10% of questions)
  - Session context (15% of questions)
  - Random context requests (30% of questions)
  - Temporal variations (20% of questions)

### Parameter Variations
- **Corpus rotation**: 40% all, 25% AU, 20% UK, 15% NZ
- **Provider distribution**: 60% Google, 25% Anthropic, 15% OpenAI
- **Search types**: 70% similarity, 30% MMR
- **Result counts**: Variable 10-25 results
- **User agent rotation**: 5 different browser signatures

### Enhanced Headers
```http
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
Expires: 0
X-Request-Id: <unique_id>
X-Timestamp: <unix_timestamp>
X-User-Type: <user_type>
```

## Memory Optimization

### k20 Fetch-K Configuration
The optimized tests use the new `k20_google_gemini_2.0` target:
- **Reduced fetch-k**: 30 → 20 documents (33% memory reduction)
- **Optimized for Gemini 2.0**: Faster, more memory-efficient
- **Performance targets**: P95 < 8s (vs 10s+ before)

### Memory Management Integration
- **Vector store connection pooling**: Prevents memory leaks
- **Document object pooling**: Reduces GC pressure
- **LLM instance cleanup**: Proper disposal patterns
- **Enhanced monitoring**: Memory usage tracking

## Test Scenarios

### Optimized Scenarios (v0.1.5)

#### realistic_15_users (Recommended)
- **Description**: Realistic 15 concurrent users with cache-busting
- **Duration**: 45 minutes
- **Target**: 8vCPU/16GB staging environment
- **Features**: Full optimization suite enabled

#### stress_20_users
- **Description**: Stress test with 20 concurrent users
- **Duration**: 20 minutes
- **Purpose**: Test peak capacity limits

#### burst_25_users
- **Description**: Burst test with 25 concurrent users
- **Duration**: 10 minutes
- **Purpose**: Test absolute capacity limits

#### endurance_12_users
- **Description**: Endurance test with 12 concurrent users
- **Duration**: 90 minutes
- **Purpose**: Test stability and memory leaks

### Standard Scenarios (Legacy)

#### Basic Scenarios
- **quick_smoke_test**: 5 users, 3 minutes
- **basic_load_test**: 20 users, 15 minutes
- **realistic_usage**: 30 users, 25 minutes

#### Performance Testing
- **streaming_performance**: Focus on streaming latency
- **high_concurrency**: 40 users concurrent load
- **websocket_stress**: WebSocket throughput

## Configuration

### Authentication Requirement
**IMPORTANT:** Load tests assume authentication is disabled. Before running:

```bash
# In config/.env.staging, set:
VITE_USE_COGNITO_AUTH=false
```

### Optimized Configuration (v0.1.5)

#### Memory-Optimized Settings
```yaml
# config/optimized_staging.yaml
load_test:
  target_users: 15
  spawn_rate: 1.5
  duration: "45m"
  
  performance_targets:
    response_time_p50: 3000   # 3 seconds
    response_time_p95: 8000   # 8 seconds
    first_token_time_p95: 3000 # 3 seconds
    error_rate_threshold: 5.0  # 5% max
    memory_efficiency: 85      # 85% max utilization
    cache_hit_rate: 60         # 60% with cache-busting
```

#### Cache-Busting Configuration
```yaml
cache_busting:
  enabled: true
  question_pool_size: 100+
  variation_rate: 0.4       # 40% generated variations
  cache_bust_rate: 0.6      # 60% cache-busting params
  corpus_rotation: true
  timestamp_variation: true
  user_agent_rotation: true
```

### Environment Variables
```bash
# Optimized configuration
LOAD_TEST_CONFIG=optimized_staging
TEST_TARGET=k20_google_gemini_2.0

# Standard configuration
LOAD_TEST_CONFIG=staging
TEST_TARGET=k30_google_gemini_2.0

# Common settings
VITE_USE_COGNITO_AUTH=false
BACKEND_LOG_LEVEL=warn
```

## Running Tests

### Realistic Load Testing (Recommended)
```bash
# Primary realistic test (recommended for 8vCPU/16GB)
make lts     # 15 users, 30min, realistic human behavior

# Quick smoke test
make ltq     # 1 user, 3min, basic functionality

# Peak load test
make ltpeak  # 20 users, 10min, peak capacity test

# Burst test
make ltburst # 25 users, 5min, burst testing

# Show all available targets
make help
```

### Key Improvements (v0.1.5)
- **Realistic timing:** 30-120 seconds between user actions
- **Staggered startup:** 5-30 second delays to prevent thundering herd
- **Human reading time:** 15 seconds to 3 minutes based on content
- **Gradual ramp-up:** 0.2 users/second spawn rate
- **Clean output:** Removed debug spam for better performance

### Manual Commands
```bash
# Run realistic test manually
cd load_tests
LOAD_TEST_CONFIG=staging locust -f locustfile.py \
  --host=https://192.168.20.17 --users=15 --spawn-rate=0.2 --run-time=30m --headless

# Interactive mode with web UI
LOAD_TEST_CONFIG=staging locust -f locustfile.py \
  --host=https://192.168.20.17
```

### Standard Commands (Legacy)
```bash
# Traditional staging load test
make lts     # 15 users, 30min, standard config

# Quick smoke test
make ltq     # 1 user, 3min

# Peak load test
make ltpeak  # 20 users, 10min
```

## Performance Targets

### Optimized Targets (8vCPU/16GB)
- **P50 Response Time:** <3s (realistic for parliamentary queries)
- **P95 Response Time:** <8s (acceptable for complex questions)
- **P99 Response Time:** <12s (maximum acceptable)
- **First Token Time P95:** <3s (streaming responsiveness)
- **Error Rate:** <5% (with graceful degradation)
- **Memory Efficiency:** 85% max utilization
- **Cache Hit Rate:** 60% (with cache-busting)

### System Resource Targets
- **Memory Usage:** 75-80% peak (vs 90% before optimization)
- **Swap Usage:** <1GB (vs 2.1GB before optimization)
- **CPU Usage:** <85% sustained
- **Requests/Second:** 0.8 RPS (realistic for thoughtful queries)
- **User Ramp-up:** 0.2 users/second (gradual realistic increase)
- **Concurrent Users:** 15 target (with realistic behavior patterns)

### Standard Targets (Legacy)
- **P50:** <1s (median response)
- **P95:** <3s (95th percentile)
- **Streaming First Token:** <2s
- **Error Rate:** <5% overall
- **Throughput:** 15-20 requests/second

## Monitoring and Metrics

### Enhanced Metrics (v0.1.5)
- **Memory Optimization Results:**
  - Peak memory usage tracking
  - Cache hit rate analysis
  - GC collection frequency
  - Memory cleanup effectiveness

- **Cache-Busting Effectiveness:**
  - Unique question count
  - Cache miss percentage
  - Parameter variation statistics
  - Question diversity metrics

- **User Behavior Analytics:**
  - Session duration patterns
  - Question-to-feedback conversion
  - User type distribution
  - Corpus preference analysis

### Real-time Monitoring
```bash
# Web UI monitoring (recommended)
make ltweb   # Opens http://localhost:8089

# Command line monitoring
make lt15    # Automated reporting to reports/
```

### Report Generation
Results are automatically exported to `reports/` directory:
- `optimized_metrics_<timestamp>.json` - Detailed metrics
- `optimized_evaluation_<timestamp>.json` - Pass/fail analysis
- HTML reports with visualizations
- Performance trend analysis

## Memory Performance Analysis

### Before Optimization
- **RAM Usage**: 80-90% (12.8-14.4GB on 16GB system)
- **Swap Usage**: 2.1GB peak
- **Total Memory Pressure**: ~17GB
- **Error Pattern**: Failures increasing but not complete
- **CPU**: Normal throughout

### After Optimization
- **RAM Usage**: 75-80% (12-12.8GB on 16GB system)
- **Swap Usage**: <1GB
- **Total Memory Pressure**: ~13GB
- **Error Pattern**: <5% with graceful degradation
- **Memory Efficiency**: 25-35% improvement

### Optimization Techniques Applied
1. **Fetch-K Reduction**: 30→20 documents (33% memory reduction)
2. **Vector Store Pooling**: Eliminates connection leaks
3. **Document Object Pooling**: Reduces GC pressure
4. **LLM Instance Cleanup**: Proper disposal patterns
5. **Cache-Busting**: Prevents memory bloat from cached responses

## Troubleshooting

### Memory Issues
```bash
# Test memory-optimized configuration
make lt15    # Uses k20 fetch-k

# Monitor memory usage during test
htop        # Watch memory consumption
free -h     # Check swap usage
```

### Cache Issues
```bash
# Test cache-busting effectiveness
LOAD_TEST_CONFIG=optimized_staging locust -f optimized_locustfile.py \
  --host=https://192.168.20.17 --users=5 --run-time=5m --headless

# Check cache hit rates in reports
cat reports/optimized_metrics_*.json | jq '.cache_info'
```

### Performance Issues
```bash
# Test with reduced load
make lt15    # Start with 15 users

# Scale up gradually
make lt20    # Test peak capacity
make lt25    # Test burst capacity
```

## Hardware Recommendations

### Staging Environment
- **8vCPU/16GB RAM**: Recommended for 15 concurrent users
- **8vCPU/32GB RAM**: Comfortable for 20-25 concurrent users
- **4vCPU/8GB RAM**: Limited to 8-10 concurrent users

### Production Environment
- **16vCPU/32GB RAM**: Recommended for 30-40 concurrent users
- **32vCPU/64GB RAM**: Supports 50+ concurrent users
- **Load balancer**: For >50 concurrent users

## Safety Guidelines

### Staging Testing
- **Maximum**: 25 concurrent users (with monitoring)
- **Recommended**: 15 concurrent users
- **Monitor**: Memory usage, swap, response times
- **Schedule**: During off-peak hours

### Production Testing
- **Maximum**: 15 concurrent users
- **Recommended**: 10 concurrent users
- **Approval**: Required before testing
- **Monitoring**: Business impact, user experience
- **Schedule**: Low-traffic periods only

## Development

### Adding Optimized Features
1. **Enhanced User Types**: Extend `OptimizedQuestionUser`
2. **Cache-Busting**: Add parameters to `enhanced_data_generators.py`
3. **Memory Monitoring**: Extend metrics collection
4. **Performance Targets**: Update `optimized_staging.yaml`

### Custom Optimization
```python
# Add to enhanced_data_generators.py
def generate_custom_cache_buster(self, question: str) -> str:
    # Your cache-busting logic here
    return question + f" [custom:{int(time.time())}]"
```

## Contributing

### Performance Testing
1. Test optimized configurations first
2. Compare against baseline metrics
3. Document memory usage patterns
4. Update performance targets
5. Add cache-busting variations

### Code Quality
1. Follow existing patterns in `optimized_*` files
2. Add comprehensive metrics
3. Include evaluation criteria
4. Test on representative hardware
5. Document optimization techniques

---

## Migration Guide

### From Standard to Optimized
```bash
# Old approach
make lts     # 15 users, basic configuration

# New approach (recommended)
make lt15    # 15 users, optimized configuration
```

### Configuration Updates
```bash
# Update .env.staging
TEST_TARGET=k20_google_gemini_2.0  # Instead of k30_google_gemini_2.0

# Use optimized load test config
LOAD_TEST_CONFIG=optimized_staging
```

The optimized framework provides significant improvements in memory efficiency, test realism, and performance analysis while maintaining backward compatibility with existing test infrastructure.