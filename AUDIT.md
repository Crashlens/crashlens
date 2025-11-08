# CrashLens Guard vs. Policy-Check Audit and Unification Plan

This document provides a complete audit of the `crashlens guard` and `crashlens policy-check` commands, outlining their implementation, overlaps, and a strategic plan to merge them into a single, unified policy enforcement engine.

## 1. File Map

| File | Key Classes/Functions | Purpose |
| --- | --- | --- |
| `crashlens/cli.py` | `policy_check()` | Defines and implements the `policy-check` command. |
| `crashlens/guard.py` | `guard()`, `Rule`, `PIIDetector` | Defines and implements the `guard` command, its rule structure, and PII detection. |
| `crashlens/policy/engine.py` | `PolicyEngine`, `PolicyRule`, `PolicyMatcher` | Core rule evaluation logic for `policy-check`. |
| `crashlens/parsers/langfuse.py`| `LangfuseParser` | Parses and validates Langfuse-style JSONL logs for `policy-check`. |
| `.crashlens/rules.yaml` | - | Default rule configuration file for `crashlens guard`. |
| `docs/GUARD.md` | - | Documentation for the `guard` command. |
| `docs/COMMAND-REFERENCE.md`| - | General command reference including `policy-check`. |

## 2. CLI Surface

### `crashlens guard`
- `logfile`: Path to log file(s) (file, directory, glob, or stdin).
- `--rules`: Path to `rules.yaml`.
- `--suppress`: Rule IDs to suppress.
- `--severity`: Minimum severity to fail on (`warn`, `error`, `fatal`).
- `--output`: Output format (`json`, `md`, `text`, `html`).
- `--no-content`: Redact content from report.
- `--strip-pii`: Strip PII from examples.
- `--fail-on-violations`: Exit with code 1 on violations.
- `--dry-run`: Always exit with code 0.
- `--summary-only`: Condensed one-line summary output.
- `--baseline-logs`: Path to historical logs for baseline comparison.
- `--baseline-deviation`: Deviation threshold for baseline alerts.
- `--cost-cap`: Maximum total cost in USD.
- `--report-path`: Path to write structured JSON report.
- `--annotation-hook`: Command to run after report is written.

### `crashlens policy-check`
- `logfile`: Path to the log file.
- `--policy-template`: Use a built-in policy template.
- `--policy-file`: Use a custom policy file.
- `--fail-on-violations`: Exit with error code if violations are found.
- `--severity-threshold`: Minimum severity to report (`low`, `medium`, `high`, `critical`).
- `--out-report`: Output path for the markdown report.
- `--detailed`: Generate a detailed JSON report.
- `--out-detailed`: Output path for the detailed JSON report.
- `--out-dir`: Output directory for both reports.
- `--force`: Overwrite existing files.
- `--quiet`: Print only a summary line.
- `--no-content`: Exclude content from reports.
- `--strip-pii`: Remove PII from reports.

## 3. Duplication & Divergence Analysis

- **Rule Engine**: `guard` uses a simple, hardcoded evaluator (`guard.py::evaluate_condition`), while `policy-check` uses the more powerful `PolicyEngine` with support for operators, dot notation, and better structure.
- **Log Parsing**: `guard` uses a basic `json.loads` loop and a streaming reader, whereas `policy-check` uses `LangfuseParser`, which includes schema validation and normalization.
- **Reporting**: The two commands use entirely separate sets of formatters (`format_*_report` functions in `guard.py` vs. `PolicyReportMarkdown`/`PolicyReportJSON` classes for `policy-check`).
- **Features**: `guard` has unique features like baseline comparison, cost caps, and annotation hooks, which are absent in `policy-check`. `policy-check` can use policy templates, which `guard` cannot.

## 4. Risk Register

| Risk | Mitigation |
| --- | --- |
| **Behavioral Drift** | Implement a feature flag (`--use-legacy-engine`) for the first few releases to allow users to revert to the old `guard` behavior if needed. |
| **Backward Compatibility** | Create a translation layer that converts old `rules.yaml` format to the `PolicyEngine` format on the fly. |
| **Performance Regression** | Benchmark the new unified engine against the old `guard` on large files to ensure performance does not degrade. |
| **User Confusion** | Clearly document the merge in the changelog and update all relevant documentation (`GUARD.md`, `COMMAND-REFERENCE.md`). |
| **Increased Complexity** | Encapsulate the unified logic within the `PolicyEngine` and keep the CLI surface clean. |
| **Incomplete Feature Merge**| Create a checklist of all features from both commands and ensure they are all present in the unified command. |
| **Testing Gaps** | Add comprehensive integration tests that cover all merged features, including baseline checks, cost caps, and policy templates. |
| **Silent Failures** | Add robust logging and validation to the new unified engine to catch any issues during the transition. |

