# CrashLens Guard - CI-Friendly Policy Enforcement

## Overview

`crashlens guard` is a lightweight, CI-friendly policy enforcement tool that evaluates JSONL logs against custom rules defined in YAML. It's designed for continuous integration pipelines to catch policy violations before they reach production.

## Quick Start

```bash
# Basic usage
crashlens guard logs.jsonl --rules .crashlens/rules.yaml

# CI mode with failing on violations
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --fail-on-violations \
  --severity error

# Generate JSON report
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --output json > report.json

# Privacy-safe reporting
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --no-content \
  --strip-pii
```

## Features

- **Rule-based evaluation**: Define custom rules in YAML with flexible conditions
- **Multiple output formats**: JSON, Markdown, or plain text
- **Privacy controls**: Strip PII, redact content
- **Suppression support**: Selectively disable rules
- **Severity thresholds**: Control when to fail based on violation severity
- **CI integration**: Exit codes designed for CI/CD pipelines
- **Zero network calls**: Runs 100% locally

## Rule Configuration

### Rules File Structure

Create a `.crashlens/rules.yaml` file in your project:

```yaml
rules:
  - id: RL001
    description: "High token usage on expensive models"
    if:
      if_model: "gpt-4o"
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal

  - id: RL002
    description: "Excessive retry attempts"
    if:
      if_retry_count_gt: 2
    action: error
    severity: error

  - id: RL003
    description: "Fallback mechanism triggered"
    if:
      if_fallback_triggered: true
    action: warn
    severity: warn

  - id: RL004
    description: "PII detected in prompts"
    if:
      if_prompt_contains_pii: true
    action: error
    severity: error

  - id: RL005
    description: "High cost per request"
    if:
      if_cost_usd_gt: 0.50
    action: fail_ci
    severity: fatal
```

### Supported Conditions

All conditions within a rule are AND-ed together by default. A log entry must match ALL conditions to trigger the rule.

| Condition | Type | Description | Example |
|-----------|------|-------------|---------|
| `if_model` | string | Exact model name match | `if_model: "gpt-4o"` |
| `if_tokens_gt` | integer | Token count greater than threshold | `if_tokens_gt: 2000` |
| `if_retry_count_gt` | integer | Retry count greater than threshold | `if_retry_count_gt: 2` |
| `if_fallback_triggered` | boolean | Fallback was triggered | `if_fallback_triggered: true` |
| `if_prompt_contains_pii` | boolean | PII detected in prompt (email/phone) | `if_prompt_contains_pii: true` |
| `if_cost_usd_gt` | float | Cost (USD) greater than threshold | `if_cost_usd_gt: 0.50` |
| `if_response_time_gt` | float | Response time (ms) greater than threshold | `if_response_time_gt: 5000` |
| `if_error_rate_gt` | float | Error rate (%) greater than threshold | `if_error_rate_gt: 10.0` |

### Boolean Composition (AND/OR/NOT)

Rules support boolean composition for complex logic:

#### OR Composition

Match when **any** condition is true:

```yaml
rules:
  - id: RL010
    description: "Expensive models (gpt-4o or claude-3)"
    if:
      or:
        - if_model: "gpt-4o"
        - if_model: "claude-3"
    action: warn
    severity: warn
```

#### NOT Composition

Negate a condition (match when condition is **false**):

```yaml
rules:
  - id: RL011
    description: "Non-cheap models"
    if:
      not:
        if_model: "gpt-3.5-turbo"
    action: warn
    severity: warn
```

#### AND Composition (Explicit)

Match when **all** conditions are true (default behavior, but can be explicit):

```yaml
rules:
  - id: RL012
    description: "Expensive model with high tokens"
    if:
      and:
        - if_model: "gpt-4o"
        - if_tokens_gt: 2000
    action: error
    severity: error
```

#### Nested Composition

Combine boolean operators for complex rules:

