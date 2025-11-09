# Guard Implementation Internals

This document consolidates technical details about CrashLens Guard (`crashlens guard`) implementation for developers and maintainers.

---

## Overview

**Purpose**: `crashlens guard` is a lightweight, CI-friendly policy enforcement CLI tool that evaluates Langfuse JSONL logs against YAML-defined rules.

**Core Design Goals**:
- **CI enforcement layer**: Evaluate logs against organization policies before changes reach production
- **Privacy-first**: Everything runs locally, with optional PII detection/redaction
- **Deterministic automation**: Exit codes, suppression, and artifact hooks built for CI/CD runners
- **Constant-memory streaming**: Bounded memory (batch streaming, fixed-size aggregations) for multi-GB logs

---

## Implementation Files

### Core Implementation
1. **crashlens/guard.py** (458 lines)
   - Main guard command implementation
   - Rule loading and validation
   - Condition evaluation engine
   - Multiple output formatters (JSON, Markdown, Text, HTML)
   - PII redaction support
   - Severity-based exit codes

2. **.crashlens/rules.yaml** (56 lines)
   - Example rules configuration
   - 6 pre-defined rules covering common patterns
   - Documented rule structure and conditions

3. **fixtures/combined-logs.jsonl** (6 entries)
   - Test fixture with realistic log samples
   - Covers all rule condition types
   - Includes PII for testing redaction

### Testing
4. **tests/test_guard.py** (617 lines)
   - 24 comprehensive unit tests
   - 100% test coverage
   - Tests for CLI, helpers, and integration
   - All tests passing ✅

### CI/CD
5. **.github/workflows/crashlens-guard.yml** (86 lines)
   - GitHub Actions workflow
   - Automated policy checks on push/PR
   - Matrix testing across log files
   - Report generation to GitHub Summary

### Documentation
6. **docs/GUARD.md** (723 lines)
   - Complete user manual
   - Rule configuration reference
   - Usage examples and patterns
   - Integration guides
   - FAQ and troubleshooting

---

## Execution Flow

1. **Entry point**: Click command parses options, resolves log sources (file, directory, glob, stdin), locates `.crashlens/rules.yaml` unless explicit path provided

2. **Streaming ingestion**: `load_jsonl()` reads each line, warns on malformed JSON but continues (skipped count tracked globally). Large files switch to streaming mode automatically using `STREAM_THRESHOLD_BYTES` and `STREAM_BATCH_SIZE`

3. **Rule load & validation**: `load_rules()` applies strict JSON Schema (duplicate ID detection, required fields) and resolves templated environment variables via `resolve_variables_in_obj()`

4. **PII detector wiring**: `PIIDetector` instance prepared up front; if `--strip-pii` or `--no-content` is present, example payloads redacted before output

5. **Evaluation loop**: For every log record, Guard walks rule list and executes `evaluate_rule()` with boolean composition support (implicit AND, explicit AND/OR/NOT nesting). Matching entries summarized into constant-memory accumulator keyed by rule ID

6. **Baseline comparison (optional)**: When `--baseline-logs` supplied, Guard loads historical stats from `performance_baseline.py` and compares current metrics (P95/P99 latency, cost, retry rate, etc.) against configured deviation thresholds

7. **Cost cap (optional)**: If `--cost-cap` set, total `cost_usd` tallied and compared against cap; exceeding limit creates synthetic violation

8. **Suppression & severity filtering**: User-supplied `--suppress` IDs remove rules from consideration. Remaining violations filtered by `--severity` threshold

9. **Report generation**: Renderer classes (`render_text_report`, `render_markdown_report`, `render_json_report`, `render_html_report`) shape accumulator into requested format. Reports include metadata (run ID, skip counts, baseline notes)

10. **Artifact handling**: `--report-path` writes structured report to disk. `--annotation-hook` can invoke downstream tooling (e.g., GitHub Checks). Console output respects `--summary-only` for terse tables

11. **Exit logic**: If `--fail-on-violations` set and any remaining rule meets severity floor, Guard exits with code 1 (unless `--dry-run`). Otherwise exit code 0

---

## Rule System

### YAML Structure
```yaml
rules:
  - id: RL001
    description: "High token usage on expensive models"
    if:
      and:
        - if_model: "gpt-4o"
        - if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
```

**Fields**: `id`, `description`, `if`, `action`, `severity` (default `warn`)  
**Actions**: `fail_ci`, `error`, `warn` (semantic labels for humans/CI logs)  
**Severities**: `warn` < `error` < `fatal` (aligned with `--severity` threshold)

### Boolean Composition
- **Implicit AND**: Flat condition dictionaries behave as AND (`if_cost_usd_gt` + `if_model`)
- **Explicit AND/OR/NOT**:
  ```yaml
  if:
    or:
      - and:
          - if_model: "gpt-4o"
          - if_cost_usd_gt: 0.50
      - if_retry_count_gt: 3
  ```
- **Unlimited nesting**: Guard walks nested dictionaries recursively, short-circuiting once branch decides outcome
- **Backwards compatible**: Older rules without boolean operators continue to work

### Supported Condition Keys

| Key | Type | Description |
| --- | ---- | ----------- |
| `if_model` | string | Exact model match |
| `if_tokens_gt` | int | Prompt tokens greater than threshold |
| `if_retry_count_gt` | int | Retry count exceeds limit |
| `if_fallback_triggered` | bool | Fallback storm detected |
| `if_prompt_contains_pii` | bool | Uses `PIIDetector` regexes |
| `if_cost_usd_gt` | float | Per-request cost guardrail |
| `if_response_time_gt` | float | Slow latency detection |
| `if_error_rate_gt` | float | Percent error threshold |