## 5. Migration Plan

1.  **[SMALL] Introduce a translation layer** in `guard.py` that converts the simple `rules.yaml` format into the `PolicyEngine` rule structure.
2.  **[MEDIUM] Refactor `guard` to use `PolicyEngine`** for its core evaluation, passing the translated rules to it. Initially, bypass `LangfuseParser`.
3.  **[MEDIUM] Integrate `LangfuseParser` into `guard`**, but make it optional via a flag (`--no-schema-validation`) to maintain backward compatibility for logs that are not Langfuse-compliant.
4.  **[LARGE] Merge `guard`-specific features** (baseline checks, cost caps, annotation hooks) into the `PolicyEngine` or as post-processing steps that consume the `PolicyEngine`'s output.
5.  **[MEDIUM] Unify the reporting formatters**. Have `guard` use the same `PolicyReport*` classes as `policy-check`, adding `text` and `html` output options to them.
6.  **[SMALL] Deprecate `policy-check`**. Change the `policy-check` command in `cli.py` to be a simple alias for `guard` with default options that mimic the old behavior (e.g., default to markdown report). Print a deprecation warning.
7.  **[SMALL] Update all documentation** (`GUARD.md`, `COMMAND-REFERENCE.md`, etc.) to reflect the unified `guard` command and the deprecation of `policy-check`.
8.  **[MEDIUM] Remove the old `policy-check` logic** and the old `guard` evaluation logic in a future release after the deprecation period.

## 6. Summary Markdown

The `crashlens guard` and `crashlens policy-check` commands are redundant. They use separate rule engines, parsers, and reporters, leading to duplicated effort and feature divergence. `guard` has superior features like baseline checks and cost caps, while `policy-check` has a more powerful rule engine. The recommended plan is to merge `policy-check`'s engine into `guard`, create a compatibility layer for old `guard` rules, and deprecate `policy-check`. This will unify the user experience, reduce maintenance, and create a single, powerful policy enforcement tool.

## 7. Implementation Progress

### ✅ Step 0: Preflight Checks (Commit 000)
- **Status**: Complete
- **Files**: `crashlens/utils/feature_flags.py`, `tests/test_preflight_repo.py`, `docs/migration_teardown.md`
- **Tests**: 7/7 passing
- **Summary**: Feature flag system, repository validation, safety procedures

### ✅ Step 1: Rule Translator (Commit 001)
- **Status**: Complete
- **Files**: `crashlens/utils/rule_translator.py`, `tests/test_rule_translator.py`, `tests/fixtures/sample-policy.yaml`
- **Tests**: 15/15 passing
- **Summary**: Translates policy-check YAML to guard-compatible JSON rules

### ✅ Step 2: Shared Ingestion Layer (Commit 002)
- **Status**: Complete
- **Files**: `crashlens/io/ingest.py`, `tests/test_ingest_streaming.py`, `tests/test_ingest_langfuse_fallback.py`
- **Tests**: 30/30 passing
- **Summary**: Unified log iterator with streaming support, optional Langfuse validation
- **Documentation**: `docs/STEP_2_INGESTION_SUMMARY.md`

### ⏳ Step 3: Integrate PolicyEngine into Guard
- **Status**: Pending
- **Planned Changes**:
  - Replace guard's direct JSON loading with LogIterator
  - Add feature flag: `CRASHLENS_USE_UNIFIED_ENGINE=true`
  - Integrate PolicyEngine for rule evaluation
  - Maintain backwards compatibility
  - Add parity tests

### ⏳ Step 4: Merge Detectors
- **Status**: Pending
- **Planned Changes**:
  - Pass detector results through PolicyEngine
  - Unified violation format
  - Combined reporting

### ⏳ Step 5: Deprecate policy-check
- **Status**: Pending
- **Planned Changes**:
  - Make policy-check alias to guard
  - Add deprecation warnings
  - Update documentation

### ⏳ Step 6: Remove Old Code
- **Status**: Pending
- **Planned Changes**:
  - Remove legacy guard evaluation logic
  - Remove old policy-check command
  - Clean up duplicate code
