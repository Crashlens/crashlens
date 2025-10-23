# Phase 1, Day 1 - Quick Reference

## ✅ What Was Built

**Observability Module** - Complete Prometheus metrics integration

- **3 Files Created:** `__init__.py`, `metrics.py`, `server.py`
- **9 Metrics:** 7 application + 2 self-monitoring
- **Test Suite:** 9/9 tests passing
- **Time:** 4 hours (target: 6-8h)

---

## 🚀 How to Use (Ready for Day 2 Integration)

### 1. Enable Metrics
```python
from crashlens.observability import initialize_metrics

# In CLI entry point (cli.py)
metrics = initialize_metrics(enabled=True, max_rules=500)
```

### 2. Record Metrics
```python
from crashlens.observability import get_metrics

metrics = get_metrics()
if metrics:
    # Record rule hits
    metrics.record_rule_hit('retry-loop', 'high', 'scan')
    
    # Record violations
    metrics.record_violation('critical')
    
    # Track processing
    metrics.record_trace_processed()
    metrics.record_trace_failed('parse_error')
    
    # Update latency
    metrics.update_decision_latency('my-rule', 0.001, 0.005)
    
    # Update timestamp
    metrics.update_run_timestamp('success')
```

### 3. Push to Pushgateway
```python
from crashlens.observability.server import push_metrics_fire_and_forget

# Non-blocking push (returns immediately)
push_metrics_fire_and_forget(
    pushgateway_url="http://localhost:9091",
    job_name="crashlens"
)
```

---

## 📊 Metrics Available

| Metric | Type | Labels | Purpose |
|--------|------|--------|---------|
| `crashlens_rule_hits_total` | Counter | rule, severity, mode | Rule triggers |
| `crashlens_violations_total` | Counter | severity | Policy violations |
| `crashlens_traces_processed_total` | Counter | - | Traces analyzed |
| `crashlens_traces_failed_total` | Counter | reason | Failed traces |
| `crashlens_decision_latency_avg_seconds` | Gauge | rule | Avg latency |
| `crashlens_decision_latency_max_seconds` | Gauge | rule | Max latency |
| `crashlens_last_run_timestamp_seconds` | Gauge | status | Last run time |
| `crashlens_metrics_push_status` | Gauge | - | Push health |
| `crashlens_rule_label_overflow_total` | Counter | - | Cardinality hits |

---

## 🔒 Safety Features

### Kill Switch
```bash
export CRASHLENS_DISABLE_METRICS=true  # Disables all metrics
```

### Cardinality Protection
- **Default:** 500 unique rule names
- **Overflow:** Excess → `rule_overflow` label
- **Monitoring:** `crashlens_rule_label_overflow_total`

### Severity Whitelist
- **Allowed:** critical, high, medium, low, info
- **Unknown:** Normalized to `info`

---

## 🧪 Testing

```bash
# Run test suite
poetry run python scripts/test_observability.py

# Expected: 9/9 tests passing
```

---

## 📦 Installation

```bash
# With metrics
pip install crashlens[metrics]

# Without metrics (default)
pip install crashlens
```

---

## 🔜 Next: Phase 1, Day 2

### CLI Integration Checklist:
- [ ] Add `--push-metrics` flag to scan command
- [ ] Add `--pushgateway-url` option
- [ ] Call `initialize_metrics()` in CLI entry point
- [ ] Record metrics in PolicyEngine
- [ ] Record metrics in parser
- [ ] Push metrics on completion
- [ ] Add integration tests
- [ ] Update documentation

**Estimated:** 6 hours

---

## 📚 Key Files

```
crashlens/observability/
├── __init__.py      - Public API
├── metrics.py       - Core implementation
└── server.py        - Pushgateway push

scripts/
└── test_observability.py  - Test suite

docs/
└── PHASE1_DAY1_COMPLETE.md  - Full report
```

---

**Status:** ✅ READY FOR DAY 2  
**Branch:** `feat/prometheus-metrics-mvp`
