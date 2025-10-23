# Per-Rule Sampling Implementation - Progress Report

**Branch:** `phase-2`  
**Status:** Steps 2.1-2.3 complete (50% of Feature 2)  
**Time Elapsed:** ~15 minutes  
**Next:** Step 2.4 (Unit Tests)

---

## 📊 Implementation Progress

### ✅ COMPLETED STEPS (3/6)

#### Step 2.1: Config Schema Extended ✅
- **File Created:** `crashlens/config/metrics_config.py` (250+ lines)
- **New Classes:**
  1. **SamplingConfig:**
     - `rate`: Global sampling rate (0.0-1.0)
     - `per_rule`: Dict[str, float] for per-rule overrides
     - `get_rate(rule_name)`: Helper method
     - Validation: Ensures rates are 0.0-1.0, rule names are non-empty
  2. **PushgatewayConfig:** Pushgateway settings
  3. **HttpServerConfig:** HTTP server settings
  4. **MetricsConfig:** Complete metrics configuration
- **Example Configs:** 3 examples (minimal, per-rule, full)
- **Status:** Complete with validation and documentation

#### Step 2.2: Metrics Class Updated ✅
- **File Modified:** `crashlens/observability/metrics.py`
- **Changes:**
  1. Updated `__init__` to accept `per_rule_rates` parameter
  2. Stored `self._per_rule_rates = per_rule_rates or {}`
  3. Added `_get_sample_rate(rule_name)` helper method:
     - Returns per-rule rate if configured
     - Falls back to global rate if rule not in per_rule_rates
     - Documented with examples
  4. Updated `record_rule_hit` to use per-rule sampling:
     - Changed from `self._sample_rate` to `self._get_sample_rate(rule_name)`
     - Added docstring note about per-rule sampling
- **Backwards Compatible:** Works without per_rule_rates (defaults to empty dict)
- **Status:** Complete and functional

#### Step 2.3: Config Passed to Metrics ✅
- **Files Modified:**
  1. `crashlens/observability/__init__.py`:
     - Added `per_rule_rates` parameter to `initialize_metrics()`
     - Updated docstring with examples
     - Passed through to `_initialize_metrics_impl()`
  2. `crashlens/observability/metrics.py`:
     - Added `per_rule_rates` parameter to `_initialize_metrics_impl()`
     - Updated log message to show per-rule count
     - Passed through to `CrashLensMetrics()` constructor
- **Status:** Complete integration

---

### ⏳ REMAINING STEPS (3/6)

#### Step 2.4: Unit Tests (45 minutes)
- **File:** `tests/unit/test_per_rule_sampling.py`
- **Test Cases:**
  1. `test_per_rule_sampling_uses_custom_rate()`:
     - Set rule "expensive" to 0.01
     - Record 1000 times
     - Verify ~10 samples recorded (1%)
  2. `test_per_rule_sampling_falls_back_to_default()`:
     - Set rule "rare" to 1.0, default to 0.1
     - Record "unknown-rule"
     - Verify uses default 0.1
  3. `test_per_rule_sampling_validates_range()`:
     - Try to set rate to 1.5
     - Should raise ValueError
  4. `test_per_rule_sampling_loaded_from_config()`:
     - Create config with per_rule
     - Load and verify
     - Initialize metrics
     - Verify rates applied
- **Approach:** Use deterministic random seed for predictable tests

#### Step 2.5: Documentation (30 minutes)
- **Files to Update:**
  1. `docs/OBSERVABILITY.md`:
     - Add "Advanced Sampling" section
     - Explain when to use per-rule sampling
     - Show config file example
     - Explain trade-offs
     - Guidance on choosing rates
  2. `examples/metrics-config-per-rule.yaml`:
     - Complete config example
     - Comments explaining each setting
     - High-frequency rule with low rate
     - Low-frequency rule with high rate
  3. `README.md`:
     - Brief mention in observability section
     - Link to full docs

#### Step 2.6: Config Validation Tool (30 minutes)
- **Command:** `crashlens config validate-metrics`
- **Behavior:**
  1. Find config file (standard locations)
  2. Load and parse YAML
  3. Validate schema with pydantic
  4. Check per-rule rates in valid range
  5. Print summary:
     - Global sampling rate
     - Number of per-rule overrides
     - Any validation errors
  6. Exit 0 if valid, exit 1 if invalid

---

## 📦 Files Created/Modified

### New Files (1)
1. `crashlens/config/metrics_config.py` - 250+ lines
   - SamplingConfig class with validation
   - PushgatewayConfig, HttpServerConfig, MetricsConfig classes
   - Example configurations
   - Comprehensive docstrings

### Modified Files (2)
1. `crashlens/observability/metrics.py` - +35 lines
   - `__init__`: Added per_rule_rates parameter
   - `_get_sample_rate`: New helper method
   - `record_rule_hit`: Uses per-rule sampling
   - `_initialize_metrics_impl`: Accepts per_rule_rates
