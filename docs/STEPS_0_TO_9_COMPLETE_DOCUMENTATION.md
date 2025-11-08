# CrashLens Guard/Policy-Check Merge - Complete Implementation Documentation

> **⚠️ HISTORICAL DOCUMENTATION**: This document describes the implementation of Steps 0-9 that built the unified PolicyEngine with a feature flag (`CRASHLENS_USE_UNIFIED_ENGINE`). As of 2025-11-08, Step 10 has been completed and the feature flag has been removed. This document is preserved for historical reference.
>
> **Current Reality (Post-Step 10):**
> - The unified PolicyEngine is the only execution path
> - The `CRASHLENS_USE_UNIFIED_ENGINE` feature flag has been removed
> - Legacy code has been deleted
> - CrashLens launched directly at v1.0 with unified engine only (no gradual rollout)
>
> For technical details about the feature flag era (Steps 0-9), continue reading below.

---

**Date:** November 8, 2025  
**Commits:** 000 through 009 (12 commits total)  
**Status:** Steps 0-9 COMPLETE, Step 10 COMPLETED (2025-11-08)  
**Final Commit:** `4d5ff0f` (Step 9)

---

## Executive Summary

This document provides comprehensive technical documentation for the 10-step guard/policy-check merge implementation in CrashLens. **Steps 0-9 were completed and the feature flag architecture was fully implemented**. **Step 10 (deprecation removal) was subsequently completed**, removing the feature flag and legacy code.

### Architecture Overview (Historical - Steps 0-9)

**State During Steps 0-9:**
- ✅ **Two CLI commands existed**: `guard` (in `crashlens/guard.py`) and `policy-check` (alias in `crashlens/cli.py`)
- ✅ **Unified engine implemented**: `GuardPolicyEngineAdapter` bridged legacy and new systems
- ✅ **Feature flag control**: `CRASHLENS_USE_UNIFIED_ENGINE=1` enabled unified engine
- ✅ **Backwards compatible**: Default was legacy mode (`CRASHLENS_USE_UNIFIED_ENGINE=0`)
- ✅ **Production ready**: 177+ tests passing, benchmarks showed 14.1% performance improvement, 100% parity

**Step 10 Completion (2025-11-08):**
- ✅ **Feature flag removed**: `CRASHLENS_USE_UNIFIED_ENGINE` deleted from codebase
- ✅ **Legacy code removed**: Single execution path (unified engine only)
- ✅ **Tests updated**: All env dict arguments and monkeypatch usage removed
- ✅ **Docs updated**: Migration documentation archived

---

## Table of Contents

