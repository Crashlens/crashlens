# CrashLens Guard Functionality Deep Dive

## 1. Purpose and Design Goals
- **CI enforcement layer:** `crashlens guard` evaluates Langfuse-style JSONL logs against organization policies before changes reach production.
- **Privacy-first:** Everything runs locally, with optional PII detection/redaction so reports are safe to archive or share.
- **Deterministic automation:** Exit codes, suppression, and artifact hooks are built for GitHub Actions, Jenkins, and other CI/CD runners.
- **Constant-memory streaming:** The engine keeps memory bounded (batch streaming, fixed-size aggregations) so multi-GB logs can be processed safely.

## 2. Execution Flow
1. **Entry point:** The Click command parses options, resolves the log sources (file, directory, glob, or stdin), and locates `.crashlens/rules.yaml` unless an explicit path is passed.
2. **Streaming ingestion:** `load_jsonl()` reads each line, warning on malformed JSON but continuing (skipped count tracked globally). Large files switch to streaming mode automatically using `STREAM_THRESHOLD_BYTES` and `STREAM_BATCH_SIZE`.
3. **Rule load & validation:** `load_rules()` applies a strict JSON Schema (duplicate ID detection, required fields) and resolves templated environment variables via `resolve_variables_in_obj()`.
4. **PII detector wiring:** A `PIIDetector` instance is prepared up front; if `--strip-pii` or `--no-content` is present, example payloads are redacted before output.
5. **Evaluation loop:** For every log record, Guard walks the rule list and executes `evaluate_rule()` with boolean composition support (implicit AND, explicit AND/OR/NOT nesting). Matching entries are summarized into a constant-memory accumulator keyed by rule ID.
6. **Baseline comparison (optional):** When `--baseline-logs` is supplied, Guard loads historical stats from `performance_baseline.py` and compares current metrics (P95/P99 latency, cost, retry rate, etc.) against configured deviation thresholds.
7. **Cost cap (optional):** If `--cost-cap` is set, total `cost_usd` is tallied and compared against the cap; exceeding the limit creates a synthetic violation.
8. **Suppression & severity filtering:** User-supplied `--suppress` IDs remove rules from consideration. Remaining violations are filtered by the `--severity` threshold.
9. **Report generation:** Renderer classes (`render_text_report`, `render_markdown_report`, `render_json_report`, `render_html_report`) shape the accumulator into the requested format. Reports include metadata (run ID, skip counts, baseline notes).
10. **Artifact handling:** `--report-path` writes the structured report to disk. `--annotation-hook` can invoke downstream tooling (e.g., GitHub Checks). Console output respects `--summary-only` for terse tables.
11. **Exit logic:** If `--fail-on-violations` is set and any remaining rule meets the severity floor, Guard exits with code 1 (unless `--dry-run`). Otherwise exit code 0.

## 3. Rule System
### 3.1 YAML Structure
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
- **Fields:** `id`, `description`, `if`, `action`, `severity` (default `warn`).
- **Actions:** `fail_ci`, `error`, `warn` (semantic labels for humans/CI logs).
- **Severities:** `warn` < `error` < `fatal`. Aligned with the `--severity` threshold.

### 3.2 Boolean Composition
- **Implicit AND:** Flat condition dictionaries behave as an AND (`if_cost_usd_gt` + `if_model`).
- **Explicit AND/OR/NOT:**
  ```yaml
  if:
    or:
      - and:
          - if_model: "gpt-4o"
          - if_cost_usd_gt: 0.50
      - if_retry_count_gt: 3
  ```
- **Unlimited nesting:** Guard walks nested dictionaries recursively, short-circuiting once a branch decides the outcome.
- **Backwards compatible:** Older rules without boolean operators continue to work.

### 3.3 Supported Condition Keys (highlights)
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

Custom keys can be added in future releases without changing the boolean layer.

## 4. Privacy Controls
- **Detection:** `PIIDetector` scans prompts/responses using email, phone, SSN, and credit card regexes. Rule RL004 in the default template uses this signal.
- **Redaction:**
  - `--strip-pii` replaces detected fragments with placeholders (e.g., `alice@example.com` → `[REDACTED_EMAIL]`).
  - `--no-content` omits prompt/response text entirely, keeping only metadata columns (timestamp, model, tokens) in the report.
- **Report hygiene:** Console output and written artifacts note when content was redacted so reviewers know why data is missing.

