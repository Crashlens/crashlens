# CrashLens Guard Command

**CI-friendly policy enforcement for LLM API logs**

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [Input Sources](#input-sources)
4. [Policy Configuration](#policy-configuration)
5. [Output Formats](#output-formats)
6. [CI/CD Integration](#cicd-integration)
7. [Privacy & Security](#privacy--security)
8. [Baseline Comparison](#baseline-comparison)
9. [Cost Control](#cost-control)
10. [Prometheus Metrics](#prometheus-metrics)
11. [Complete Examples](#complete-examples)
12. [Best Practices](#best-practices)

---

## Overview

The `guard` command is CrashLens's **policy enforcement engine** designed for CI/CD pipelines and production monitoring.

**Key Features**:
✅ **Policy Enforcement** - Evaluate logs against custom YAML rules  
✅ **CI/CD Ready** - Fail builds on violations with `--fail-on-violations`  
✅ **Privacy First** - `--strip-pii` and `--no-content` for safe sharing  
✅ **Multiple Outputs** - JSON, Markdown, HTML, or plain text reports  
✅ **Organized Storage** - Violations saved to `policy-violations/` folder  
✅ **Backwards Compatible** - Works with legacy `policy-check` command  
✅ **Prometheus Integration** - Export metrics for monitoring  

**Syntax**:
```bash
crashlens guard [LOGFILE] [OPTIONS]
```

**Quick Start**:
```bash
# Basic guard with auto-discovered rules
crashlens guard logs.jsonl

# Fail build on violations (CI/CD)
crashlens guard logs.jsonl --fail-on-violations

# Privacy-safe report
crashlens guard logs.jsonl --strip-pii --no-content
```

---

## Basic Usage

### Simple Policy Check

```bash
# Auto-discover rules from .crashlens/rules.yaml
crashlens guard logs.jsonl

# Specify rules file
crashlens guard logs.jsonl --rules policies/production.yaml

# Check multiple files
crashlens guard logs/*.jsonl --rules rules.yaml

# Check directory
crashlens guard logs/ --rules rules.yaml
```

### Dry Run (Preview Mode)

**Test policies without failing builds**:

```bash
# Show violations but don't exit with error code
crashlens guard logs.jsonl --dry-run

# Useful for testing new rules
crashlens guard logs.jsonl --rules new-rules.yaml --dry-run

# Preview with full output
crashlens guard logs.jsonl --dry-run --output json
```

### Auto-Discovery

**Guard automatically searches for rules in**:
1. `.crashlens/rules.yaml` (current directory)
2. `~/.crashlens/rules.yaml` (home directory)
3. Command-line `--rules` flag (highest priority)

```bash
# Uses .crashlens/rules.yaml if it exists
crashlens guard logs.jsonl

# Override with explicit path
crashlens guard logs.jsonl --rules custom-policy.yaml
```

---

## Input Sources

### 1. Local Files

```bash
# Single file
crashlens guard logs.jsonl

# Multiple files
crashlens guard file1.jsonl file2.jsonl file3.jsonl

# Glob patterns
crashlens guard logs/*.jsonl
```

### 2. Directory Scanning

```bash
# Scan entire directory
crashlens guard ./logs/

# Recursive scan
crashlens guard ./logs/ --rules policies/strict.yaml
```

### 3. Standard Input

```bash
# From pipe
cat logs.jsonl | crashlens guard --stdin --rules rules.yaml

# From API
curl https://api.example.com/logs | crashlens guard --stdin --rules rules.yaml
```

### Input Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `LOGFILE` | Path | Required | Path to JSONL log file or directory |
| `--stdin` | Flag | False | Read from standard input |

---

## Policy Configuration

### Rule File Structure

**Basic YAML format**:

```yaml
version: 1

rules:
  - id: RL001
    description: "Block expensive models on simple tasks"
    if:
      and:
        - input.model: "gpt-4"
        - usage.completion_tokens:
            '<': 10
    action: fail_ci
    severity: fatal
    suggestion: "Use gpt-3.5-turbo for short completions"
  
  - id: RL002
    description: "Warn on high retry counts"
    if:
      metadata.retry_count:
        '>': 3
    action: warn
    severity: error
    suggestion: "Implement exponential backoff"
```

### Rule Components

**Required fields**:
- `id`: Unique rule identifier (e.g., `RL001`)
- `description`: Human-readable explanation
- `if`: Condition block (supports AND, OR, NOT)
- `action`: `fail_ci`, `warn`, `block`
- `severity`: `fatal`, `error`, `warn`, `low`

**Condition operators**:
- Comparison: `>`, `>=`, `<`, `<=`, `==`, `!=`
- List matching: `in: [...]`
- String matching: `regex: ...`
- Boolean logic: `and: [...]`, `or: [...]`, `not: {...}`

### Policy Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--rules` | Path | Auto-discover | Path to rules YAML file |
| `-s`, `--suppress` | String | None | Suppress rule(s) by ID (repeatable) |
| `--severity` | Choice | `error` | Min severity: `warn`, `error`, `fatal` |

**Examples**:

```bash
# Explicit rules file
crashlens guard logs.jsonl --rules policies/prod.yaml

# Suppress noisy rules
crashlens guard logs.jsonl --suppress RL001 --suppress RL002

# Only fatal violations
crashlens guard logs.jsonl --severity fatal
```

---

## Output Formats

### 1. JSON Format (Default for CI/CD)

**Structured output for automation**:

```bash
crashlens guard logs.jsonl --output json
```

**Output structure**:
```json
{
  "summary": {
    "total_rules": 8,
    "violations": 3,
    "skipped_lines": 0,
    "total_cost": 2.45,
    "cost_cap": null,
    "cost_cap_exceeded": false
  },
  "rules": {
    "RL001": {
      "count": 2,
      "severity": "fatal",
      "description": "High token usage on expensive models",
      "examples": [
        {
          "timestamp": "2025-01-15T10:00:00Z",
          "model": "gpt-4",
          "tokens": 2500,
          "cost": 0.15,
          "reason": "usage.prompt_tokens=2500 (rule: >2000)"
        }
      ]
    }
  }
}
```

### 2. Markdown Format

**Human-readable reports**:

```bash
crashlens guard logs.jsonl --output md
```

**Example output**:
```markdown
# CrashLens Guard Report

- **Scanned**: `logs.jsonl`
- **Rules Checked**: 8
- **Violations Found**: 3

## Violations by Rule

### RL001: High token usage on expensive models (Fatal)
- **Count**: 2 violations
- **Severity**: Fatal
- **Examples**:
  - Trace: abc123 (gpt-4, 2500 tokens)
```

### 3. HTML Format

**Web-ready reports with styling**:

```bash
crashlens guard logs.jsonl --output html
```

Features:
- Color-coded severity indicators
- Expandable violation details
- Copy-to-clipboard functionality
- Responsive design

### 4. Text Format

**Plain text for terminal**:

```bash
crashlens guard logs.jsonl --output text
```

Simple, clean output for quick review.

### Output Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | Choice | `text` | Format: `json`, `md`, `text`, `html` |
| `--report-path` | Path | `crashlens-report.json` | Path to write report |

---

## CI/CD Integration

### Fail Build on Violations

**Critical for production pipelines**:

```bash
# Exit with code 2 if violations found
crashlens guard logs.jsonl --fail-on-violations

# Combined with severity threshold
crashlens guard logs.jsonl \
  --fail-on-violations \
  --severity fatal
```

**Exit codes**:
- `0`: No violations (or violations but not failing)
- `1`: General error (file not found, invalid rules)
- `2`: Policy violations found with `--fail-on-violations`

### GitHub Actions Example

```yaml
name: Policy Enforcement

on: [push, pull_request]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Fetch logs from Langfuse
        env:
          LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
          LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
        run: crashlens fetch-langfuse --hours-back 24 --output logs.jsonl
      
      - name: Run guard
        run: |
          crashlens guard logs.jsonl \
            --rules .crashlens/rules.yaml \
            --fail-on-violations \
            --output json \
            --report-path ci-report.json
      
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: guard-report
          path: ci-report.json
```

### GitLab CI Example

```yaml
guard:
  stage: test
  script:
    - pip install crashlens
    - crashlens guard logs.jsonl --rules .crashlens/rules.yaml --fail-on-violations
  artifacts:
    when: always
    reports:
      junit: crashlens-report.json
```

### CI/CD Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--fail-on-violations` | Flag | False | Exit with code 2 on violations |
| `--dry-run` | Flag | False | Show violations without failing |

---

## Privacy & Security

### Strip PII (Personally Identifiable Information)

**Remove sensitive data from reports**:

```bash
# Remove emails, phones, SSNs, credit cards
crashlens guard logs.jsonl --strip-pii

# Supported PII types:
# - Email addresses
# - Phone numbers
# - Social Security Numbers
# - Credit card numbers
# - IP addresses
```

**Example**:
```
Before: "Contact user@example.com for assistance"
After:  "Contact [EMAIL_REDACTED] for assistance"
```

### No Content Mode

**Exclude prompt/response text from reports**:

```bash
# Remove all log content (prompts, completions)
crashlens guard logs.jsonl --no-content

# Shows only metadata and violation counts
# Perfect for sharing with external teams
```

### Summary Only

**Hide trace IDs for internal sharing**:

```bash
# Suppress trace IDs from output
crashlens guard logs.jsonl --summary-only

# Shows aggregated stats without identifying traces
```

### Combined Privacy Options

```bash
# Maximum privacy: no PII, no content, no trace IDs
crashlens guard logs.jsonl \
  --strip-pii \
  --no-content \
  --summary-only \
  --output json
```

### Privacy Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--strip-pii` | Flag | False | Remove PII (emails, phones, SSNs) |
| `--no-content` | Flag | False | Exclude log content (prompts/responses) |
| `--summary-only` | Flag | False | Suppress trace IDs |

---

## Organized Output

### Policy Violations Folder

**All violations automatically saved to `policy-violations/` directory**:

```
policy-violations/
├── reports/
│   ├── 2025-01-15-violations.json      # Daily reports
│   ├── 2025-01-15-violations.md
│   └── 2025-01-15-violations.html
├── traces/
│   ├── RL001/                          # Organized by rule ID
│   │   ├── trace-abc123.json
│   │   └── trace-def456.json
│   └── RL002/
│       └── trace-ghi789.json
└── README.md                           # Auto-generated guide
```

### Directory Structure

**Automatic organization**:
- `reports/`: Timestamped full reports
- `traces/`: Individual violation details by rule
- `README.md`: Index of violations

**Control output location**:

```bash
# Default location
crashlens guard logs.jsonl  # → policy-violations/

# Custom report path
crashlens guard logs.jsonl --report-path ./ci-reports/violations.json

# Disable organized output (stdout only)
crashlens guard logs.jsonl --output text > report.txt
```

---

## Baseline Comparison

### Performance Regression Detection

**Compare against historical baselines**:

```bash
# Alert on 50% deviation from baseline
crashlens guard current.jsonl \
  --baseline-logs historical.jsonl \
  --baseline-deviation 0.50

# Stricter threshold (30%)
crashlens guard current.jsonl \
  --baseline-logs last-week.jsonl \
  --baseline-deviation 0.30
```

### What's Compared

**Metrics analyzed**:
- P95 latency
- P99 latency
- Average token usage
- Cost per request
- Error rates

**Example alert**:
```
⚠️  Baseline Deviation Detected

Metric: P95 Latency
Baseline: 1.2s
Current: 2.5s
Deviation: +108% (threshold: 50%)
```

### Baseline Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--baseline-logs` | Path | None | Historical logs for comparison |
| `--baseline-deviation` | Float | 0.50 | Deviation threshold (0.50 = 50%) |

---

## Cost Control

### Cost Cap Enforcement

**Fail builds if costs exceed budget**:

```bash
# Maximum $100 per batch
crashlens guard logs.jsonl \
  --cost-cap 100.0 \
  --fail-on-violations

# Combined with other checks
crashlens guard logs.jsonl \
  --cost-cap 50.0 \
  --rules policies/budget.yaml \
  --fail-on-violations
```

**Exit behavior**:
- Exits with code 2 if cost exceeds cap
- Reports total cost in summary
- Detailed cost breakdown per trace

### Cost Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--cost-cap` | Float | None | Max total cost in USD |

---

## Prometheus Metrics

### Enable Metrics Export

**Push to Prometheus Pushgateway**:

```bash
# Basic metrics push
crashlens guard logs.jsonl --push-metrics

# Custom Pushgateway
crashlens guard logs.jsonl \
  --push-metrics \
  --pushgateway-url http://prometheus:9091 \
  --metrics-job guard_production
```

### Exported Metrics

**Available in Prometheus**:

```promql
# Total guard runs
crashlens_guard_runs_total{status="success"}

# Violations by severity
crashlens_guard_violations_total{severity="fatal", rule_id="RL001"}

# Logs processed
crashlens_guard_logs_processed_total

# Rules evaluated
crashlens_guard_rules_evaluated_total{rule_id="RL001"}

# Guard execution time
crashlens_guard_duration_seconds

# Last run timestamp
crashlens_guard_last_run_timestamp
```

### Metrics Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--push-metrics` | Flag | False | Enable Prometheus metrics |
| `--pushgateway-url` | String | `http://localhost:9091` | Pushgateway URL |
| `--metrics-job` | String | `crashlens-guard` | Job name |

### Environment Variables

```bash
# Alternative to CLI flags
export CRASHLENS_PUSHGATEWAY=http://prometheus:9091
export CRASHLENS_METRICS_JOB=guard_production

crashlens guard logs.jsonl --push-metrics
```

---

## Hooks & Automation

### Annotation Hooks

**Run custom scripts after guard completes**:

```bash
# Post-process report
crashlens guard logs.jsonl \
  --annotation-hook "./scripts/process-violations.sh"

# Hook receives report path as argument
# Example hook script:
# #!/bin/bash
# REPORT=$1
# echo "Processing $REPORT"
# python analyze.py "$REPORT"
```

### Hook Use Cases

1. **Slack notifications**: Send custom alerts
2. **JIRA integration**: Create tickets for violations
3. **Data processing**: Extract metrics for dashboards
4. **Report transformation**: Convert to custom formats
5. **Alerting**: Trigger PagerDuty/OpsGenie

### Hook Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--annotation-hook` | String | None | Command to run after report |

---

## Complete Examples

### 1. Local Development

```bash
# Quick check with dry run
crashlens guard logs.jsonl --dry-run

# Check with specific rules
crashlens guard logs.jsonl --rules policies/dev.yaml

# Privacy-safe review
crashlens guard logs.jsonl --strip-pii --no-content
```

### 2. CI/CD Pipeline (Strict)

```bash
# Fail on any fatal violations
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --severity fatal \
  --fail-on-violations \
  --output json \
  --report-path ci-report.json \
  --push-metrics
```

### 3. Production Monitoring

```bash
# Full monitoring with baseline comparison
crashlens guard current.jsonl \
  --rules policies/production.yaml \
  --baseline-logs historical.jsonl \
  --baseline-deviation 0.30 \
  --cost-cap 500.0 \
  --fail-on-violations \
  --strip-pii \
  --summary-only \
  --push-metrics \
  --annotation-hook "./notify-team.sh"
```

### 4. Privacy-Safe Audit

```bash
# Maximum privacy for external review
crashlens guard logs.jsonl \
  --rules audit-rules.yaml \
  --strip-pii \
  --no-content \
  --summary-only \
  --output html \
  --report-path external-audit.html
```

### 5. Staged Rollout

```bash
# Gradually enforce new rules
crashlens guard logs.jsonl \
  --rules new-rules.yaml \
  --suppress OLD_RULE_001 \
  --suppress OLD_RULE_002 \
  --severity error \
  --dry-run \
  --output md
```

### 6. Cost Budget Gate

```bash
# Fail if daily costs exceed budget
crashlens guard daily-logs.jsonl \
  --cost-cap 100.0 \
  --fail-on-violations \
  --output json \
  --report-path budget-check.json
```

---

## Best Practices

### 1. Start with Dry Runs

```bash
# Test new rules before enforcing
crashlens guard logs.jsonl --rules new-rules.yaml --dry-run

# Review output before enabling --fail-on-violations
```

### 2. Use Severity Appropriately

**Recommended thresholds per environment**:

- **Development**: `--severity warn` (catch everything)
- **Staging**: `--severity error` (block medium issues)
- **Production**: `--severity fatal` (only critical failures)

```bash
# Development
crashlens guard logs.jsonl --severity warn

# Production
crashlens guard logs.jsonl --severity fatal --fail-on-violations
```

### 3. Gradual Rule Rollout

```bash
# Week 1: Add rule, suppress it
crashlens guard logs.jsonl --suppress NEW_RULE_001 --dry-run

# Week 2: Enable in dry-run mode
crashlens guard logs.jsonl --dry-run

# Week 3: Enable enforcement
crashlens guard logs.jsonl --fail-on-violations
```

### 4. Privacy by Default

**For any shared reports**:

```bash
crashlens guard logs.jsonl \
  --strip-pii \
  --no-content \
  --summary-only
```

### 5. CI/CD Configuration

**Always include**:
- `--fail-on-violations` (gate builds)
- `--output json` (machine-readable)
- `--push-metrics` (observability)
- `--report-path` (artifact storage)

```bash
crashlens guard logs.jsonl \
  --fail-on-violations \
  --output json \
  --report-path ci-report.json \
  --push-metrics
```

### 6. Organize Suppression

**Create suppression config**:

```yaml
# .crashlens/suppressions.yaml
suppressions:
  - RL001  # Temporary during migration
  - RL005  # Known issue, ticket #123
```

Use with:
```bash
crashlens guard logs.jsonl \
  --suppress RL001 \
  --suppress RL005
```

### 7. Baseline Updates

**Refresh baselines regularly**:

```bash
# Weekly baseline update
crashlens guard this-week.jsonl \
  --baseline-logs last-week.jsonl \
  --baseline-deviation 0.30

# Save current logs as next baseline
cp this-week.jsonl baselines/$(date +%Y-%m-%d).jsonl
```

---

## Backwards Compatibility

### Legacy `policy-check` Command

**Guard is backwards compatible with `policy-check`**:

```bash
# Old command (deprecated)
crashlens policy-check logs.jsonl --policy rules.yaml

# New command (recommended)
crashlens guard logs.jsonl --rules rules.yaml
```

**Migration path**:
1. Replace `policy-check` with `guard`
2. Rename `--policy` to `--rules`
3. All other options remain the same

### Rule Format Compatibility

**Both formats supported**:

```yaml
# Old format (still works)
match:
  model: gpt-4
  tokens: ">1000"

# New format (recommended)
if:
  and:
    - input.model: gpt-4
    - usage.prompt_tokens:
        '>': 1000
```

---

## Troubleshooting

### No Rules Found

```bash
# Error: No rules file found
crashlens guard logs.jsonl

# Solution 1: Create .crashlens/rules.yaml
mkdir .crashlens
echo 'version: 1\nrules: []' > .crashlens/rules.yaml

# Solution 2: Specify rules explicitly
crashlens guard logs.jsonl --rules my-rules.yaml
```

### Exit Code Issues

```bash
# Guard found violations but exited with 0
# → Add --fail-on-violations flag

crashlens guard logs.jsonl --fail-on-violations
```

### Missing Violations

```bash
# Check severity threshold
crashlens guard logs.jsonl --severity warn  # Show all

# Verify rule is not suppressed
crashlens guard logs.jsonl  # Remove --suppress flags
```

### Performance Issues

```bash
# For large log files, use sampling
crashlens guard large.jsonl --summary-only

# Or split into batches
split -l 10000 large.jsonl batch-
for f in batch-*; do
  crashlens guard "$f" --fail-on-violations
done
```

---

## See Also

- **[Scan Command](./scan-command.md)**: Token waste detection
- **[Report Command](./report-command.md)**: Cost digest reports  
- **[CLI Reference](../CLI_COMMAND_REFERENCE.md)**: All commands
- **[Policy Guide](../how-to-guides/guard.md)**: Policy configuration
- **[CI/CD Integration](../how-to-guides/ci-cd-integration.md)**: Pipeline setup
- **[Observability](../how-to-guides/observability.md)**: Prometheus & Grafana

---

**Quick Start**: `crashlens guard logs.jsonl --fail-on-violations --strip-pii`
