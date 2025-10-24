# Prometheus Integration Verification Suite

**Self-Contained Terminal-Executable Tests for Production Readiness**

This test suite proves the CrashLens Prometheus integration meets production requirements through automated, reproducible tests that require **no external services** (no Prometheus, Grafana, or Pushgateway). All network I/O is mocked.

---

## ✅ Quick Verification (5 Minutes)

Run all tests to verify production readiness:

```bash
# 1. Activate virtual environment (if needed)
# poetry shell  # OR: python -m venv venv && source venv/bin/activate (Unix) / venv\Scripts\activate (Windows)

# 2. Install test dependencies
pip install -e .[dev,metrics]

# 3. Run all Prometheus integration tests
pytest tests/test_lazy_import.py -v
pytest tests/test_registry_isolation.py -v
pytest tests/test_cardinality_cap_and_overflow.py -v
pytest tests/test_fire_and_forget_push_default_non_blocking.py -v
pytest tests/test_fire_and_forget_push_strict_mode_fails.py -v
pytest tests/test_push_success_failure_counters.py -v
pytest tests/test_registry_cardinality_gauge_value.py -v
pytest tests/test_log_rotation_to_tmp.py -v

# 4. Run performance benchmark
python benchmarks/benchmark_memory_and_runtime.py

# Expected: All tests PASS, overhead <10%, memory <30MB
```

---

## 📋 Test Inventory

### Test 1: Lazy Import (`test_lazy_import.py`)
**Purpose:** Verify `prometheus_client` not loaded unless `CRASHLENS_ENABLE_METRICS=1`

**What It Proves:**
- Default imports don't load Prometheus libraries
- Zero overhead when metrics disabled
- Import time <500ms

**Run:**
```bash
pytest tests/test_lazy_import.py -v
# OR standalone: python tests/test_lazy_import.py
```

**Expected Output:**
```
✓ test_lazy_import_prometheus_client_not_loaded_by_default PASSED
✓ test_lazy_import_prometheus_client_loaded_when_enabled PASSED
✓ test_lazy_import_startup_time_overhead PASSED
```

---

### Test 2: Registry Isolation (`test_registry_isolation.py`)
**Purpose:** Verify `CollectorRegistry` per-run isolation (no cross-contamination)

**What It Proves:**
- Parallel scans don't interfere
- Metrics from run A don't appear in run B
- Registry reset between runs

**Run:**
```bash
pytest tests/test_registry_isolation.py -v
```

**Expected Output:**
```
✓ test_registry_isolation_separate_counters PASSED
✓ test_registry_isolation_multiple_metrics PASSED
✓ test_registry_reset_between_runs PASSED
```

---

### Test 3: Cardinality Cap (`test_cardinality_cap_and_overflow.py`)
**Purpose:** Verify 500 unique rule limit + overflow tracking

**What It Proves:**
- Max 500 unique policy rules tracked
- `crashlens_rules_overflow_total` counter increments for folded rules
- Memory constant even with 10,000 overflow events

**Run:**
```bash
pytest tests/test_cardinality_cap_and_overflow.py -v
```

**Expected Output:**
```
✓ test_cardinality_cap_enforced_at_500 PASSED
✓ test_cardinality_cap_no_overflow_under_limit PASSED
✓ test_cardinality_cap_repeated_hits_dont_overflow PASSED
✓ test_cardinality_cap_custom_limit PASSED
✓ test_cardinality_memory_constant PASSED
```

---

### Test 4: Non-Blocking Push (`test_fire_and_forget_push_default_non_blocking.py`)
**Purpose:** Verify push_to_gateway doesn't block main thread