```yaml
rules:
  - id: RL013
    description: "High cost from expensive models OR excessive retries"
    if:
      or:
        - and:
            - if_model: "gpt-4o"
            - if_cost_usd_gt: 0.50
        - if_retry_count_gt: 3
    action: fail_ci
    severity: fatal

  - id: RL014
    description: "Cheap model WITHOUT fallback"
    if:
      and:
        - if_model: "gpt-3.5-turbo"
        - not:
            if_fallback_triggered: true
    action: warn
    severity: warn

  - id: RL015
    description: "PII in expensive models (either gpt-4o or claude-3)"
    if:
      and:
        - if_prompt_contains_pii: true
        - or:
            - if_model: "gpt-4o"
            - if_model: "claude-3"
    action: error
    severity: error
```

**Key Points**:
- `and`: List of conditions (all must be true)
- `or`: List of conditions (at least one must be true)
- `not`: Single condition (negates result)
- Nesting is unlimited - combine operators as needed
- Backward compatible: flat dictionaries still use implicit AND

### Actions

Actions determine the intended response to a violation:

- `fail_ci`: Intended for CI pipeline failures
- `error`: Serious violation requiring attention
- `warn`: Advisory notice, non-blocking

### Severities

Severities work with the `--severity` threshold to control exit behavior:

- `fatal` (rank 3): Critical violations
- `error` (rank 2): Standard violations
- `warn` (rank 1): Low-priority violations

## Log Format

Guard expects JSONL files where each line is a JSON object with these fields:

```json
{
  "timestamp": "2025-10-24T10:00:00Z",
  "model": "gpt-4o",
  "tokens": 2500,
  "retry_count": 0,
  "fallback_triggered": false,
  "prompt": "User query text",
  "cost_usd": 0.25,
  "endpoint": "/api/generate"
}
```

**Required fields**: None (all conditions will simply not match if fields are missing)

**Optional fields**: All fields are optional, but rules will only trigger when relevant fields exist

## Command Options

```bash
crashlens guard LOGFILE --rules RULES_FILE [OPTIONS]
```

### Arguments

- `LOGFILE`: Path to JSONL log file to analyze

### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--rules` | path | (required) | Path to rules YAML file |
| `--suppress`, `-s` | string | - | Rule ID to suppress (repeatable) |
| `--severity` | choice | `error` | Minimum severity threshold: `warn`, `error`, `fatal` |
| `--output` | choice | `text` | Output format: `json`, `md`, `text`, `html` |
| `--no-content` | flag | false | Redact examples from report (privacy mode) |
| `--strip-pii` | flag | false | Remove emails/phones from example prompts |
| `--fail-on-violations` | flag | false | Exit 1 when violations meet severity threshold |
| `--dry-run` | flag | false | Validate rules without failing CI (exit code always 0) |
| `--summary-only` | flag | false | Output condensed one-line-per-rule summary |

### Exit Codes

- `0`: No violations detected OR violations below severity threshold OR `--dry-run` enabled
- `1`: Violations detected that meet/exceed severity threshold (only with `--fail-on-violations` and not `--dry-run`)

## Usage Examples

### Example 1: Dry-Run Mode (Validate Without Failing)

Useful for testing rules without blocking CI:

```bash
# Test rules without failing
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --fail-on-violations \
  --dry-run

# Output shows violations but exit code is always 0
# stderr: 🔍 Guard (dry-run): Violations found but not failing CI
```

### Example 2: Summary-Only Mode (Condensed Output)

Get a quick overview of violations:

```bash
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --summary-only

# Output:
# Rule ID | Violations | Severity
# ----------------------------------------
# RL001         | 5          | fatal
# RL003         | 12         | warn
```

### Example 3: Combined Flags

```bash
# Dry-run with summary for quick validation
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --fail-on-violations \
  --dry-run \
  --summary-only
```

### Example 4: CI Pipeline Integration

```yaml
# .github/workflows/guard-check.yml
name: Policy Check
on: [push, pull_request]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Run Guard
        run: |
          crashlens guard logs/production.jsonl \
            --rules .crashlens/rules.yaml \
            --fail-on-violations \
            --severity error \
            --output md > guard-report.md
      
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: guard-report
          path: guard-report.md
```

