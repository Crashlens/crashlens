# Phase 1, Day 1 - QUICK REFERENCE (Steps 4 & 5)

**Status:** ✅ COMPLETE - All 37 tests passing (100%)

---

## What Was Built

### Step 4: Fire-and-Forget Push ✅
- **File:** `crashlens/observability/server.py` (230 lines)
- **Key Functions:**
  - `validate_pushgateway_url()` - URL validation (http/https only)
  - `push_metrics_async()` - Non-blocking push with daemon threads
  - `get_pushgateway_url_from_env()` - Read from CRASHLENS_PUSHGATEWAY_URL
- **Features:**
  - Rotating log handler (1MB + 1MB backup = 2MB max)
  - Log path: `/tmp/crashlens-metrics.log` (Unix) or `%TEMP%\crashlens-metrics.log` (Windows)
  - Max wait: 2 seconds (configurable)
  - Daemon threads prevent blocking
  - Success/failure status updates (`metrics_push_status` gauge)

### Step 5: Mock Unit Tests ✅
- **File:** `tests/unit/test_metrics_mock.py` (370 lines)
- **Test Count:** 28 test cases
- **Framework:** pytest + unittest.mock
- **Key Coverage:**
  - Lazy import behavior
  - Kill switch (CRASHLENS_DISABLE_METRICS)
  - Cardinality protection (500-rule limit)
  - Severity normalization (10 cases)
  - URL validation (8 cases)
  - Fire-and-forget push non-blocking behavior
  - Daemon thread continuation
  - Singleton pattern

---

## Test Commands

### Run Mock Tests (WITHOUT prometheus-client)
```bash
poetry run pytest tests/unit/test_metrics_mock.py -v
# Result: 28/28 passing in ~21 seconds
```

### Run Functional Tests (WITH prometheus-client)
```bash
poetry run python scripts/test_observability.py
# Result: 9/9 passing
```

### Run All Observability Tests
```bash
poetry run pytest tests/unit/test_metrics_mock.py -v
poetry run python scripts/test_observability.py
# Combined: 37/37 passing (100%)
```

---

## Installation

### With Metrics Support
```bash
# Install with prometheus-client
poetry install -E metrics

# Or using pip
pip install crashlens[metrics]
```

### Without Metrics Support (CI)
```bash
# Install without optional dependencies
poetry install

# Tests still pass with mocks
poetry run pytest tests/unit/test_metrics_mock.py -v
# ✅ 28/28 passing
```

---

## Usage Example

```python
from crashlens.observability import initialize_metrics
from crashlens.observability.server import push_metrics_async

# 1. Initialize metrics
metrics = initialize_metrics(enabled=True, max_rules=500)

if metrics:
    # 2. Record some metrics
    metrics.record_rule_hit("excessive_retries", "high", "scan")
    metrics.record_violation("critical")
    metrics.record_trace_processed()
    
    # 3. Push to Pushgateway (fire-and-forget)
    push_metrics_async(
        gateway_url="http://localhost:9091",
        job_name="crashlens",
        max_wait=2.0,  # Return after 2s max
        metrics_instance=metrics
    )
    # Function returns in ≤2s, push continues in background
```

---

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CRASHLENS_DISABLE_METRICS` | Kill switch (disables all metrics) | `false` |
| `CRASHLENS_PUSHGATEWAY_URL` | Override pushgateway URL | `http://localhost:9091` |

**Example:**
```bash
export CRASHLENS_DISABLE_METRICS=true
# Metrics now disabled regardless of --metrics flag
```

---

## File Structure

```
crashlens/
├── observability/
│   ├── __init__.py          (67 lines)  - Public API
│   ├── metrics.py           (320 lines) - Metrics implementation
│   └── server.py            (230 lines) - Push implementation ✨ ENHANCED
tests/
└── unit/
    └── test_metrics_mock.py (370 lines) - Mock unit tests ✨ NEW
scripts/
└── test_observability.py    (224 lines) - Functional tests
```

**Total:** 1,211 lines of code (617 production + 594 test)

---

## Key Metrics

| Metric Name | Type | Labels | Purpose |
|-------------|------|--------|---------|
| `crashlens_rule_hits_total` | Counter | rule, severity, mode | Track rule evaluations |
| `crashlens_violations_total` | Counter | severity | Count policy violations |
| `crashlens_traces_processed_total` | Counter | - | Successful trace processing |
| `crashlens_traces_failed_total` | Counter | reason | Failed trace processing |
| `crashlens_decision_latency_avg_seconds` | Gauge | rule | Average rule eval time |
| `crashlens_decision_latency_max_seconds` | Gauge | rule | Max rule eval time |
| `crashlens_last_run_timestamp_seconds` | Gauge | status | Last scan timestamp |
| `crashlens_metrics_push_status` | Gauge | - | Push success (1) or failure (0) |
| `crashlens_label_overflow_total` | Counter | - | Cardinality limit overflows |

---

## Troubleshooting

### Issue: Tests failing with "prometheus_client not available"
**Solution:** Tests should use mocks. Ensure you're running `test_metrics_mock.py`, not `test_observability.py`.

```bash
# ✅ Correct (uses mocks)
poetry run pytest tests/unit/test_metrics_mock.py -v

# ❌ Wrong (requires prometheus-client)
poetry run python scripts/test_observability.py
```

### Issue: Push failures not visible
**Solution:** Check rotating log file:

```bash
# Unix/Linux/macOS
tail -f /tmp/crashlens-metrics.log

# Windows
Get-Content "$env:TEMP\crashlens-metrics.log" -Wait
```

### Issue: Cardinality limit reached
**Symptoms:** Log warning: `Rule cardinality limit reached (500). Collapsing to 'rule_overflow'`

**Solution:** Increase max_rules when initializing:

```python
metrics = initialize_metrics(enabled=True, max_rules=1000)
```

---

## What's Next (Phase 1, Day 2)

### Step 6: CLI Integration for `scan` Command
- Add `--metrics`, `--pushgateway-url`, `--metrics-job` flags
- Initialize metrics in scan command
- Record detector metrics (rule hits, violations)
- Push metrics at end of scan

### Step 7: CLI Integration for `policy-check` Command
- Record rule evaluation latencies
- Track violations by severity
- Push metrics on completion

### Step 8: Integration Tests
- Test scan with --metrics enabled
- Test policy-check with --metrics enabled
- Verify pushgateway receives metrics

### Step 9: Documentation Updates
- Add metrics section to USER_MANUAL.md
- Document all environment variables
- Add troubleshooting guide

---

## Sign-Off

✅ **Phase 1, Day 1 Complete**  
✅ **All 37 Tests Passing (100%)**  
✅ **Ready for Day 2 CLI Integration**

**No blockers. Proceed to Phase 1, Day 2.**

---

**Last Updated:** 2025-01-XX  
**Generated By:** GitHub Copilot (AI Coding Agent)
