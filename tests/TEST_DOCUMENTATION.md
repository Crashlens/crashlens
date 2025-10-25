# CrashLens Test Suite Documentation

**Last Updated**: 2025-01-24  
**Test Suite Version**: Phase 2 - Prometheus Integration  
**Total Tests**: 26 (6 critical verification tests + 20 supporting tests)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Critical Verification Tests (Phase 2)](#critical-verification-tests-phase-2)
3. [Supporting Test Suites](#supporting-test-suites)
4. [Running Tests](#running-tests)
5. [Test Organization](#test-organization)
6. [Debugging Test Failures](#debugging-test-failures)

---

## Overview

This document provides comprehensive documentation for all tests in the CrashLens project. Each test is documented with:
- **Purpose**: Why the test exists
- **What It Tests**: Specific functionality being verified
- **Acceptance Criteria**: What must pass for the test to succeed
- **Failure Scenarios**: Common reasons the test might fail

### Test Categories

```
tests/
├── integration/                    # End-to-end integration tests
│   ├── test_integration_e2e.py    # Docker-based E2E tests (Tests 6)
│   ├── test_http_server_integration.py
│   └── test_metrics_pushgateway.py
├── unit/                           # Unit tests for individual components
└── test_*.py                       # Verification tests (Tests 1-5)
```

---

## Critical Verification Tests (Phase 2)

These 6 tests form the **production validation gate** for the Prometheus integration feature.

### Test 1: Lazy Loading (`test_lazy_import.py`)

**File**: `tests/test_lazy_import.py`  
**Duration**: ~1.88s  
**Priority**: CRITICAL

#### Purpose
Verify that prometheus_client is NOT imported when metrics are disabled, ensuring zero performance overhead for users who don't use observability features.

#### What It Tests
1. Import behavior when `CRASHLENS_DISABLE_METRICS` is not set
2. Import behavior when `CRASHLENS_DISABLE_METRICS=true`
3. Module presence in `sys.modules` before and after import
4. Clean environment state for metrics initialization

#### Acceptance Criteria
- ✅ `prometheus_client` must NOT be in `sys.modules` after importing crashlens with metrics disabled
- ✅ `prometheus_client` SHOULD be available when metrics are explicitly enabled
- ✅ No performance penalty when observability is disabled

#### Why This Matters
**Production Impact**: Without lazy loading, every CrashLens user would pay the import cost of prometheus_client (~50-100ms) even if they never use metrics. This test ensures we honor the "zero overhead when disabled" principle.

#### Common Failure Scenarios
```python
# ❌ FAILS: Eager import at module level
from prometheus_client import Counter  # Don't do this!

# ✅ PASSES: Lazy import inside function
def get_metrics():
    from prometheus_client import Counter
    return Counter(...)
```

#### How to Run
```bash
poetry run pytest tests/test_lazy_import.py -v
```

---

### Test 2: Fire-and-Forget Push Timeout (`test_fire_and_forget_push_default_non_blocking.py`)

**File**: `tests/test_fire_and_forget_push_default_non_blocking.py`  
**Duration**: ~3.05s  
**Priority**: CRITICAL

#### Purpose
Ensure that metrics push operations NEVER block the CLI, even if the Pushgateway is unreachable or slow. The push happens in a background thread with a strict 3-second timeout.

#### What It Tests
1. Push timeout enforcement (3 seconds max)
2. Non-blocking behavior with unresponsive gateway
3. Thread-based asynchronous push execution
4. Graceful degradation when push fails

#### Acceptance Criteria
- ✅ Total execution time < 5 seconds (3s timeout + 2s buffer)
- ✅ Main CLI thread continues immediately after initiating push
- ✅ Background thread terminated after timeout
- ✅ No exceptions propagated to user

#### Why This Matters
**Production Impact**: Users should never experience CLI hangs due to network issues with the Pushgateway. A hung metrics push could delay CI/CD pipelines or block local development workflows.

#### Test Scenario
```python
# Simulates unreachable Pushgateway
pushgateway_url = "http://10.255.255.1:9091"  # Black hole IP
start = time.time()
push_metrics_async(metrics, pushgateway_url, job_name="test", timeout=3)
elapsed = time.time() - start
assert elapsed < 5  # Must complete within timeout window
```

#### Common Failure Scenarios
- Network timeout configuration too high (>3s)
- Synchronous push call instead of async
- Thread not properly daemonized

#### How to Run
```bash
poetry run pytest tests/test_fire_and_forget_push_default_non_blocking.py -v
```

---

### Test 3: Push Success/Failure Counters (`test_push_success_failure_counters.py`)

**File**: `tests/test_push_success_failure_counters.py`  
**Duration**: ~1.81s  
**Priority**: CRITICAL

#### Purpose
Verify that the metrics system correctly tracks its own health by recording push success and failure events via `crashlens_metrics_push_status`.

#### What It Tests
1. `crashlens_metrics_push_status{status="success"}` increments on successful push
2. `crashlens_metrics_push_status{status="failure"}` increments on failed push
3. Counter persistence across multiple push attempts
4. Self-monitoring behavior

#### Acceptance Criteria
- ✅ Success counter increments when Pushgateway responds 200 OK
- ✅ Failure counter increments on network errors or timeouts
- ✅ Both counters can be scraped from HTTP metrics endpoint
- ✅ Counter values are accurate (no double-counting)

#### Why This Matters
**Production Impact**: Operations teams need visibility into whether metrics are successfully reaching the Pushgateway. This metric enables alerts like "CrashLens metrics push has failed for 10+ consecutive attempts."

#### Test Scenario
```python
# Success case
mock_push.return_value = Mock(status_code=200)
metrics.push_to_gateway(url, job="test")
assert metrics.get_push_status("success") == 1

# Failure case
mock_push.side_effect = Timeout()
metrics.push_to_gateway(url, job="test")
assert metrics.get_push_status("failure") == 1
```

#### How to Run
```bash
poetry run pytest tests/test_push_success_failure_counters.py -v
```

---

### Test 4: Cardinality Cap and Overflow (`test_cardinality_cap_and_overflow.py`)

**File**: `tests/test_cardinality_cap_and_overflow.py`  
**Duration**: ~1.88s  
**Priority**: CRITICAL

#### Purpose
Prevent metrics cardinality explosion by capping the number of unique rule names tracked and collapsing excess rules into an `OVERFLOW_SENTINEL` label.

#### What It Tests
1. Maximum rule limit enforcement (default: 500)
2. Overflow detection when limit exceeded
3. `crashlens_rule_label_overflow_total` counter increments
4. Metric labels collapse to `rule="rule_overflow"`
5. Memory protection (constant memory usage)

#### Acceptance Criteria
- ✅ First 500 unique rule names tracked individually
- ✅ Rules 501+ collapsed to `rule="rule_overflow"`
- ✅ Overflow counter increments for each collapsed rule
- ✅ No unbounded memory growth

#### Why This Matters
**Production Impact**: Without cardinality protection, a misconfigured policy with 10,000 unique rule names could:
- Exhaust Prometheus memory (100KB per series * 10,000 = 1GB)
- Cause Pushgateway OOM crashes
- Make Grafana dashboards unusable
- Violate Prometheus best practices (keep cardinality <1000 per metric)

#### Test Scenario
```python
# Add 505 unique rules
for i in range(505):
    metrics.record_rule_hit(f"rule_{i}", "high", "scan")

# Verify first 500 tracked, rest overflow
assert len(metrics._tracked_rules) == 500
assert metrics.get_overflow_count() == 5
```

#### Common Failure Scenarios
- Overflow counter not incrementing
- All rules tracked (memory leak)
- Overflow threshold too high/low

#### How to Run
```bash
poetry run pytest tests/test_cardinality_cap_and_overflow.py -v
```

---

### Test 5: Metrics Disabled by Default (`test_metrics_disabled_by_default.py`)

**File**: `tests/test_metrics_disabled_by_default.py`  
**Duration**: ~1.86s  
**Priority**: CRITICAL

#### Purpose
Verify that metrics collection is **opt-in** by default. Users must explicitly enable metrics via `--push-metrics` or environment variables.

#### What It Tests
1. Default state when no flags/env vars are set
2. `initialize_metrics(enabled=False)` returns None
3. No metrics HTTP server starts by default
4. Kill switch `CRASHLENS_DISABLE_METRICS=true` always disables metrics

#### Acceptance Criteria
- ✅ `initialize_metrics()` returns `None` when `enabled=False`
- ✅ No prometheus_client imports in default case
- ✅ Kill switch overrides all other configuration
- ✅ No background threads spawned

#### Why This Matters
**Production Impact**: Metrics collection should be **opt-in** for:
- Privacy (no data sent without consent)
- Performance (zero overhead by default)
- Security (no open ports without explicit request)
- Compliance (GDPR, data sovereignty)

#### Test Scenario
```python
# Default case - metrics disabled
os.environ.pop("CRASHLENS_PUSH_METRICS", None)
metrics = initialize_metrics(enabled=False)
assert metrics is None

# Kill switch - always disabled
os.environ["CRASHLENS_DISABLE_METRICS"] = "true"
metrics = initialize_metrics(enabled=True)  # Even with enabled=True
assert metrics is None
```

#### How to Run
```bash
poetry run pytest tests/test_metrics_disabled_by_default.py -v
```

---

### Test 6: E2E Integration with Real Docker Pushgateway (`test_integration_e2e.py`)

**File**: `tests/integration/test_integration_e2e.py`  
**Duration**: ~10.80s  
**Priority**: CRITICAL (Ultimate Proof)

#### Purpose
This is the **ultimate end-to-end proof** that the entire Prometheus integration works in a real production-like environment. It spins up a real Docker container running the official `prom/pushgateway` image and verifies that CrashLens can successfully push metrics to it.

#### What It Tests
1. **Docker Infrastructure**: Container lifecycle (start → run → stop)
2. **Real Network Communication**: HTTP POST to real Pushgateway
3. **CLI Subprocess Execution**: Running `poetry run crashlens scan` as real user would
4. **Environment Variable Configuration**: All env vars correctly applied
5. **Metrics Serialization**: Prometheus text format correctness
6. **Job Name Grouping**: Custom job names applied to metrics
7. **Metric Persistence**: Metrics retrievable from Pushgateway after push
8. **Non-Zero Values**: Actual data is being recorded (not just empty metrics)

#### Acceptance Criteria
- ✅ Docker container starts successfully
- ✅ Pushgateway responds to health checks
- ✅ CrashLens CLI exits with code 0
- ✅ Metrics visible at `http://localhost:9091/metrics`
- ✅ Custom job name `job="crashlens_e2e_test"` present
- ✅ Core metrics found:
  - `crashlens_traces_processed_total`
  - `crashlens_rule_hits_total`
  - `crashlens_violations_total`
  - `crashlens_last_run_timestamp_seconds`
- ✅ Metric values > 0 (data recorded)
- ✅ Container cleanup successful

#### Why This Matters
**Production Impact**: This test proves that the integration works **exactly as users will deploy it in production**:
- Real Docker infrastructure (not mocks)
- Real network calls (not stubbed HTTP)
- Real CLI execution (not internal function calls)
- Real Pushgateway (official Prometheus image)

This is the test that would catch issues like:
- Firewall/networking problems
- Docker permission issues
- Prometheus text format incompatibilities
- Real-world race conditions
- Environment variable parsing bugs

#### Test Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ pytest (test runner)                                        │
└──────────────────┬──────────────────────────────────────────┘
                   │
         ┌─────────▼──────────┐
         │ docker_pushgateway │ (pytest fixture)
         │   fixture          │
         └─────────┬──────────┘
                   │
    ┌──────────────▼───────────────┐
    │ Docker: prom/pushgateway     │
    │ Port: 9091                   │
    │ URL: http://localhost:9091   │
    └──────────────┬───────────────┘
                   │
         ┌─────────▼──────────┐
         │ subprocess.run()   │
         │ poetry run         │
         │ crashlens scan     │
         └─────────┬──────────┘
                   │
    ┌──────────────▼────────────────┐
    │ CrashLens CLI (real process)  │
    │ - Parse JSONL logs            │
    │ - Run detectors               │
    │ - Collect metrics             │
    │ - Push to Pushgateway         │
    └──────────────┬────────────────┘
                   │
         ┌─────────▼──────────┐
         │ HTTP POST          │
         │ /metrics/job/...   │
         └─────────┬──────────┘
                   │
    ┌──────────────▼────────────────┐
    │ Pushgateway (receives push)   │
    │ - Stores metrics              │
    │ - Exposes /metrics endpoint   │
    └──────────────┬────────────────┘
                   │
         ┌─────────▼──────────┐
         │ Test verifies:     │
         │ - Metrics present  │
         │ - Job name correct │
         │ - Values non-zero  │
         └────────────────────┘
```

#### Environment Variables Used

```bash
CRASHLENS_PUSH_METRICS=true              # Enable metrics push
CRASHLENS_PUSHGATEWAY_URL=http://localhost:9091
CRASHLENS_METRICS_JOB=crashlens_e2e_test # Custom job name
TEST_PROMETHEUS_INTEGRATION=true         # Enable Docker tests
```

#### Sample Log Format

The test creates sample JSONL logs matching the Langfuse v1 schema:

```json
{
  "traceId": "trace-001",
  "startTime": "2024-01-15T10:00:00Z",
  "input": {
    "model": "gpt-4",
    "prompt": "Test query"
  },
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  },
  "cost": 0.009,
  "level": "ERROR",
  "statusMessage": "Rate limit exceeded"
}
```

#### Expected Metrics Output

```prometheus
# CrashLens metrics with custom job name
crashlens_rule_hits_total{instance="",job="crashlens_e2e_test",mode="scan",rule="RetryLoopDetector",severity="high"} 1
crashlens_rule_hits_total{instance="",job="crashlens_e2e_test",mode="scan",rule="OverkillModelDetector",severity="medium"} 1
crashlens_violations_total{instance="",job="crashlens_e2e_test",severity="high"} 1
crashlens_violations_total{instance="",job="crashlens_e2e_test",severity="medium"} 1
crashlens_traces_processed_total{instance="",job="crashlens_e2e_test"} 3
crashlens_last_run_timestamp_seconds{instance="",job="crashlens_e2e_test",status="success"} 1.761342e+09

# Python runtime metrics (from prometheus_client)
python_gc_collections_total{generation="0",instance="",job="crashlens_e2e_test"} 83
python_info{implementation="CPython",instance="",job="crashlens_e2e_test",major="3",minor="12",patchlevel="10",version="3.12.10"} 1
```

#### Prerequisites

1. **Docker Desktop** must be running
2. **Port 9091** must be available
3. **Network access** to Docker Hub (to pull `prom/pushgateway`)
4. **Environment variable**: `TEST_PROMETHEUS_INTEGRATION=true`

#### How to Run

```bash
# Start Docker Desktop first
# Then run the test:
$env:TEST_PROMETHEUS_INTEGRATION="true"
poetry run pytest tests/integration/test_integration_e2e.py::test_e2e_metrics_push_to_real_pushgateway -v -s
```

#### Common Failure Scenarios

| Failure | Cause | Solution |
|---------|-------|----------|
| `Docker daemon not running` | Docker Desktop not started | Start Docker Desktop |
| `Port 9091 already in use` | Another service using port | Stop conflicting service or change port |
| `Container failed to start` | Network/permission issues | Check Docker logs: `docker logs <container_id>` |
| `Metrics not found in Pushgateway` | Wrong environment variables | Verify `CRASHLENS_METRICS_JOB` is set |
| `Exit code 1` | Log parsing error | Check log format matches schema |

#### Debug Commands

```bash
# Check if Docker is running
docker ps

# View Pushgateway logs
docker logs <container_id>

# Query Pushgateway metrics manually
curl http://localhost:9091/metrics

# Check for CrashLens metrics
curl http://localhost:9091/metrics | grep crashlens

# Run test with verbose output
poetry run pytest tests/integration/test_integration_e2e.py -v -s
```

#### Test Output (Success)

```
🎯 E2E TEST: Running CrashLens CLI with Real Pushgateway
📝 Environment:
  CRASHLENS_PUSH_METRICS: true
  CRASHLENS_PUSHGATEWAY_URL: http://localhost:9091
  CRASHLENS_METRICS_JOB: crashlens_e2e_test

🚀 Running CrashLens CLI...
Exit Code: 0

✓ PASS: CrashLens CLI executed successfully
✓ PASS: Pushgateway responded (200 OK)
✓ PASS: CrashLens job found in Pushgateway
✓ PASS: Found metric 'crashlens_traces_processed_total'
✓ PASS: Found metric 'crashlens_rule_hits_total'
✓ PASS: Found non-zero metric value: 2.0

🎉 E2E TEST PASSED: All assertions successful!
```

#### Related Tests

- `test_e2e_metrics_disabled_by_default`: Verifies metrics are NOT pushed when disabled
- `test_http_server_integration.py`: Tests HTTP metrics server (alternative to push mode)
- `test_metrics_pushgateway.py`: Unit tests for Pushgateway client

---

## Supporting Test Suites

### Integration Tests

#### `test_http_server_integration.py`
**Purpose**: Verify HTTP metrics server functionality (alternative to Pushgateway)

**What It Tests**:
- HTTP server starts on configured port
- `/metrics` endpoint returns Prometheus format
- Basic authentication works (when enabled)
- Server shutdown is graceful

**How to Run**:
```bash
poetry run pytest tests/integration/test_http_server_integration.py -v
```

#### `test_metrics_pushgateway.py`
**Purpose**: Unit tests for Pushgateway client

**What It Tests**:
- Push request formatting
- Error handling for network failures
- URL validation
- Metric serialization

**How to Run**:
```bash
poetry run pytest tests/integration/test_metrics_pushgateway.py -v
```

---

### Unit Tests

#### `test_registry_isolation.py`
**Purpose**: Ensure each test has isolated metrics registry

**What It Tests**:
- Registry created per test
- No metric leakage between tests
- Cleanup after test completion

#### `test_sampling_rate_effect.py`
**Purpose**: Verify sampling reduces overhead

**What It Tests**:
- 100% sampling records all metrics
- 10% sampling reduces write calls
- 0% sampling records nothing
- Statistical correctness

#### `test_histogram_bucket_config.py`
**Purpose**: Validate histogram bucket configuration

**What It Tests**:
- Custom bucket boundaries respected
- Default buckets for latency metrics
- Bucket count limits

#### `test_url_validation_ssrf.py`
**Purpose**: Security test for SSRF prevention

**What It Tests**:
- Reject private IPs (10.0.0.0/8, 192.168.0.0/16)
- Reject localhost/127.0.0.1
- Reject metadata endpoints (169.254.169.254)
- Allow valid public URLs

---

## Running Tests

### Run All Critical Tests

```bash
poetry run pytest tests/test_lazy_import.py \
                  tests/test_fire_and_forget_push_default_non_blocking.py \
                  tests/test_push_success_failure_counters.py \
                  tests/test_cardinality_cap_and_overflow.py \
                  tests/test_metrics_disabled_by_default.py \
                  tests/integration/test_integration_e2e.py::test_e2e_metrics_push_to_real_pushgateway \
                  -v
```

### Run All Tests

```bash
poetry run pytest tests/ -v
```

### Run Tests by Category

```bash
# Integration tests only
poetry run pytest tests/integration/ -v

# Unit tests only
poetry run pytest tests/unit/ -v

# Critical verification tests
poetry run pytest tests/test_*.py -v
```

### Run with Coverage

```bash
poetry run pytest tests/ --cov=crashlens --cov-report=html
```

### Run E2E Test (Requires Docker)

```bash
# Windows PowerShell
$env:TEST_PROMETHEUS_INTEGRATION="true"
poetry run pytest tests/integration/test_integration_e2e.py -v -s

# Linux/Mac
export TEST_PROMETHEUS_INTEGRATION=true
poetry run pytest tests/integration/test_integration_e2e.py -v -s
```

---

## Test Organization

### Naming Conventions

| Pattern | Purpose | Example |
|---------|---------|---------|
| `test_*.py` | Verification tests | `test_lazy_import.py` |
| `test_integration_*.py` | Integration tests | `test_integration_e2e.py` |
| `test_*_integration.py` | Component integration | `test_http_server_integration.py` |
| `test_unit_*.py` | Pure unit tests | `test_unit_parser.py` |

### Fixtures

**Location**: `tests/conftest.py`

Key fixtures:
- `docker_pushgateway`: Spins up real Pushgateway container
- `sample_log_file`: Creates test JSONL logs
- `metrics_instance`: Isolated CrashLensMetrics instance
- `clean_env`: Resets environment variables

---

## Debugging Test Failures

### Common Issues

#### 1. Docker Not Running

**Symptom**:
```
Error: Cannot connect to the Docker daemon
```

**Solution**:
```bash
# Windows: Start Docker Desktop
# Linux: sudo systemctl start docker
# Mac: Open Docker Desktop app
```

#### 2. Port Already in Use

**Symptom**:
```
Error: Port 9091 is already allocated
```

**Solution**:
```bash
# Find process using port
netstat -ano | findstr :9091  # Windows
lsof -i :9091                 # Mac/Linux

# Kill the process or change test port
```

#### 3. Environment Variable Not Set

**Symptom**:
```
SKIPPED: TEST_PROMETHEUS_INTEGRATION environment variable not set
```

**Solution**:
```bash
# Set the environment variable
$env:TEST_PROMETHEUS_INTEGRATION="true"  # PowerShell
export TEST_PROMETHEUS_INTEGRATION=true  # Bash
```

#### 4. Metrics Not Found in Pushgateway

**Symptom**:
```
AssertionError: CrashLens job not found in Pushgateway metrics
```

**Solution**:
- Verify environment variable: `CRASHLENS_METRICS_JOB`
- Check Pushgateway logs: `docker logs <container_id>`
- Query Pushgateway: `curl http://localhost:9091/metrics | grep crashlens`

---

## Test Maintenance

### Adding New Tests

1. Create test file following naming conventions
2. Add docstring explaining purpose
3. Use appropriate fixtures from `conftest.py`
4. Add test to this documentation
5. Update `run_verification_suite.py` if it's a verification test

### Updating Existing Tests

1. Update test code
2. Update documentation in this file
3. Run full test suite to ensure no regressions
4. Update version number in this document

### Deprecating Tests

1. Mark test as `@pytest.mark.skip` with reason
2. Document deprecation in this file
3. Remove after 2 release cycles

---

## Performance Benchmarks

| Test | Duration | Acceptable Range |
|------|----------|------------------|
| Test 1: Lazy Loading | 1.88s | 1-3s |
| Test 2: Fire-and-Forget | 3.05s | 3-5s |
| Test 3: Push Counters | 1.81s | 1-3s |
| Test 4: Cardinality Cap | 1.88s | 1-3s |
| Test 5: Disabled by Default | 1.86s | 1-3s |
| Test 6: E2E Integration | 10.80s | 8-15s |

**Total Suite**: ~21s (acceptable range: 15-30s)

---

## Continuous Integration

### GitHub Actions Configuration

The test suite runs automatically on:
- Push to `main` or `develop` branches
- Pull request creation/updates
- Manual workflow dispatch

**Workflow File**: `.github/workflows/ci.yml`

**Matrix**:
- Python: 3.10, 3.11, 3.12
- OS: ubuntu-latest, windows-latest, macos-latest

**E2E Tests**: Only run on Linux due to Docker requirements

---

## Support

For test-related questions:
1. Check this documentation first
2. Review test code and inline comments
3. Check GitHub Issues for known problems
4. Open new issue with test failure logs

**Maintainers**: CrashLens Core Team  
**Last Review**: 2025-01-24