### Example 2: Local Development

```bash
# Quick check during development
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --output text

# Detailed investigation
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --output json | jq '.rules[] | select(.count > 0)'
```

### Example 3: Privacy-Safe Sharing

```bash
# Generate report safe for sharing internally
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --no-content \
  --strip-pii \
  --output md > sanitized-report.md
```

### Example 4: Selective Rule Testing

```bash
# Test only high-severity rules
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --suppress RL003 \
  --suppress RL006 \
  --severity fatal \
  --fail-on-violations
```

### Example 5: Multi-File Analysis

```bash
# Analyze multiple log files
for logfile in logs/*.jsonl; do
  echo "Analyzing $logfile"
  crashlens guard "$logfile" \
    --rules .crashlens/rules.yaml \
    --output text
done
```

## Output Formats

### JSON Format

Structured output suitable for programmatic processing:

```json
{
  "summary": {
    "total_rules": 5,
    "violations": 2
  },
  "rules": {
    "RL001": {
      "count": 1,
      "severity": "fatal",
      "description": "High token usage on expensive models",
      "examples": [
        {
          "timestamp": "2025-10-24T10:00:00Z",
          "model": "gpt-4o",
          "tokens": 2500,
          "retry_count": 0,
          "fallback_triggered": false,
          "endpoint": "/api/generate",
          "prompt": "User query..."
        }
      ]
    }
  }
}
```

### Markdown Format

Human-readable report with formatting:

```markdown
# CrashLens Guard Report

- **Scanned**: `logs.jsonl`
- **Rules Checked**: 5
- **Violations Found**: 2

## Violations by Rule

### RL001 — `fatal` severity

**Description**: High token usage on expensive models

**Violation Count**: 1

**Example Violations**:

1. **Timestamp**: 2025-10-24T10:00:00Z
   - **Model**: `gpt-4o`
   - **Tokens**: 2500
   ...
```

### Text Format

Plain text for terminal output:

```
============================================================
CrashLens Guard Report
============================================================
Scanned: logs.jsonl
Rules Checked: 5
Violations Found: 2
============================================================

Rule: RL001 [FATAL]
Description: High token usage on expensive models
Violation Count: 1
Examples:
  - 2025-10-24T10:00:00Z | gpt-4o | tokens=2500 | prompt=User query...
------------------------------------------------------------
```

## Best Practices

### 1. Start with Warnings

Begin with `severity: warn` for new rules to understand baseline behavior before enforcing:

```yaml
rules:
  - id: RL_NEW_001
    description: "Experimental rule - monitoring only"
    if:
      if_tokens_gt: 5000
    action: warn
    severity: warn
```

### 2. Use Suppressions During Migration

When introducing guard to an existing project, suppress rules temporarily:

```bash
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --suppress RL001 \
  --suppress RL002
```

### 3. Separate Rules by Environment

Maintain different rule sets for different environments:

```bash
# Development - lenient
crashlens guard logs.jsonl --rules .crashlens/rules-dev.yaml

# Production - strict
crashlens guard logs.jsonl --rules .crashlens/rules-prod.yaml
```

### 4. Combine Conditions for Precision

Avoid false positives by combining multiple conditions:

```yaml
rules:
  - id: RL_COMBINED
    description: "Expensive model + high tokens + retries"
    if:
      if_model: "gpt-4o"
      if_tokens_gt: 2000
      if_retry_count_gt: 1
    action: fail_ci
    severity: fatal
```

### 5. Document Rule Intent

Always include clear descriptions explaining why a rule exists:

```yaml
rules:
  - id: RL_BUDGET
    description: |
      Cost control: Prevent individual requests exceeding $1.00.
      Budget impact: High-cost requests can drain monthly allocation.
      Action: Investigate prompt optimization or model selection.
    if:
      if_cost_usd_gt: 1.00
    action: fail_ci
    severity: fatal
```