Custom keys can be added in future releases without changing boolean layer.

---

## Privacy Controls

### Detection
- `PIIDetector` scans prompts/responses using email, phone, SSN, and credit card regexes
- Rule RL004 in default template uses this signal

### Redaction
- `--strip-pii`: Replaces detected fragments with placeholders (e.g., `alice@example.com` → `[REDACTED_EMAIL]`)
- `--no-content`: Omits prompt/response text entirely, keeping only metadata columns (timestamp, model, tokens)

### Report Hygiene
- Console output and written artifacts note when content was redacted
- Reviewers know why data is missing

---

## Baseline & Cost Controls

### Baseline Comparison
- `--baseline-logs`: Points to historical JSONL file
- Metrics (latency percentiles, cost, retries) compared using `compare_to_baseline()`
- Violations get synthetic IDs `baseline_<metric>`
- `--baseline-deviation`: Tunes drift tolerance (e.g., `0.75` = 75% over baseline triggers)

### Cost Cap Enforcement
- `--cost-cap 50.0`: Fails when aggregate `cost_usd` crosses cap
- Catches runaway spend

---

## CLI Options Reference

| Flag | Purpose |
| --- | ------- |
| `--output [text\|md\|json\|html]` | Choose renderer. HTML excellent for CI artifacts |
| `--report-path PATH` | Persist report on disk (default `crashlens-report.json`) |
| `--fail-on-violations` | Exit 1 when severity threshold met |
| `--dry-run` | Always exit 0 (combine with `--summary-only` for safe experimentation) |
| `--summary-only` | Print `Rule ID \| Violations \| Severity` table |
| `--suppress RL003` | Suppress specific rule IDs (repeatable) |
| `--annotation-hook "python scripts/annotate.py"` | Post-process generated report |

---

## Output Formats

- **Text**: Fixed-width banners, great for console logs
- **Markdown**: Headings, lists, tables for PR comments or wikis
- **JSON**: Machine-readable summary + per-rule breakdown, suited for dashboards and custom tooling
- **HTML**: Fully styled dashboard with severity indicators—ideal for CI artifact viewers

All formats include metadata: `run_id`, skipped line count, execution duration, optional baseline notes

---

## Example Workflows

### 1. CI Gate (fail on error+)
```bash
python -m crashlens.cli guard logs/production.jsonl \
  --rules .crashlens/rules.yaml \
  --fail-on-violations \
  --severity error \
  --output md \
  --report-path guard.md
```

### 2. Dry-run During Rule Tuning
```bash
python -m crashlens.cli guard sample-logs/demo-logs.jsonl \
  --rules .crashlens/rules.yaml \
  --dry-run \
  --summary-only
```

### 3. Privacy-safe Artifact
```bash
python -m crashlens.cli guard sample-logs/demo-logs.jsonl \
  --rules .crashlens/rules.yaml \
  --output html \
  --strip-pii \
  --no-content \
  --report-path guard-sanitized.html
```

### 4. Baseline Comparison
```bash
python -m crashlens.cli guard sample-logs/demo-logs.jsonl \
  --rules .crashlens/rules.yaml \
  --baseline-logs sample-logs/compliant_logs.jsonl \
  --baseline-deviation 0.50 \
  --output text
```

---

## Integration Best Practices

1. **Pin rule IDs**: Reference rule IDs in dashboards, annotations, suppression files so teams know exactly what failed

2. **Promote gradually**: Start rules at `warn`, then promote to `error` or `fatal` once false positives eliminated

3. **Combine with `scan`**: Use detector output (retry loops, fallback storms) to inform new guard rules for recurring issues

4. **Archive artifacts**: Upload HTML/JSON reports as CI artifacts for auditing; they contain run metadata (`run_id`, timestamp, git hash)

5. **Monitor drifts**: Pair `--baseline-logs` with scheduled job to detect regressions in latency or cost trends before SLAs breached

---

## Troubleshooting

### "No such command 'guard'"
**Solution**: Ensure running workspace version (`python -m crashlens.cli guard ...`) or reinstall package in editable mode

### Schema Errors on Startup
**Solution**: Loader prints precise `jsonschema` validation errors when `.crashlens/rules.yaml` is malformed

### Large File Performance
**Solution**: Adjust `CRASHLENS_STREAM_THRESHOLD` and `CRASHLENS_STREAM_BATCH_SIZE` environment variables for different streaming cutoffs

### False PII Positives
**Solution**: Provide custom `PIIDetector` implementation or narrow regexes (future releases will expose plug-in hooks)

---

## Integration with Existing Codebase

### CLI Integration
- Added to main `crashlens/cli.py`
- Follows existing Click command patterns
- Uses same error handling conventions
- Consistent with project style guide

### Testing Standards
- Uses pytest framework (existing pattern)
- CliRunner for CLI testing (existing pattern)
- Type hints on all functions (existing standard)
- Comprehensive docstrings

### Documentation Standards
- Follows existing Markdown format
- Includes code examples with syntax highlighting
- Provides quick reference tables
- Cross-references other documentation

---

## File Locations

- **Command implementation**: `crashlens/guard.py`
- **Default rules template**: `.crashlens/rules.yaml`
- **Baseline helpers**: `crashlens/performance_baseline.py`
- **CLI documentation**: `docs/GUARD.md`
- **Test suite**: `tests/test_guard.py`
- **Example reports**: `guard-report.json`, `guard-baseline.html`, `guard-md.json`

---

*Consolidated from: GUARD_IMPLEMENTATION_SUMMARY.md, GUARD_FUNCTIONALITY.md*  
*Last updated: 2025-11-09*