## 5. Baseline & Cost Controls
- **Baseline comparison:**
  - `--baseline-logs` points to a historical JSONL file.
  - Metrics (latency percentiles, cost, retries) are compared using `compare_to_baseline()`; violations get synthetic IDs `baseline_<metric>`.
  - `--baseline-deviation` tunes how much drift is tolerated (e.g., `0.75` means 75% over baseline triggers).
- **Cost cap enforcement:** `--cost-cap 50.0` fails when aggregate `cost_usd` crosses the cap, catching runaway spend.

## 6. CLI Options (excerpt)
| Flag | Purpose |
| --- | ------- |
| `--output [text|md|json|html]` | Choose renderer. HTML is excellent for CI artifacts. |
| `--report-path PATH` | Persist report on disk (default `crashlens-report.json`). |
| `--fail-on-violations` | Exit 1 when severity threshold is met. |
| `--dry-run` | Always exit 0 (combine with `--summary-only` for safe experimentation). |
| `--summary-only` | Print `Rule ID | Violations | Severity` table. |
| `--suppress RL003` | Suppress specific rule IDs (repeatable). |
| `--annotation-hook "python scripts/annotate.py"` | Post-process the generated report. |

## 7. Output Formats
- **Text:** Fixed-width banners, great for console logs.
- **Markdown:** Headings, lists, and tables for pull-request comments or wikis.
- **JSON:** Machine-readable summary + per-rule breakdown, suited for dashboards and custom tooling.
- **HTML:** Fully styled dashboard with severity indicators—ideal for CI artifact viewers.
- All formats include metadata (`run_id`, skipped line count, execution duration, optional baseline notes).

## 8. Example Workflows
1. **CI Gate (fail on error+):**
   ```bash
   python -m crashlens.cli guard logs/production.jsonl \
     --rules .crashlens/rules.yaml \
     --fail-on-violations \
     --severity error \
     --output md \
     --report-path guard.md
   ```
2. **Dry-run during rule tuning:**
   ```bash
   python -m crashlens.cli guard sample-logs/demo-logs.jsonl \
     --rules .crashlens/rules.yaml \
     --dry-run \
     --summary-only
   ```
3. **Privacy-safe artifact:**
   ```bash
   python -m crashlens.cli guard sample-logs/demo-logs.jsonl \
     --rules .crashlens/rules.yaml \
     --output html \
     --strip-pii \
     --no-content \
     --report-path guard-sanitized.html
   ```
4. **Baseline comparison:**
   ```bash
   python -m crashlens.cli guard sample-logs/demo-logs.jsonl \
     --rules .crashlens/rules.yaml \
     --baseline-logs sample-logs/compliant_logs.jsonl \
     --baseline-deviation 0.50 \
     --output text
   ```

## 9. Integration Best Practices
- **Pin rules IDs:** Reference rule IDs in dashboards, annotations, and suppression files so teams know exactly what failed.
- **Promote gradually:** Start rules at `warn`, then promote to `error` or `fatal` once false positives are eliminated.
- **Combine with `scan`:** Use detector output (retry loops, fallback storms) to inform new guard rules for recurring issues.
- **Archive artifacts:** Upload HTML/JSON reports as CI artifacts for auditing; they contain run metadata (`run_id`, timestamp, git hash).
- **Monitor drifts:** Pair `--baseline-logs` with a scheduled job to detect regressions in latency or cost trends before SLAs are breached.

## 10. Troubleshooting
- **"No such command 'guard'":** Ensure you are running the workspace version (`python -m crashlens.cli guard ...`) or reinstall the package in editable mode.
- **Schema errors on startup:** The loader prints precise `jsonschema` validation errors when `.crashlens/rules.yaml` is malformed.
- **Large file performance:** Adjust `CRASHLENS_STREAM_THRESHOLD` and `CRASHLENS_STREAM_BATCH_SIZE` environment variables if you need different streaming cutoffs.
- **False PII positives:** Provide a custom `PIIDetector` implementation or narrow regexes (future releases will expose plug-in hooks).

## 11. File Locations & References
- Command implementation: `crashlens/guard.py`
- Default rules template: `.crashlens/rules.yaml`
- Baseline helpers: `crashlens/performance_baseline.py`
- CLI documentation: `docs/GUARD.md`
- Example reports (generated via demo runs): `guard-report.json`, `guard-baseline.html`, `guard-md.json`

*Last updated: 2025-11-08*