## Troubleshooting

### Issue: Rules not triggering

**Solution**: Verify log format matches expected fields

```bash
# Check first line of log
head -n 1 logs.jsonl | jq .

# Verify fields exist
jq 'select(.tokens > 0)' logs.jsonl | head -n 1
```

### Issue: False positives

**Solution**: Refine conditions or adjust thresholds

```yaml
# Before (too aggressive)
if:
  if_tokens_gt: 100

# After (more reasonable)
if:
  if_tokens_gt: 1000
  if_model: "gpt-4o"  # Only for expensive models
```

### Issue: Missing violations in report

**Solution**: Check suppression and severity settings

```bash
# List all violations (no filtering)
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --severity warn \
  --output json
```

### Issue: CI failing unexpectedly

**Solution**: Review severity threshold and rule severities

```bash
# Local test with same settings
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --fail-on-violations \
  --severity error
```

## Performance Thresholds

CrashLens Guard can automatically enforce performance thresholds to fail CI if logs show degraded performance. Thresholds are configured via environment variables and work independently of rule-based violations.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SLOW_RESPONSE_THRESHOLD_MS` | 3000 | Maximum acceptable response time in milliseconds |
| `EXPENSIVE_REQUEST_THRESHOLD` | 0.05 | Maximum acceptable cost in USD per request |
| `ERROR_RATE_THRESHOLD` | 0.20 | Maximum acceptable error rate (0.0-1.0, e.g., 0.20 = 20%) |

### How It Works

1. Guard evaluates all log entries against your rules
2. Simultaneously calculates performance metrics:
   - **Max Latency**: Highest `response_time_ms` value across all logs
   - **Max Cost**: Highest `cost_usd` value across all logs
   - **Error Rate**: Percentage of logs with `error: true`
3. If any threshold is exceeded, Guard adds synthetic "fatal" violations
4. CI fails if `--fail-on-violations` is set (or always for fatal violations)

### Usage Example

```bash
# Set strict thresholds for production
export SLOW_RESPONSE_THRESHOLD_MS=2000
export EXPENSIVE_REQUEST_THRESHOLD=0.10
export ERROR_RATE_THRESHOLD=0.05

# Run guard - will fail if ANY threshold breached
crashlens guard production-logs.jsonl \
  --rules .crashlens/rules.yaml \
  --fail-on-violations
```

### Threshold Violation Output

When a threshold is breached, you'll see synthetic violations:

```
[FATAL] perf_latency_threshold: Max latency 3500ms exceeds threshold 2000ms
[FATAL] perf_cost_threshold: Max cost $0.25 exceeds threshold $0.10
[FATAL] perf_error_rate_threshold: Error rate 12.50% exceeds threshold 5.00%
```

These appear alongside regular rule violations in all output formats (text, JSON, Markdown, HTML).

### CI Integration Example

**GitHub Actions:**

```yaml
name: Performance Guard