**What It Proves:**
- Default 2s timeout with fire-and-forget
- Push returns in <500ms even if backend is slow (5s)
- No exceptions raised on timeout
- Daemon threads (don't block process exit)

**Run:**
```bash
pytest tests/test_fire_and_forget_push_default_non_blocking.py -v
```

**Expected Output:**
```
✓ test_fire_and_forget_completes_quickly_default_timeout PASSED
✓ test_fire_and_forget_doesnt_raise_on_timeout PASSED
✓ test_fire_and_forget_doesnt_raise_on_connection_error PASSED
✓ test_fire_and_forget_multiple_pushes_non_blocking PASSED
✓ test_fire_and_forget_daemon_thread PASSED
✓ test_fire_and_forget_custom_timeout PASSED
```

---

### Test 5: Strict Mode (`test_fire_and_forget_push_strict_mode_fails.py`)
**Purpose:** Verify strict mode raises on push failures

**What It Proves:**
- `CRASHLENS_METRICS_STRICT=1` enables blocking push
- `TimeoutError` raised on timeout
- `ConnectionError` raised on connection failure
- Non-strict mode (default) silently ignores errors

**Run:**
```bash
pytest tests/test_fire_and_forget_push_strict_mode_fails.py -v
```

**Expected Output:**
```
✓ test_strict_mode_raises_on_timeout PASSED
✓ test_strict_mode_raises_on_connection_error PASSED
✓ test_strict_mode_raises_on_http_error PASSED
✓ test_strict_mode_blocks_until_completion PASSED
✓ test_non_strict_mode_doesnt_raise PASSED
✓ test_non_strict_mode_returns_immediately PASSED
✓ test_strict_mode_env_var_detection PASSED
✓ test_strict_mode_success_doesnt_raise PASSED
```

---

### Test 6: Push Counters (`test_push_success_failure_counters.py`)
**Purpose:** Verify `crashlens_push_success_total` and `crashlens_push_failure_total`

**What It Proves:**
- Success counter increments on successful push
- Failure counter increments with `error_type` labels (timeout, connection, other)
- Counters accumulate correctly
- Independent counters (success doesn't affect failure)

**Run:**
```bash
pytest tests/test_push_success_failure_counters.py -v
```

**Expected Output:**
```
✓ test_push_success_counter_increments PASSED
✓ test_push_failure_counter_increments_on_timeout PASSED
✓ test_push_failure_counter_increments_on_connection_error PASSED
✓ test_push_counters_accumulate_correctly PASSED
✓ test_push_counters_independent PASSED
✓ test_push_failure_other_error_type PASSED
✓ test_push_counters_prometheus_format PASSED
```

---

### Test 7: Cardinality Gauge (`test_registry_cardinality_gauge_value.py`)
**Purpose:** Verify `crashlens_registry_cardinality` gauge accuracy

**What It Proves:**
- Gauge value equals unique rules tracked
- Updates as rules added
- Respects 500 cap
- Repeated rules don't increment
- Type=gauge (not counter)

**Run:**
```bash
pytest tests/test_registry_cardinality_gauge_value.py -v
```

**Expected Output:**
```
✓ test_cardinality_gauge_reflects_unique_rules PASSED
✓ test_cardinality_gauge_updates_as_rules_added PASSED
✓ test_cardinality_gauge_respects_cap PASSED
✓ test_cardinality_gauge_repeated_rules_dont_increment PASSED
✓ test_cardinality_gauge_prometheus_format PASSED
✓ test_cardinality_gauge_zero_initial_value PASSED
✓ test_cardinality_gauge_large_values PASSED
✓ test_cardinality_gauge_decrements_on_cleanup PASSED
```

---

### Test 8: Log Rotation (`test_log_rotation_to_tmp.py`)
**Purpose:** Verify metrics logs rotate correctly at size threshold

**What It Proves:**
- Logs written to `/tmp/crashlens-metrics.log`
- Rotation triggered when exceeding maxBytes
- Backup count respected (old logs deleted)
- Individual files under size limit
- No data loss during rotation

**Run:**
```bash
pytest tests/test_log_rotation_to_tmp.py -v
```

**Expected Output:**
```
✓ test_log_rotation_creates_backup_files PASSED
✓ test_log_rotation_respects_backup_count PASSED
✓ test_log_rotation_individual_files_under_limit PASSED
✓ test_log_rotation_no_data_loss PASSED
✓ test_log_rotation_custom_path PASSED
✓ test_log_rotation_concurrent_writes PASSED
✓ test_log_rotation_empty_log_behavior PASSED
✓ test_log_rotation_permissions PASSED
```

---

### Benchmark: Memory & Runtime Overhead (`benchmark_memory_and_runtime.py`)
**Purpose:** Measure performance impact of metrics collection

**What It Proves:**
- Runtime overhead <10%
- Memory overhead <30MB
- Statistical validity (3 runs averaged)

**Run:**
```bash
# Default workload (1000 traces, 10 policies)
python benchmarks/benchmark_memory_and_runtime.py

# Custom workload
python benchmarks/benchmark_memory_and_runtime.py --traces 5000 --policies 20 --runs 5

# JSON output for CI
python benchmarks/benchmark_memory_and_runtime.py --json-only --output results.json
```

**Expected Output:**
```
======================================================================
CRASHLENS PROMETHEUS METRICS OVERHEAD BENCHMARK
======================================================================
Configuration:
  Traces: 1000
  Policies: 10
  Runs: 3
  Memory tracking: resource

Running baseline (metrics disabled)...
  Run 1: 0.123s, mem: 2.5MB delta
  Run 2: 0.119s, mem: 2.4MB delta
  Run 3: 0.121s, mem: 2.5MB delta
Baseline average: 0.121s, mem: 2.5MB

Running with metrics enabled...
  Run 1: 0.131s, mem: 5.2MB delta
  Run 2: 0.129s, mem: 5.1MB delta
  Run 3: 0.132s, mem: 5.3MB delta
Metrics average: 0.131s, mem: 5.2MB

======================================================================
RESULTS
======================================================================
Runtime Overhead: +8.26% (0.121s → 0.131s)
  Threshold: <10%
  Status: ✓ PASS

Memory Overhead: +2.7MB (2.5MB → 5.2MB)
  Threshold: <30MB
  Status: ✓ PASS

======================================================================
OVERALL: ✓ PASS - Metrics overhead within acceptable limits
======================================================================
```

---

## 🛠️ Advanced Usage

### Run All Tests at Once
```bash
# All Prometheus tests
pytest tests/test_lazy_import.py tests/test_registry_isolation.py tests/test_cardinality_cap_and_overflow.py tests/test_fire_and_forget_push_default_non_blocking.py tests/test_fire_and_forget_push_strict_mode_fails.py tests/test_push_success_failure_counters.py tests/test_registry_cardinality_gauge_value.py tests/test_log_rotation_to_tmp.py -v

# OR: Use pattern matching
pytest tests/test_*prometheus*.py tests/test_lazy*.py tests/test_registry*.py tests/test_cardinality*.py tests/test_fire*.py tests/test_push*.py tests/test_log_rotation*.py -v
```

### Standalone Execution (No pytest)
Each test file can run independently:
```bash
python tests/test_lazy_import.py
python tests/test_registry_isolation.py
python tests/test_cardinality_cap_and_overflow.py
# ... etc
```

### Skip Slow Tests
```bash
pytest tests/ -v -m "not slow"
```

### Run with Coverage
```bash
pytest tests/test_lazy_import.py --cov=crashlens.observability --cov-report=term
```

### Environment Variables
```bash
# Enable strict mode for testing
export CRASHLENS_METRICS_STRICT=1
pytest tests/test_fire_and_forget_push_strict_mode_fails.py -v

# Enable metrics for lazy loading test
export CRASHLENS_ENABLE_METRICS=1
pytest tests/test_lazy_import.py::test_lazy_import_prometheus_client_loaded_when_enabled -v
```

---

## 🚦 CI Integration

### GitHub Actions Example
```yaml
name: Prometheus Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install -e .[dev,metrics]
      
      - name: Run Prometheus tests
        run: |
          pytest tests/test_lazy_import.py -v
          pytest tests/test_registry_isolation.py -v
          pytest tests/test_cardinality_cap_and_overflow.py -v
          pytest tests/test_fire_and_forget_push_default_non_blocking.py -v
          pytest tests/test_fire_and_forget_push_strict_mode_fails.py -v
          pytest tests/test_push_success_failure_counters.py -v
          pytest tests/test_registry_cardinality_gauge_value.py -v
          pytest tests/test_log_rotation_to_tmp.py -v
      
      - name: Run benchmark
        run: |
          python benchmarks/benchmark_memory_and_runtime.py --json-only --output benchmark-results.json
      
      - name: Check thresholds
        run: |
          python -c "
          import json
          with open('benchmark-results.json') as f:
              results = json.load(f)
          assert results['results']['overall_pass'], 'Benchmark failed!'
          print('✓ All checks passed')
          "
```

---

## 📊 Test Coverage Summary

| Test File | Tests | What It Proves |
|-----------|-------|----------------|
| `test_lazy_import.py` | 3 | Lazy loading, <500ms import |
| `test_registry_isolation.py` | 3 | Registry per-run, no cross-contamination |
| `test_cardinality_cap_and_overflow.py` | 5 | 500 rule cap, overflow tracking, constant memory |
| `test_fire_and_forget_push_default_non_blocking.py` | 6 | Non-blocking push, <500ms return, daemon threads |
| `test_fire_and_forget_push_strict_mode_fails.py` | 8 | Strict mode errors, blocking behavior |
| `test_push_success_failure_counters.py` | 7 | Push metrics, error_type labels |
| `test_registry_cardinality_gauge_value.py` | 8 | Gauge accuracy, type=gauge |
| `test_log_rotation_to_tmp.py` | 8 | Log rotation, backup count, no data loss |
| `benchmark_memory_and_runtime.py` | 1 | <10% runtime, <30MB memory |
| **TOTAL** | **49** | **Production readiness proven** |

---

## 🎯 Acceptance Criteria

**All tests must pass for production readiness:**

- [x] **Lazy Loading:** prometheus_client not imported unless enabled
- [x] **Registry Isolation:** Parallel scans don't interfere
- [x] **Cardinality Cap:** Max 500 rules, overflow tracked
- [x] **Non-Blocking Push:** Returns <500ms, daemon threads
- [x] **Strict Mode:** Raises on errors when enabled
- [x] **Push Counters:** Success/failure tracking
- [x] **Cardinality Gauge:** Accurate unique rule count
- [x] **Log Rotation:** Size-based rotation, no data loss
- [x] **Performance:** <10% runtime overhead
- [x] **Memory:** <30MB memory overhead

---

## 🐛 Troubleshooting

### Test Failures

**"prometheus_client not installed"**
```bash
pip install prometheus-client
# OR: pip install -e .[metrics]
```

**"Module not found: crashlens"**
```bash
# Install in editable mode
pip install -e .
```

**"Memory tracking unavailable"**
- Unix: `resource` module used automatically
- Windows: Install psutil: `pip install psutil`
- Benchmark will skip memory checks if unavailable (still tests runtime)

**Timing-sensitive test failures**
- Tests allow tolerance (e.g., 500ms for <500ms target)
- Slow CI runners may fail timing tests (increase tolerance in test code if needed)

### Standalone Execution Issues

**"No module named 'pytest'"**
```bash
# Use standalone execution (no pytest needed)
python tests/test_lazy_import.py
```

**Environment variables not working**
- Windows PowerShell: `$env:CRASHLENS_ENABLE_METRICS=1`
- Windows CMD: `set CRASHLENS_ENABLE_METRICS=1`
- Unix/Mac: `export CRASHLENS_ENABLE_METRICS=1`

---

## 📝 Test Maintenance

### Adding New Tests

1. Create test file in `tests/test_<feature>.py`
2. Follow established pattern:
   - Module docstring with purpose + acceptance criteria
   - Import guard for optional dependencies
   - Multiple test functions (3-8 per file)
   - pytest.mark.skipif decorators
   - Main block for standalone execution
3. Add to this README's test inventory
4. Run `pytest <new_file> -v` to verify

### Updating Fixtures

Edit `tests/conftest.py` to add shared fixtures. Available fixtures:
- `reset_modules()` - Clean sys.modules
- `mock_push_to_gateway()` - Mock Prometheus push
- `mock_registry()` - Fresh CollectorRegistry
- `clean_env()` - Environment variable cleanup
- `sample_traces()` - Generate test trace data
- `sample_policies()` - Generate test policy rules

---

## 🎓 For Reviewers / Seed Funding Demo

**Quick Validation Commands:**
```bash
# 1. Clone repo
git clone <repo> && cd crashlens

# 2. Install + run all tests (5 minutes)
pip install -e .[dev,metrics]
pytest tests/test_*.py -v
python benchmarks/benchmark_memory_and_runtime.py

# 3. Expected: 48 tests PASSED, 1 benchmark PASSED
#    Output: Runtime overhead <10%, Memory overhead <30MB
```

**This suite proves:**
1. ✅ **No production impact** - <10% overhead, lazy loading
2. ✅ **Constant memory** - 500 rule cap, overflow tracking
3. ✅ **Non-blocking** - Fire-and-forget push, daemon threads
4. ✅ **Reliable** - 49 automated tests, all passing
5. ✅ **Reproducible** - Terminal-executable, no external services

---

**Last Updated:** 2025-01-XX  
**Test Suite Version:** 1.0  
**Total Tests:** 49 (48 unit + 1 benchmark)