1. [Files Added by Step](#files-added-by-step)
2. [Functions and Logic Added](#functions-and-logic-added)
3. [Files Modified](#files-modified)
4. [Files Removed](#files-removed-none)
5. [Architecture Diagrams](#architecture-diagrams)
6. [Step 10 Blocking Analysis](#step-10-blocking-analysis)
7. [Testing Summary](#testing-summary)
8. [Performance Benchmarks](#performance-benchmarks)

---

## Files Added by Step

### Step 0: Repository Initialization (Commit 000)
**Purpose:** Foundation setup for 9-step migration

**Files Created:**
- `docs/migration_teardown.md` (148 lines)
  - **Purpose:** Safety mechanisms and rollback procedures
  - **Key Content:** Feature flag documentation, migration phases, parity gates, rollback procedures
  - **Logic:** Defines 4-phase migration (Preparation → Integration → Deprecation → Removal)

---

### Step 1: Rule Translator (Commit 001)
**Purpose:** Convert legacy guard rule format to PolicyEngine YAML format

**Files Created:**
- `crashlens/policy/rule_translator.py` (287 lines)
  - **Purpose:** Bidirectional translation between rule formats
  - **Key Functions:**
    * `translate_guard_to_policy(guard_rule: Dict) -> Dict` - Convert guard rule to policy YAML
    * `translate_policy_to_guard(policy_rule: Dict) -> Dict` - Convert policy YAML to guard rule
    * `_translate_condition(condition: Dict, target_format: str) -> Dict` - Convert condition syntax
  - **Logic:** 
    - Maps guard operators (`gt`, `gte`, `lt`, `lte`, `eq`, `in`, `regex`) to policy operators (`>`, `>=`, `<`, `<=`, `==`, `in:[...]`, `regex:...`)
    - Handles nested conditions with dot notation (e.g., `usage.prompt_tokens`)
    - Preserves rule metadata (ID, severity, description, suggestion)

**Tests Created:**
- `tests/test_rule_translator.py` (420 lines)
  - 18 test cases covering bidirectional translation, edge cases, error handling

**Documentation:**
- `docs/STEP_1_RULE_TRANSLATOR_COMPLETE.md` (312 lines)

---

### Step 2: Shared Ingestion Layer (Commit 002)
**Purpose:** Unified JSONL parsing for both guard and policy-check

**Files Created:**
- `crashlens/parsers/shared_ingestion.py` (245 lines)
  - **Purpose:** Single source of truth for log parsing
  - **Key Functions:**
    * `ingest_jsonl(file_path: Path, schema_version: str) -> Dict[str, List[Dict]]` - Parse JSONL file
    * `validate_record(record: Dict, schema_version: str) -> bool` - Schema validation
    * `group_by_trace_id(records: List[Dict]) -> Dict[str, List[Dict]]` - Group records by traceId
  - **Logic:**
    - Supports multiple schema versions (langfuse-v1, langfuse-v2)
    - Groups records by `traceId` for trace-level analysis
    - Validates required fields: `traceId`, `model`, `prompt_tokens`, `completion_tokens`

**Tests Created:**
- `tests/test_shared_ingestion.py` (312 lines)
  - 14 test cases for parsing, validation, grouping, error handling

**Documentation:**
- `docs/STEP_2_INGESTION_SUMMARY.md` (187 lines)

---

### Step 3: Detector Driver (Commit 003)
**Purpose:** Orchestrate multiple detectors with priority-based suppression

**Files Created:**
- `crashlens/detectors/detector_driver.py` (398 lines)
  - **Purpose:** Run detectors in priority order, prevent double-counting
  - **Key Functions:**
    * `run_detectors(traces: Dict, detectors: List, model_pricing: Dict) -> List[Dict]` - Execute detector pipeline
    * `suppress_lower_priority(detections: List[Dict]) -> List[Dict]` - Remove duplicate detections
    * `enrich_with_metadata(detection: Dict, trace_data: Dict) -> Dict` - Add context to detections
  - **Logic:**
    - Priority order: RetryLoopDetector > FallbackStormDetector > OverkillModelDetector > FallbackFailureDetector
    - Tracks `already_flagged_ids` set to prevent re-flagging same trace
    - Enriches detections with model pricing, token counts, cost estimates

**Tests Created:**
- `tests/test_detector_driver.py` (487 lines)
  - 22 test cases for priority suppression, enrichment, multi-detector scenarios

**Documentation:**
- `docs/STEP_3_DETECTOR_DRIVER_SUMMARY.md` (256 lines)

---

### Step 4: Guard Adapter (Commits 004, 005)
**Purpose:** Integrate PolicyEngine into guard command via adapter pattern

**Files Created:**
- `crashlens/guard_adapter.py` (445 lines)
  - **Purpose:** Bridge between guard CLI and unified PolicyEngine
  - **Key Classes:**
    * `GuardPolicyEngineAdapter` - Main adapter class
      - `run(log_path: Path, rules_path: Path, **kwargs) -> Dict` - Execute policy check with guard parameters
      - `_convert_policy_output_to_guard_format(policy_result: Dict) -> Dict` - Transform output
      - `_apply_guard_filters(violations: List, suppress: List, severity: List) -> List` - Filter violations
  - **Logic:**
    - Checks `CRASHLENS_USE_UNIFIED_ENGINE` environment variable
    - If enabled (`=1`): Route to PolicyEngine
    - If disabled (`=0`, default): Use legacy guard evaluator
    - Translates PolicyEngine output to legacy guard format for backwards compatibility

**Tests Created:**
- `tests/test_guard_adapter.py` (612 lines)
  - 28 test cases for feature flag, output conversion, filter application, error handling

**Documentation:**
- `docs/STEP_4_GUARD_POLICYENGINE_ADAPTER_SUMMARY.md` (412 lines)
- `docs/STEP_4_PHASE_2_GUARD_INTEGRATION_COMPLETE.md` (398 lines)

---

### Step 5: Backwards Compatibility Tests (Commit 006)
**Purpose:** Ensure unified engine produces identical output to legacy

**Files Created:**
- `tests/test_guard_policyengine_integration.py` (845 lines)
  - **Purpose:** End-to-end parity tests between legacy and unified modes
  - **Key Test Classes:**
    * `TestGuardUnifiedIntegration` - Feature flag behavior tests
    * `TestOutputParity` - Output format equivalence tests
    * `TestPerformanceParity` - Performance regression tests
  - **Test Coverage:**
    - Feature flag toggling (ON/OFF)
    - Output format conversion (policy → guard)
    - Filter application (suppress, severity)
    - Error handling parity
    - Performance benchmarking (time, memory)

**Documentation:**
- `docs/STEP_5_BACKWARDS_COMPAT_COMPLETE.md` (287 lines)

---

### Step 6: Baseline Injection (Commit 007)
**Purpose:** Add baseline comparison support to unified engine

**Files Created:**
- `crashlens/policy/baseline_injector.py` (312 lines)
  - **Purpose:** Inject historical baseline data into rule evaluation context
  - **Key Functions:**
    * `inject_baseline_context(policy_rules: List[Dict], baseline_data: Dict) -> List[Dict]` - Add baseline to rules
    * `compute_baseline_stats(historical_logs: List[Dict]) -> Dict` - Calculate historical metrics
    * `generate_deviation_rules(baseline_stats: Dict, threshold: float) -> List[Dict]` - Auto-generate deviation rules
  - **Logic:**
    - Computes p50/p95/p99 latency, avg cost, error rate from historical logs
    - Injects as rule context: `{{baseline.p95_latency}}`, `{{baseline.avg_cost}}`
    - Generates dynamic rules: "Flag if current > baseline * (1 + threshold)"

**Tests Created:**
- `tests/test_baseline_injector.py` (398 lines)
  - 18 test cases for baseline computation, injection, deviation detection

**Documentation:**
- `docs/STEP_6_BASELINE_INJECTION_COMPLETE.md` (312 lines)

---

### Step 7: CLI Alias (Commit 008)
**Purpose:** Create `policy-check` command as alias to `guard` with unified engine enabled

**Files Modified:**
- `crashlens/cli.py` (added 78 lines for `policy-check` command)
  - **Location:** Lines 4079-4170
  - **Key Logic:**
    ```python
    @click.command("policy-check")
    # ... all same options as guard ...
    def policy_check(...):
        # Force unified engine
        os.environ['CRASHLENS_USE_UNIFIED_ENGINE'] = '1'
        
        # Call guard with all parameters
        ctx = Context(guard)
        ctx.invoke(guard, ...)
    ```
  - **Behavior:**
    - `crashlens policy-check` → Calls `guard()` with `CRASHLENS_USE_UNIFIED_ENGINE=1`
    - Identical parameters to `guard` command
    - Shows message: "🔧 Using unified PolicyEngine (next-generation analysis)"

- `crashlens/guard.py` (added deprecation warning)
  - **Location:** Lines 887-900
  - **Key Logic:**
    ```python
    if not os.getenv('CRASHLENS_USE_UNIFIED_ENGINE') and not os.getenv('CRASHLENS_QUIET'):
        click.echo("⚠️  DEPRECATION NOTICE: Legacy guard engine", err=True)
        click.echo("   Next-generation: crashlens policy-check", err=True)
        click.echo("   Or: export CRASHLENS_USE_UNIFIED_ENGINE=1", err=True)
    ```
  - **Behavior:**
    - Warning shown when `guard` used WITHOUT unified engine
    - Suppressed if `CRASHLENS_QUIET=1` or `CRASHLENS_USE_UNIFIED_ENGINE=1`

**Tests Created:**
- `tests/test_cli_alias.py` (612 lines)
  - 20 test cases for alias behavior, env var persistence, deprecation warnings

**Documentation:**
- `docs/STEP_7_CLI_ALIAS_COMPLETE.md` (398 lines)

---

### Step 8: Performance Benchmarks (Commit 009)
**Purpose:** Validate unified engine performance vs legacy

**Files Created:**
- `bench/benchmark_unified.py` (420 lines)
  - **Purpose:** Cross-platform Python benchmark runner
  - **Key Classes:**
    * `PerformanceBenchmark` - Benchmark orchestrator
      - `run_command(cmd: List[str], env: Dict) -> Tuple[float, float, int]` - Execute and measure
      - `compare_results(legacy: Dict, unified: Dict) -> Dict` - Compare metrics
  - **Metrics Collected:**
    - Wall time (seconds)
    - Peak RSS memory (MB)
    - Exit code
  - **Thresholds:**
    - Time: Unified ≤ Legacy + 15%
    - Memory: Unified ≤ Legacy + 25%

- `bench/benchmark_unified.sh` (180 lines)
  - **Purpose:** Bash benchmark for Linux/macOS with native tools
  - **Tools Used:**
    - `time -v` for memory profiling
    - `mprof` (memory_profiler) for detailed plots
  - **Output:** JSON results + memory plots

- `.github/workflows/bench-unified.yml` (170 lines)
  - **Purpose:** CI workflow for automated benchmarks on PRs
  - **Triggers:** Pull requests, workflow_dispatch
  - **Jobs:**
    1. Run benchmarks (Python 3.12, ubuntu-latest)
    2. Generate results table
    3. Comment on PR with results
    4. Upload artifacts (30-day retention)

**Benchmark Results (Local):**
- Legacy: 2.34s, 145.2 MB
- Unified: 2.01s, 145.3 MB
- **Improvement: 14.1% FASTER, 0.1% more memory** ✅

**Tests Created:**
- Benchmark scripts are self-testing (exit code validation)

**Documentation:**
- `docs/STEP_8_BENCHMARKS_COMPLETE.md` (312 lines)

---

### Step 9: Integration Tests + Canary (Commit 010, commit hash `4d5ff0f`)
**Purpose:** End-to-end parity validation and safe deployment workflow

**Files Created:**
- `tests/integration/test_parity_end_to_end.py` (560 lines)
  - **Purpose:** Comprehensive parity testing framework
  - **Key Classes:**
    * `ParityTester` - Parity test orchestrator
      - `run_policy_check(log_path: Path, policy_path: Path) -> ParityResult` - Run policy-check command
      - `run_guard_unified(log_path: Path, policy_path: Path) -> ParityResult` - Run guard with unified engine
      - `compare_results(pc_result: ParityResult, guard_result: ParityResult) -> Tuple[bool, List[str]]` - Compare outputs
      - `generate_diff_diagnostics(pc_result: ParityResult, guard_result: ParityResult) -> str` - Detailed diff report
    * `ParityResult` - Result container
      - Fields: `violations_found`, `severity_buckets`, `exit_code`, `stdout`, `stderr`, `execution_time_ms`
    * `TestParityEndToEnd` - pytest test suite
      - `test_parity_for_all_templates()` - Test all 5 policy templates
      - Individual tests for each template (block-gpt4-on-summary, ci-sample, fallback-chain-detector, max-cost-per-trace, retry-loop-detector)
  - **Parity Validation:**
    - Violation counts: ±1% tolerance
    - Severity buckets: Exact match required
    - Exit codes: Must match
  - **Test Results:** 5/5 templates passing with 100% exact match

- `.github/workflows/canary.yml` (220 lines)
  - **Purpose:** Multi-stage canary deployment with automatic rollback
  - **Triggers:** Push to `internal/canary` branch, workflow_dispatch
  - **Stages:**
    1. **Parity Tests** (automated)
       - Run `test_parity_end_to_end.py` on all templates
       - Upload artifacts (90-day retention)
       - Fail workflow if any template fails
    2. **Integration Tests** (automated, depends on Stage 1)
       - Full integration test suite
       - Upload test results
    3. **Manual Sign-Off** (manual approval required)
       - Checkpoint before merge
       - Requires manual workflow approval
    4. **Automatic Rollback** (on failure)
       - Triggered by any stage failure
       - Creates rollback issue with diagnostics
       - Notifies team
  - **Rollback Actions:**
    - Set `CRASHLENS_USE_UNIFIED_ENGINE=0` in environment
    - Create GitHub issue with failure logs
    - Notify via Slack (if webhook configured)

**Documentation:**
- `docs/STEP_9_INTEGRATION_COMPLETE.md` (412 lines)

---

## Functions and Logic Added

### Core Abstraction: GuardPolicyEngineAdapter

**Purpose:** Provide seamless switching between legacy and unified engines without CLI changes

**Key Methods:**

#### `GuardPolicyEngineAdapter.__init__(self, verbose: bool = False)`
- **Purpose:** Initialize adapter with configuration
- **Parameters:**
  - `verbose`: Enable debug logging
- **Logic:** Sets up logging, validates dependencies

#### `GuardPolicyEngineAdapter.run(log_path: Path, rules_path: Path, **kwargs) -> Dict`
- **Purpose:** Execute policy check with guard-compatible interface
- **Parameters:**
  - `log_path`: Path to JSONL log file
  - `rules_path`: Path to YAML rules file
  - `**kwargs`: Additional options (suppress, severity, output format, etc.)
- **Returns:** Dictionary with keys:
  - `violations`: List of violation dicts
  - `total_violations`: Count
  - `severity_breakdown`: Dict of {severity: count}
  - `exit_code`: 0 (pass) or 1 (violations found)
- **Logic:**
  1. Parse JSONL logs using `shared_ingestion.ingest_jsonl()`
  2. Load YAML rules, translate to PolicyEngine format if needed
  3. Run PolicyEngine evaluation
  4. Convert output to guard format using `_convert_policy_output_to_guard_format()`
  5. Apply filters (suppress, severity) using `_apply_guard_filters()`
  6. Return formatted result

#### `GuardPolicyEngineAdapter._convert_policy_output_to_guard_format(policy_result: Dict) -> Dict`
- **Purpose:** Transform PolicyEngine output to legacy guard output format
- **Input:** PolicyEngine result dict (YAML-style severity, rule IDs)
- **Output:** Guard result dict (legacy format)
- **Logic:**
  - Maps PolicyEngine severity (`critical`, `high`, `medium`, `low`) to guard severity (`error`, `warn`, `info`)
  - Renames keys: `rule_id` → `rule`, `log_entry` → `record`
  - Preserves all detection metadata (trace_id, cost, tokens, description, suggestion)

#### `GuardPolicyEngineAdapter._apply_guard_filters(violations: List, suppress: List, severity: List) -> List`
- **Purpose:** Apply guard-style filtering to violation list
- **Parameters:**
  - `violations`: List of violation dicts
  - `suppress`: List of rule IDs to suppress
  - `severity`: List of severity levels to include
- **Returns:** Filtered violation list
- **Logic:**
  - Remove violations where `rule_id in suppress`
  - Keep violations where `severity in severity` (if severity filter specified)
  - Preserve original ordering

### Feature Flag System

**Module:** `crashlens/utils/feature_flags.py`

#### `is_unified_engine_enabled() -> bool`
- **Purpose:** Check if unified engine is enabled
- **Returns:** `True` if `CRASHLENS_USE_UNIFIED_ENGINE=1`, else `False`
- **Default:** `False` (legacy mode)

#### `get_unified_engine_mode() -> str`
- **Purpose:** Get current engine mode
- **Returns:** `'1'` (unified) or `'0'` (legacy)

#### `set_unified_engine_mode(enabled: bool) -> None`
- **Purpose:** Programmatically set unified engine mode
- **Parameters:** `enabled` - `True` for unified, `False` for legacy
- **Side Effect:** Sets `CRASHLENS_USE_UNIFIED_ENGINE` env var

### Rule Translation Logic

**Module:** `crashlens/policy/rule_translator.py`

#### `translate_guard_to_policy(guard_rule: Dict) -> Dict`
- **Purpose:** Convert guard rule format to PolicyEngine YAML format
- **Input Example:**
  ```python
  {
    "id": "excessive_retries",
    "condition": {"retry_count": {"gt": 3}},
    "severity": "error",
    "description": "Too many retries",
    "suggestion": "Implement circuit breaker"
  }
  ```
- **Output Example:**
  ```python
  {
    "id": "excessive_retries",
    "match": {"retry_count": ">3"},
    "action": "fail",
    "severity": "high",
    "description": "Too many retries",
    "suggestion": "Implement circuit breaker"
  }
  ```
- **Logic:**
  - Operator mapping: `gt` → `>`, `gte` → `>=`, `lt` → `<`, `lte` → `<=`, `eq` → `==`
  - Severity mapping: `error` → `high`, `warn` → `medium`, `info` → `low`, `fatal` → `critical`
  - Action mapping: `error`/`fatal` → `fail`, `warn` → `warn`, `info` → `block`

#### `translate_policy_to_guard(policy_rule: Dict) -> Dict`
- **Purpose:** Reverse conversion (PolicyEngine → guard)
- **Logic:** Inverse of `translate_guard_to_policy()`

### Baseline Injection Logic

**Module:** `crashlens/policy/baseline_injector.py`

#### `compute_baseline_stats(historical_logs: List[Dict]) -> Dict`
- **Purpose:** Calculate statistical baseline from historical logs
- **Input:** List of JSONL log entries from previous period
- **Output:**
  ```python
  {
    "p50_latency": 234.5,        # milliseconds
    "p95_latency": 456.7,
    "p99_latency": 789.2,
    "avg_cost": 0.0023,          # USD
    "total_cost": 45.67,
    "error_rate": 0.012,          # 1.2%
    "total_requests": 12345
  }
  ```
- **Logic:**
  - Extracts latency from `endTime - startTime`
  - Calculates percentiles using `numpy.percentile()` (if available) or manual sorting
  - Computes error rate from `level == 'ERROR'` records
  - Sums cost from `cost` field

#### `inject_baseline_context(policy_rules: List[Dict], baseline_data: Dict) -> List[Dict]`
- **Purpose:** Add baseline data to rule evaluation context
- **Logic:**
  - For each rule, add `baseline` field with stats
  - Enable templating in rule conditions: `"latency": ">{{baseline.p95_latency * 1.5}}"`
  - Rules can now reference historical context

#### `generate_deviation_rules(baseline_stats: Dict, threshold: float) -> List[Dict]`
- **Purpose:** Auto-generate rules for baseline deviations
- **Parameters:**
  - `baseline_stats`: Output from `compute_baseline_stats()`
  - `threshold`: Deviation tolerance (e.g., 0.30 for 30%)
- **Generated Rules:**
  - Latency deviation: `current_latency > baseline.p95_latency * (1 + threshold)`
  - Cost deviation: `current_cost > baseline.avg_cost * (1 + threshold)`
  - Error rate spike: `current_error_rate > baseline.error_rate * (1 + threshold)`

### Parity Testing Logic

**Module:** `tests/integration/test_parity_end_to_end.py`

#### `ParityTester.compare_results(pc_result: ParityResult, guard_result: ParityResult, policy_name: str) -> Tuple[bool, List[str]]`
- **Purpose:** Compare policy-check and guard outputs for equivalence
- **Parameters:**
  - `pc_result`: Result from `crashlens policy-check`
  - `guard_result`: Result from `crashlens guard` with `CRASHLENS_USE_UNIFIED_ENGINE=1`
  - `policy_name`: Policy template name (for diagnostics)
- **Returns:**
  - `bool`: `True` if parity achieved, `False` otherwise
  - `List[str]`: List of discrepancy descriptions
- **Validation Criteria:**
  1. **Violation Count Parity:** `|pc_violations - guard_violations| / pc_violations <= 0.01` (±1%)
  2. **Severity Bucket Parity:** Exact match required for `{critical: X, high: Y, medium: Z, low: W}`
  3. **Exit Code Parity:** Must match exactly
- **Logic:**
  ```python
  issues = []
  
  # Check violation count
  diff_percent = abs(pc_violations - guard_violations) / pc_violations * 100
  if diff_percent > PARITY_THRESHOLD_PERCENT:  # 1.0%
      issues.append(f"Violation count mismatch: {pc_violations} vs {guard_violations}")
  
  # Check severity buckets
  if pc_result.severity_buckets != guard_result.severity_buckets:
      issues.append(f"Severity bucket mismatch: {pc_buckets} vs {guard_buckets}")
  
  # Check exit codes
  if pc_result.exit_code != guard_result.exit_code:
      issues.append(f"Exit code mismatch: {pc_exit} vs {guard_exit}")
  
  return len(issues) == 0, issues
  ```

#### `ParityTester.generate_diff_diagnostics(pc_result: ParityResult, guard_result: ParityResult) -> str`
- **Purpose:** Generate detailed diff report for debugging parity failures
- **Output:** Markdown-formatted report with:
  - Side-by-side violation count comparison
  - Severity bucket breakdown
  - Execution time comparison
  - stdout/stderr diffs
  - Sample violation details

---

## Files Modified

### `crashlens/cli.py`
**Lines Modified:** 4079-4170, 4670-4677

**Changes:**
1. **Added `policy-check` command** (Lines 4079-4170)
   - Duplicate of `guard` command signature
   - Sets `CRASHLENS_USE_UNIFIED_ENGINE=1` before calling `guard()`
   - Displays unified engine message

2. **Registered commands** (Lines 4670-4677)
   - Added: `cli.add_command(policy_check)` (appears twice, second is Step 7 alias)
   - Added: `cli.add_command(guard)`

**Rationale:** Provide `policy-check` as next-gen interface while keeping `guard` for backwards compatibility

---

### `crashlens/guard.py`
**Lines Modified:** 887-900, 942-955

**Changes:**
1. **Added deprecation warning** (Lines 887-900)
   - Shown when `guard` used WITHOUT `CRASHLENS_USE_UNIFIED_ENGINE=1`
   - Suppressed if `CRASHLENS_QUIET=1`
   - Message: "⚠️ DEPRECATION NOTICE: Legacy guard engine"

2. **Added unified engine check** (Lines 942-955)
   ```python
   use_unified_engine = os.getenv("CRASHLENS_USE_UNIFIED_ENGINE", "0") == "1"
   if use_unified_engine:
       click.echo("🔧 Using unified PolicyEngine (CRASHLENS_USE_UNIFIED_ENGINE=1)", err=True)
       from .guard_adapter import GuardPolicyEngineAdapter
       adapter = GuardPolicyEngineAdapter(verbose=verbose)
       result = adapter.run(logfile, rules, ...)
       # Handle result, apply formatting, exit
   else:
       # Legacy code path (original guard logic)
       ...
   ```

**Rationale:** Route to unified engine when feature flag enabled, maintain legacy path as default

---

### `.gitignore`
**Lines Added:** 3 lines

**Changes:**
- `bench/results/` - Ignore benchmark result files
- `*.dat` - Ignore memory profiler data files
- `*.png` - Ignore memory profiler plots

**Rationale:** Prevent benchmark artifacts from being committed

---

## Files Removed (NONE)

**NO FILES WERE REMOVED in Steps 0-9.**

**Why:** Migration strategy prioritizes backwards compatibility and safe rollout. Feature flag allows instant rollback by disabling unified engine. Legacy code remains as fallback.

**Future Removal (Step 10, BLOCKED):**
When Step 10 conditions are met (2+ production releases, <5% legacy usage telemetry), the following files would be removed:
- `crashlens/guard.py` - Legacy evaluator logic (keep CLI shell that errors)
- Feature flag checks in `guard_adapter.py`
- Legacy-specific tests

**BUT:** Step 10 is blocked until June 2026 (see Section 6 for details).

---

## Architecture Diagrams

### Current Architecture (Post Steps 0-9)

```
┌─────────────────────────────────────────────────────────────┐
│                         User CLI                            │
└─────────────────────────────────────────────────────────────┘
                │                          │
                │                          │
                ▼                          ▼
┌───────────────────────────┐   ┌──────────────────────────┐
│  crashlens guard          │   │  crashlens policy-check  │
│  (guard.py)               │   │  (cli.py alias)          │
│                           │   │                          │
│  DEFAULT:                 │   │  FORCES:                 │
│  CRASHLENS_USE_           │   │  CRASHLENS_USE_          │
│  UNIFIED_ENGINE=0         │   │  UNIFIED_ENGINE=1        │
└───────────────────────────┘   └──────────────────────────┘
                │                          │
                │                          │
                └──────────┬───────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │  Feature Flag Check        │
              │  CRASHLENS_USE_UNIFIED_    │
              │  ENGINE == "1" ?           │
              └────────────────────────────┘
                     │              │
                     │ Yes          │ No
                     ▼              ▼
      ┌──────────────────────┐   ┌─────────────────────────┐
      │ Unified Engine Path  │   │ Legacy Engine Path      │
      │ (guard_adapter.py)   │   │ (guard.py original)     │
      └──────────────────────┘   └─────────────────────────┘
                     │                       │
                     ▼                       ▼
      ┌──────────────────────┐   ┌─────────────────────────┐
      │ GuardPolicyEngine    │   │ Legacy Guard Evaluator  │
      │ Adapter              │   │                         │
      │                      │   │ - Direct rule eval      │
      │ 1. Shared Ingestion  │   │ - No detector driver    │
      │ 2. Rule Translator   │   │ - Original output fmt   │
      │ 3. Detector Driver   │   │                         │
      │ 4. PolicyEngine      │   │                         │
      │ 5. Output Converter  │   │                         │
      │ 6. Filter Application│   │                         │
      └──────────────────────┘   └─────────────────────────┘
                     │                       │
                     └───────────┬───────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Unified Output Format │
                    │  (guard-compatible)    │
                    └────────────────────────┘
```

### Data Flow: policy-check Command (Unified Engine)

```
crashlens policy-check logs.jsonl --rules policy.yaml
    │
    ├─> cli.py: policy_check() function (Line 4109)
    │   └─> Set CRASHLENS_USE_UNIFIED_ENGINE=1
    │   └─> ctx.invoke(guard, ...)
    │
    ├─> guard.py: guard() function (Line 942)
    │   └─> Check os.getenv("CRASHLENS_USE_UNIFIED_ENGINE")
    │   └─> "1" detected → Unified path
    │
    ├─> guard_adapter.py: GuardPolicyEngineAdapter.run()
    │   │
    │   ├─> shared_ingestion.ingest_jsonl(logs.jsonl)
    │   │   └─> Returns: {traceId: [records], ...}
    │   │
    │   ├─> rule_translator.translate_guard_to_policy(policy.yaml)
    │   │   └─> Convert guard format → PolicyEngine YAML
    │   │
    │   ├─> detector_driver.run_detectors(traces, detectors)
    │   │   └─> Priority: Retry > Fallback > Overkill > Failure
    │   │   └─> Returns: [detection1, detection2, ...]
    │   │
    │   ├─> policy_engine.evaluate(traces, rules)
    │   │   └─> Match rules against log entries
    │   │   └─> Returns: [violation1, violation2, ...]
    │   │
    │   ├─> _convert_policy_output_to_guard_format(violations)
    │   │   └─> Map PolicyEngine → guard format
    │   │
    │   └─> _apply_guard_filters(violations, suppress, severity)
    │       └─> Apply CLI filters
    │
    └─> Output: Guard-compatible format (JSON/Markdown/Text)
```

### Data Flow: guard Command (Legacy Engine)

```
crashlens guard logs.jsonl --rules policy.yaml
    │
    ├─> guard.py: guard() function (Line 942)
    │   └─> Check os.getenv("CRASHLENS_USE_UNIFIED_ENGINE")
    │   └─> "0" or unset → Legacy path
    │
    ├─> guard.py: Legacy evaluator (original code)
    │   │
    │   ├─> Direct JSONL parsing (no shared_ingestion)
    │   │   └─> Parse each line with json.loads()
    │   │
    │   ├─> Load rules (YAML or guard format)
    │   │   └─> No translation needed
    │   │
    │   ├─> Rule evaluation loop
    │   │   └─> For each record, check rule conditions
    │   │   └─> No detector driver (inline detection)
    │   │
    │   └─> Format output (original guard formatter)
    │
    └─> Output: Original guard format
```

---

## Step 10 Blocking Analysis

### Why Step 10 Cannot Be Implemented

**Step 10 Objective:** Remove legacy code, delete `CRASHLENS_USE_UNIFIED_ENGINE` feature flag, make unified engine the only implementation.

**Blocking Factors:**

#### 1. Prerequisites Not Met (Per Migration Spec)

**Required Conditions (from `docs/migration_teardown.md`):**
- ✅ **Condition 1:** 2+ production releases with unified as default
  - **Status:** ❌ FAILED - Zero releases, unified not deployed
  - **Current:** Steps 0-9 committed, no v3.0.0 release yet
  
- ✅ **Condition 2:** Telemetry shows legacy usage <5%
  - **Status:** ❌ FAILED - No telemetry infrastructure deployed
  - **Current:** Prometheus metrics exist in code but not running in production
  
- ✅ **Condition 3:** No unresolved rollback incidents
  - **Status:** ❌ N/A - Nothing in production to roll back
  - **Current:** Cannot validate without production deployment

**Timeline:**
- **Current Date:** November 8, 2025
- **Earliest v3.0.0 Release:** November 2025 (this week)
- **v3.1.0 (Canary Rollout):** January 2026 (4-8 weeks after v3.0.0)
- **v3.2.0 (Deprecation Warnings):** March-April 2026 (8-12 weeks after v3.1.0)
- **v4.0.0 (Step 10):** June-September 2026 (12-24 weeks after v3.2.0, if <5% legacy usage)

**Earliest Step 10 Date:** **June 2026** (7-8 months from now)

#### 2. Telemetry Infrastructure Not Operational

**What's Missing:**
- ❌ Prometheus metrics not deployed in production
- ❌ Grafana dashboards not configured with production data
- ❌ Telemetry collection not enabled
- ❌ No usage data: Cannot determine if legacy usage <5%

**What Exists (Code Only):**
- ✅ Prometheus client instrumentation in code (`crashlens/observability/`)
- ✅ Metrics config examples (`examples/metrics-config-*.yaml`)
- ✅ Grafana dashboard JSON (`dashboards/crashlens-policy-enforcement.json`)
- ✅ Alert rules (`dashboards/crashlens-alert-rules.yml`)

**Gap:** Infrastructure code exists but not running in production environment.

#### 3. Parity Validation Only Local

**Current Validation:**
- ✅ 5/5 policy templates pass parity tests locally
- ✅ 100% exact match on violation counts
- ✅ Identical severity buckets
- ✅ Exit codes match

**What's Missing:**
- ❌ No production workload validation
- ❌ No real user logs tested (only synthetic test fixtures)
- ❌ No long-running stability data (months of continuous operation)
- ❌ No edge case discovery from production failures

**Risk:** Local parity ≠ production parity. Real-world logs may expose untested edge cases.

#### 4. No User Communication or Migration Period

**Step 10 Requirement (from spec):**
> "After 2 release cycles of deprecation"

**Current State:**
- ❌ Zero deprecation announcements made
- ❌ Zero user communication sent
- ❌ No migration guide published externally
- ❌ No grace period provided for users to adapt

**Standard Software Practice:**
- Deprecation announcement: 3-6 months before removal
- Breaking change warning: Major version bump (v3.x → v4.0)
- User survey: Confirm <5% still using legacy

**Gap:** Cannot remove code without user notification and grace period.

#### 5. Safety-First Philosophy Violation

**From Project Instructions:**
> "Safety-first: prefer short-lived feature flags to reckless rewrites. Work incrementally; each step must leave the repo in a fully testable state."

**Step 10 Without Production Validation:**
- ❌ Removes safety net (feature flag) before validating it's safe to remove
- ❌ No rollback path if production issues discovered post-removal
- ❌ Violates "testable state" requirement (cannot test without deployment)

**Proper Sequence:**
1. Deploy → 2. Validate → 3. Remove

**Attempting:** ~~Deploy~~ → ~~Validate~~ → Remove (skip first two steps = UNSAFE)

#### 6. Architectural Confusion in Original Spec

**Original Step 10 Spec Stated:**
> "Remove `policy-check` implementation, keep CLI alias that errors and instructs usage of `guard --fast-template`"

**This is Backwards:**
- **Current Architecture:** `guard` is legacy, `policy-check` uses unified engine
- **Spec Implies:** `policy-check` is old, `guard` is new
- **Contradiction:** Steps 0-9 built unified engine FOR `policy-check`, not `guard`

**Actual Current State:**
- `guard` = Legacy OR unified (via feature flag)
- `policy-check` = Unified ONLY (alias that forces flag)

**If Step 10 Executed As Spec:**
- Would remove the new unified engine code (policy-check)
- Would keep the legacy code (guard)
- **Result:** Backwards migration, deletes all Steps 0-9 work

**Clarification Needed:** Step 10 spec needs revision to match actual architecture.

---

### What SHOULD Happen Before Step 10

#### Phase A: Production Deployment (v3.0.0 → v3.1.0)
**Timeline:** November 2025 - January 2026 (2-3 months)

1. **Tag v3.0.0 Release** (This Week)
   ```bash
   git tag -a v3.0.0 -m "feat: Unified engine with feature flag (default OFF)"
   git push origin v3.0.0
   poetry build
   poetry publish
   ```

2. **Deploy v3.0.0 to Production**
   - Default: `CRASHLENS_USE_UNIFIED_ENGINE=0` (legacy mode)
   - Enable Prometheus metrics collection
   - Configure Grafana dashboards
   - Set up alerting (error rate, parity violations, performance)

3. **Monitor v3.0.0 for 4-8 Weeks**
   - Collect baseline metrics (error rate, latency, memory)
   - No unified engine usage yet (just infrastructure deployment)
   - Validate telemetry pipeline working

4. **Canary Rollout v3.1.0** (January 2026)
   - Push to `internal/canary` branch (triggers `.github/workflows/canary.yml`)
   - Gradual rollout: 10% → 25% → 50% → 100% over 4-8 weeks
   - Each stage: Run parity tests, monitor metrics, wait 1-2 weeks
   - If ANY stage fails: Automatic rollback via canary workflow

5. **Release v3.1.0** (After Canary Success)
   - Change default: `CRASHLENS_USE_UNIFIED_ENGINE=1`
   - Legacy still available: `CRASHLENS_USE_UNIFIED_ENGINE=0`
   - Announce in release notes: "Unified engine now default"

#### Phase B: Deprecation Period (v3.2.0)
**Timeline:** March-April 2026 (2-3 months after v3.1.0)

1. **Add Deprecation Warnings** (Already Done in Step 7)
   - Warning shown when `CRASHLENS_USE_UNIFIED_ENGINE=0` used
   - Message: "Legacy engine will be removed in v4.0.0"

2. **Collect Legacy Usage Telemetry**
   - Prometheus metric: `crashlens_engine_type{type="legacy"}` vs `{type="unified"}`
   - Track percentage over time
   - Target: <5% legacy usage before proceeding

3. **User Communication**
   - Blog post: "Unified engine now stable, legacy deprecated"
   - Email list: Announce deprecation timeline
   - GitHub discussions: Field questions, provide support
   - Survey: Ask legacy users why they haven't migrated

4. **Monitor for 12-24 Weeks**
   - Wait for legacy usage to drop naturally
   - Provide migration assistance to holdouts
   - Extend timeline if needed (safety > speed)

#### Phase C: Final Validation (Pre-Step 10)
**Timeline:** June 2026 (3-4 months after v3.2.0)

1. **Validate Prerequisites**
   - ✅ 2+ releases with unified as default (v3.1.0, v3.2.0)
   - ✅ Telemetry shows <5% legacy usage for 8+ weeks
   - ✅ Zero critical rollback incidents in 6+ months
   - ✅ Parity gates passing continuously in production
   - ✅ Performance gates passing continuously

2. **Stakeholder Sign-Off**
   - Engineering: Review metrics, confirm stability
   - Product: Confirm user feedback positive
   - Support: Confirm no unresolved incidents
   - Security: Audit unified engine, approve removal

3. **Create LTS Branch (Optional)**
   - If >5% legacy users remain, consider:
   - Tag `v3.9.9-lts` as last version with legacy support
   - Maintain security patches on LTS branch for 6-12 months
   - Communicate: "Upgrade to v4.0+ or stay on v3.x LTS"

4. **Final Pre-Release Checklist**
   - [ ] All prerequisites met
   - [ ] Stakeholder approvals documented
   - [ ] Rollback plan tested
   - [ ] User communication sent (3+ months notice)
   - [ ] LTS branch created (if needed)
   - [ ] Step 10 implementation reviewed and approved

**THEN AND ONLY THEN:** Proceed with Step 10.

---

### Risks of Premature Step 10 Execution

#### Risk 1: Production Breakage
**Scenario:** Remove feature flag, discover critical bug in unified engine

**Without Feature Flag:**
- ❌ No instant rollback capability
- ❌ Must revert entire release (hours of downtime)
- ❌ Users stuck with broken version

**With Feature Flag (Current):**
- ✅ Set `CRASHLENS_USE_UNIFIED_ENGINE=0` (instant rollback)
- ✅ Zero downtime
- ✅ Fix bug, re-enable flag when ready

**Impact:** High severity, affects all users

#### Risk 2: Hidden Edge Cases
**Scenario:** Real production workload exposes untested code paths

**Current Testing:**
- ✅ Synthetic test fixtures (demo logs)
- ✅ 5 policy templates validated
- ❌ No real user logs tested at scale
- ❌ No long-running stability data

**Production Reality:**
- Diverse log formats
- Edge case rule combinations
- High-volume workloads (1M+ traces)
- Time-dependent bugs (memory leaks over days)

**Risk:** Unified engine may fail on patterns never seen in testing

#### Risk 3: User Churn
**Scenario:** Remove legacy without notice, users find breaking changes

**Result:**
- ❌ Loss of user trust
- ❌ Negative reviews
- ❌ Users fork project or switch tools
- ❌ Support burden increases

**Proper Approach:**
- ✅ 3-6 month deprecation notice
- ✅ Migration guide published
- ✅ Support channel for questions
- ✅ LTS branch for holdouts

#### Risk 4: Rollback Complexity
**Scenario:** v4.0.0 (Step 10) deployed, critical bug found

**Rollback After Feature Flag Removed:**
```bash
# Must revert entire release
git revert <v4.0.0-commit-hash>
poetry build
poetry publish  # Emergency v4.0.1 with revert
# Users must upgrade again (friction)
```

**Rollback With Feature Flag (Current):**
```bash
# Environment variable change (zero downtime)
export CRASHLENS_USE_UNIFIED_ENGINE=0
# OR Kubernetes
kubectl set env deployment/crashlens CRASHLENS_USE_UNIFIED_ENGINE=0
# Instant rollback, no new release needed
```

**Impact:** Hours vs minutes of downtime

---

### Decision Matrix: When Step 10 Is Safe

| Criteria | Current Status | Required Status | Met? |
|----------|---------------|-----------------|------|
| **Releases** | 0 releases | 2+ releases (v3.1.0, v3.2.0) | ❌ |
| **Legacy Usage** | Unknown (no telemetry) | <5% for 8+ weeks | ❌ |
| **Production Time** | 0 days | 6+ months (v3.0.0 → v3.2.0) | ❌ |
| **Parity Gates** | Local only (100% pass) | Production (6+ months passing) | ❌ |
| **Performance Gates** | Benchmarks pass (+14.1%) | Production (6+ months passing) | ❌ |
| **Rollback Incidents** | N/A (no deployment) | Zero unresolved | ❌ |
| **User Communication** | None | 3+ months notice | ❌ |
| **Stakeholder Approval** | Not requested | All signed off | ❌ |

**Summary:** 0/8 criteria met. **Step 10 is UNSAFE to proceed.**

**Recommendation:** Wait until **June 2026** or later, after all criteria validated in production.

---

## Testing Summary

### Test Coverage by Step

| Step | Test File | Tests Added | Total Tests | Pass Rate |
|------|-----------|-------------|-------------|-----------|
| 0 | (None) | 0 | 0 | N/A |
| 1 | `test_rule_translator.py` | 18 | 18 | 100% |
| 2 | `test_shared_ingestion.py` | 14 | 32 | 100% |
| 3 | `test_detector_driver.py` | 22 | 54 | 100% |
| 4 | `test_guard_adapter.py` | 28 | 82 | 100% |
| 5 | `test_guard_policyengine_integration.py` | 35 | 117 | 100% |
| 6 | `test_baseline_injector.py` | 18 | 135 | 100% |
| 7 | `test_cli_alias.py` | 20 | 155 | 100% |
| 8 | (Benchmark scripts) | 0 | 155 | N/A |
| 9 | `test_parity_end_to_end.py` | 22 | 177 | 100% |

**Total Test Count:** 177 tests  
**Pass Rate:** 100%  
**Test Types:** Unit tests, integration tests, parity tests, benchmark validation

### Test Execution

**Command:**
```bash
poetry run pytest tests/ -v
```

**Output (Summarized):**
```
=============================== test session starts ===============================
platform win32 -- Python 3.12.10, pytest-8.4.1
collected 177 items

tests/test_rule_translator.py ..................                           [ 10%]
tests/test_shared_ingestion.py ..............                             [ 18%]
tests/test_detector_driver.py ......................                      [ 30%]
tests/test_guard_adapter.py ............................                  [ 46%]
tests/test_guard_policyengine_integration.py ...................................
                                                                           [ 66%]
tests/test_baseline_injector.py ..................                        [ 76%]
tests/test_cli_alias.py ....................                              [ 87%]
tests/integration/test_parity_end_to_end.py ......................        [100%]

============================== 177 passed in 45.23s ===============================
```

### Parity Test Results (Step 9)

**Test Command:**
```bash
poetry run python tests/integration/test_parity_end_to_end.py
```

**Output:**
```
Running parity tests for all policy templates...

Testing: block-gpt4-on-summary
  policy-check: 3 violations (critical:1, high:1, medium:1)
  guard+unified: 3 violations (critical:1, high:1, medium:1)
  ✅ PASS - Exact match

Testing: ci-sample
  policy-check: 5 violations (high:2, medium:3)
  guard+unified: 5 violations (high:2, medium:3)
  ✅ PASS - Exact match

Testing: fallback-chain-detector
  policy-check: 8 violations (high:3, medium:5)
  guard+unified: 8 violations (high:3, medium:5)
  ✅ PASS - Exact match

Testing: max-cost-per-trace
  policy-check: 2 violations (critical:2)
  guard+unified: 2 violations (critical:2)
  ✅ PASS - Exact match

Testing: retry-loop-detector
  policy-check: 12 violations (high:4, medium:8)
  guard+unified: 12 violations (high:4, medium:8)
  ✅ PASS - Exact match

========================================
✅ ALL PARITY TESTS PASSED (5/5)
========================================

Summary:
- Total templates tested: 5
- Exact matches: 5 (100%)
- Parity threshold: ±1% violations, exact severity buckets
- Achieved: 0% deviation (perfect parity)
```

**Validation:**
- ✅ Violation counts: Exact match (0% deviation, well under ±1% threshold)
- ✅ Severity buckets: Identical across all templates
- ✅ Exit codes: Matching
- ✅ Execution time: Within 10% (performance parity)

---

## Performance Benchmarks

### Benchmark Results (Step 8)

**Test Environment:**
- OS: Windows 11
- CPU: Intel Core i7-12700K (12 cores, 20 threads)
- RAM: 32 GB DDR4
- Python: 3.12.10
- Test File: `sample-logs/demo-logs.jsonl` (1,247 lines, 845 KB)
- Policy: `policies/retry-loop-detector.yaml` (3 rules)

**Command Executed:**
```bash
poetry run python bench/benchmark_unified.py
```

**Results:**

| Metric | Legacy | Unified | Difference | Pass? |
|--------|--------|---------|------------|-------|
| **Wall Time** | 2.34s | 2.01s | -0.33s (-14.1%) | ✅ |
| **Peak RSS** | 145.2 MB | 145.3 MB | +0.1 MB (+0.1%) | ✅ |
| **Exit Code** | 0 | 0 | Matching | ✅ |

**Thresholds:**
- Time: Unified ≤ Legacy + 15% → **2.01s ≤ 2.69s** ✅ PASS
- Memory: Unified ≤ Legacy + 25% → **145.3 MB ≤ 181.5 MB** ✅ PASS

**Analysis:**
- **Unified engine is FASTER:** 14.1% improvement (not regression!)
- **Memory neutral:** 0.1% increase (effectively identical)
- **Validation:** Exceeds performance requirements

**Why Unified Is Faster:**
1. **Shared Ingestion:** Parses JSONL once, reuses for all detectors
2. **Detector Driver:** Efficient priority-based suppression (avoid duplicate work)
3. **Compiled Regex:** PolicyEngine pre-compiles regex patterns
4. **Optimized Data Structures:** Dict-based lookups instead of list scans

---

## Appendix: Key Configuration Files

### Feature Flag Usage

**Environment Variable:**
```bash
# Enable unified engine (default OFF)
export CRASHLENS_USE_UNIFIED_ENGINE=1

# Disable unified engine (legacy mode)
export CRASHLENS_USE_UNIFIED_ENGINE=0

# Suppress deprecation warnings
export CRASHLENS_QUIET=1
```

**CLI Commands:**
```bash
# Use unified engine explicitly
crashlens policy-check logs.jsonl --rules policy.yaml

# Use legacy engine (with deprecation warning)
crashlens guard logs.jsonl --rules policy.yaml

# Use legacy engine (suppress warning)
CRASHLENS_QUIET=1 crashlens guard logs.jsonl --rules policy.yaml

# Force unified engine for guard command
CRASHLENS_USE_UNIFIED_ENGINE=1 crashlens guard logs.jsonl --rules policy.yaml
```

### Canary Deployment Workflow

**Trigger Canary Rollout:**
```bash
# Create and push canary branch
git checkout -b internal/canary
git push origin internal/canary

# Workflow automatically runs:
# 1. Parity tests (all 5 templates)
# 2. Integration tests
# 3. Waits for manual sign-off
# 4. Merges to main OR rolls back on failure
```

**Manual Rollback:**
```bash
# Option 1: Environment variable (instant)
export CRASHLENS_USE_UNIFIED_ENGINE=0

# Option 2: Git revert
git revert <problematic-commit>
git push origin main

# Option 3: Restore previous release
git checkout v3.0.0
git tag -a v3.x.y -m "hotfix: Rollback to v3.0.0"
```

---

## Conclusion

**Steps 0-9 Status:** ✅ COMPLETE  
**Code Quality:** ✅ 177 tests passing, 100% parity, 14.1% performance improvement  
**Production Ready:** ✅ Yes (code ready, deployment pending)  
**Step 10 Status:** ❌ BLOCKED until June 2026

**Next Immediate Actions:**
1. Tag v3.0.0 release (this week)
2. Deploy to production with `CRASHLENS_USE_UNIFIED_ENGINE=0` (default legacy)
3. Enable Prometheus metrics collection
4. Monitor for 4-8 weeks
5. Begin canary rollout (January 2026)

**Step 10 Timeline:**
- **Earliest:** June 2026 (7-8 months from now)
- **Prerequisites:** 2+ releases, <5% legacy usage, 6+ months production stability
- **Approval Required:** Engineering, Product, Support, Security sign-offs

**Safety-First Principle Upheld:** Feature flag remains until production validation confirms safe to remove. No premature deletions. Rollback capability preserved.

---

**Document Version:** 1.0  
**Last Updated:** November 8, 2025  
**Author:** CrashLens Development Team  
**Review Status:** Ready for Stakeholder Review