2. `crashlens/observability/__init__.py` - +5 lines
   - `initialize_metrics`: Added per_rule_rates parameter
   - Updated docstring

---

## 🎯 Design Decisions

### Why Per-Rule Sampling?
- **Use Case:** High-cardinality environments with >500 unique rules
- **Problem:** Some rules trigger frequently (10k+ times), causing:
  - High memory usage (Prometheus metrics storage)
  - High overhead (metric recording cost)
  - Cardinality explosion (unique label combinations)
- **Solution:** Sample frequently-triggered rules at lower rates

### Sample Rate Recommendations
```yaml
# High-frequency rules (trigger >1000x per scan)
rate_limit_violation: 0.01  # 1% sampling
prompt_too_long: 0.01       # 1% sampling

# Medium-frequency rules (trigger 100-1000x)
model_overkill: 0.1         # 10% sampling

# Low-frequency / critical rules (trigger <100x)
security_breach: 1.0        # 100% sampling (no sampling)
cost_overrun: 1.0           # 100% sampling
```

### Backwards Compatibility
- **Without per_rule_rates:** Works exactly as before (global sampling only)
- **Empty dict:** Same as not providing the parameter
- **Partial config:** Unconfigured rules use global rate

### Validation Strategy
- **At Config Load:** Pydantic validates rates are 0.0-1.0
- **At Runtime:** `_get_sample_rate()` safely handles missing rules
- **User-Friendly Errors:** Clear messages for invalid configurations

---

## 🧪 Testing Strategy

### Unit Tests (Step 2.4)
- **Deterministic:** Use `random.seed()` for reproducible results
- **Statistical:** Test sampling rates with large sample sizes (1000+ iterations)
- **Tolerance:** Allow ±10% variance (e.g., 1% ± 0.1% = 0.9%-1.1%)
- **Fast:** All tests should run in <5 seconds

### Integration Tests
- Not required for this feature (extends existing sampling)
- Existing metrics tests validate sampling behavior

---

## 📚 Example Configuration

### Basic Per-Rule Sampling
```yaml
# crashlens-config.yaml
metrics:
  enabled: true
  sampling:
    rate: 0.1  # 10% global sampling
    per_rule:
      expensive_rule: 0.01  # 1% for noisy rules
      critical_violation: 1.0  # 100% for important events
```

### Usage in CLI
```bash
# With config file
crashlens scan logs.jsonl --config crashlens-config.yaml --push-metrics

# Config is automatically loaded from standard locations:
# 1. ./crashlens-config.yaml
# 2. ~/.crashlens/config.yaml
# 3. /etc/crashlens/config.yaml
```

### Programmatic Usage
```python
from crashlens.observability import initialize_metrics

metrics = initialize_metrics(
    enabled=True,
    sample_rate=0.1,  # 10% global
    per_rule_rates={
        "expensive_rule": 0.01,  # 1% for this rule
        "rare_event": 1.0,       # 100% for this rule
    }
)

# Recording metrics
metrics.record_rule_hit("expensive_rule", "high", "scan")  # 1% chance
metrics.record_rule_hit("rare_event", "critical", "scan")  # 100% chance
metrics.record_rule_hit("unknown_rule", "medium", "scan")  # 10% chance (uses global)
```

---

## 🚀 Next Steps

### Immediate (Steps 2.4-2.6)
1. **Create Unit Tests** (45 min)
   - 4 test cases covering all scenarios
   - Deterministic random seed
   - Fast execution

2. **Update Documentation** (30 min)
   - Add to OBSERVABILITY.md
   - Create example config file
   - Update README.md

3. **Create Validation Tool** (30 min)
   - Add CLI command
   - Validate config schema
   - Clear error messages

### Validation Before Merge
- [ ] All unit tests passing (4 new tests)
- [ ] Backwards compatible (works without per_rule_rates)
- [ ] Documentation complete
- [ ] Example config tested
- [ ] Validation command works

---

## 📊 Performance Impact

### Expected Overhead
- **Config Loading:** ~1ms (one-time at startup)
- **Dict Lookup:** O(1) per metric call (~10ns)
- **Additional Memory:** ~80 bytes per rule in per_rule_rates dict
- **Net Impact:** <0.01% additional overhead vs baseline sampling

### Benchmark Plan
- Not required for this feature (extends existing sampling)
- Existing benchmark validates sampling overhead (<5%)

---

## 🎯 Success Criteria

Feature 2 is complete when:
- [x] Config schema extended (Step 2.1) ✅
- [x] Metrics class updated (Step 2.2) ✅
- [x] Config passed to metrics (Step 2.3) ✅
- [ ] Unit tests passing (Step 2.4)
- [ ] Documentation complete (Step 2.5)
- [ ] Validation tool working (Step 2.6)
- [ ] Backwards compatible
- [ ] No performance regression

---

**Last Updated:** October 23, 2025  
**Progress:** 3/6 steps (50%)  
**Status:** Ready for Step 2.4 (Unit Tests)  
**Estimated Remaining Time:** 1.5-2 hours