on: [push, pull_request]

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install CrashLens
        run: pip install crashlens
      
      - name: Enforce Performance Thresholds
        env:
          SLOW_RESPONSE_THRESHOLD_MS: 1500  # 1.5 second SLA
          EXPENSIVE_REQUEST_THRESHOLD: 0.05  # $0.05 max per request
          ERROR_RATE_THRESHOLD: 0.02  # 2% max error rate
        run: |
          crashlens guard logs/*.jsonl \
            --rules .crashlens/rules.yaml \
            --fail-on-violations \
            --output markdown > performance-report.md
      
      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: performance-report
          path: performance-report.md
```

### Best Practices

1. **Start Lenient**: Use default thresholds initially, then tighten based on baseline metrics
2. **Environment-Specific**: Use stricter thresholds in production than staging
3. **Monitor Trends**: Track threshold violations over time to detect performance degradation
4. **Combine with Rules**: Use thresholds alongside custom rules for comprehensive policy enforcement
5. **Test Before Enforcing**: Run guard with `--dry-run` to validate thresholds won't cause false positives

### Disabling Thresholds

To disable specific thresholds, set them to very high values:

```bash
# Disable latency threshold
export SLOW_RESPONSE_THRESHOLD_MS=999999

# Disable cost threshold
export EXPENSIVE_REQUEST_THRESHOLD=9999.99

# Disable error rate threshold
export ERROR_RATE_THRESHOLD=1.0  # 100% = no enforcement
```

Or don't set the environment variables at all (defaults are intentionally lenient).

### Troubleshooting

**Q: Threshold violations but logs look normal?**

Check your log format. Ensure fields match expected names:
- `response_time_ms` for latency (milliseconds)
- `cost_usd` for cost (USD)
- `error` for error status (boolean: true/false)

**Q: Want per-rule thresholds instead of global?**

Use conditional rules with `if_cost_usd_gt` or `if_response_time_gt` conditions instead of environment variables.

**Q: Can I customize synthetic violation severity?**

Not currently. Performance threshold violations are always "fatal" severity to ensure they fail CI.

## Integration Patterns

### Pattern 1: Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

if [ -f "logs/latest.jsonl" ]; then
  crashlens guard logs/latest.jsonl \
    --rules .crashlens/rules.yaml \
    --severity error
  
  if [ $? -ne 0 ]; then
    echo "⚠️  Policy violations detected in logs"
    echo "Review violations before committing"
  fi
fi
```

### Pattern 2: Scheduled Audit

```yaml
# .github/workflows/weekly-audit.yml
name: Weekly Policy Audit
on:
  schedule:
    - cron: '0 9 * * 1'  # Every Monday at 9 AM

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Fetch production logs
        run: ./scripts/fetch-logs.sh
      
      - name: Run Guard
        run: |
          crashlens guard logs/production-*.jsonl \
            --rules .crashlens/rules.yaml \
            --output md > weekly-report.md
      
      - name: Send to Slack
        run: ./scripts/send-to-slack.sh weekly-report.md
```

### Pattern 3: Feature Branch Validation

```yaml
# .github/workflows/pr-check.yml
name: PR Validation
on: pull_request

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Guard on Test Logs
        run: |
          crashlens guard tests/fixtures/*.jsonl \
            --rules .crashlens/rules.yaml \
            --fail-on-violations
```

## FAQ

**Q: Can I use guard with non-LLM logs?**

A: Yes, as long as your logs are JSONL and contain fields matching your rule conditions.

**Q: How do I create custom conditions?**

A: Currently, conditions are fixed. For custom logic, use the existing `crashlens guard` command which supports more complex YAML conditions.

**Q: Can guard analyze live API traffic?**

A: Not directly. Guard analyzes static JSONL files. Use logging middleware to capture traffic to JSONL first.

**Q: What's the difference between guard and guard?**

A: 
- `guard`: Lightweight, CI-focused, simple YAML conditions
- `guard`: Full-featured, complex nested conditions, more verbose

Choose `guard` for CI pipelines and quick checks. Choose `guard` for comprehensive policy enforcement.

**Q: How do I migrate from guard to guard?**

A: Translate your guard rules to guard's simpler condition format:

```yaml
# guard (complex)
match:
  usage.prompt_tokens: ">= 2000"
  model: "gpt-4o"

# guard (simple)
if:
  if_tokens_gt: 2000
  if_model: "gpt-4o"
```

## See Also

- [CrashLens Policy Check](../COMMAND-REFERENCE.md#guard) - Advanced policy evaluation
- [CrashLens Scan](../COMMAND-REFERENCE.md#scan) - Waste pattern detection
- [GitHub Actions Integration](../examples/ci-workflows/) - CI/CD examples
- [Sample Rules](../.crashlens/rules.yaml) - Reference rule templates

## Support

For issues, questions, or contributions:

- GitHub Issues: https://github.com/Crashlens/crashlens/issues
- Documentation: https://github.com/Crashlens/crashlens/docs
