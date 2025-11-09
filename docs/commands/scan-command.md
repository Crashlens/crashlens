# CrashLens Scan Command

**Core analysis command for detecting token waste patterns in LLM API logs**

---

## Table of Contents

1. [Overview](#overview)
2. [Basic Usage](#basic-usage)
3. [Input Sources](#input-sources)
4. [Output Formats](#output-formats)
5. [Detection & Analysis](#detection--analysis)
6. [Policy Enforcement](#policy-enforcement)
7. [Reporting Options](#reporting-options)
8. [Prometheus Metrics](#prometheus-metrics)
9. [Configuration](#configuration)
10. [Complete Examples](#complete-examples)
11. [Best Practices](#best-practices)

---

## Overview

The `scan` command is CrashLens's primary analysis tool that:

✅ **Detects** 4 core token waste patterns (retry loops, fallback storms, model overkill, fallback failures)  
✅ **Calculates** exact cost impact in USD for each waste pattern  
✅ **Provides** actionable optimization recommendations  
✅ **Enforces** custom policies (optional)  
✅ **Exports** metrics to Prometheus (optional)  
✅ **Generates** reports in multiple formats

**Syntax**:
```bash
crashlens scan [LOGFILE] [EXTRA_FILES...] [OPTIONS]
```

---

## Basic Usage

### Scan Single File

```bash
# Basic scan (outputs to console in Slack format)
crashlens scan logs.jsonl

# With summary
crashlens scan logs.jsonl --summary

# Markdown format
crashlens scan logs.jsonl --format markdown

# JSON format
crashlens scan logs.jsonl --format json
```

### Scan Multiple Files

```bash
# Scan multiple files
crashlens scan file1.jsonl file2.jsonl file3.jsonl

# Scan all JSONL files in directory
crashlens scan logs/*.jsonl

# Recursive scan
crashlens scan --log-paths "logs/**/*.jsonl"
```

### Demo Mode

**Use built-in sample data for testing**:

```bash
# Run with demo data
crashlens scan --demo

# Demo with different formats
crashlens scan --demo --format markdown
crashlens scan --demo --format json --summary

# Demo with policies
crashlens scan --demo --policy-template retry-loop-prevention

# Demo with detailed reports
crashlens scan --demo --detailed --detailed-dir ./demo-reports/
```

**What demo mode includes**:
- 15+ realistic traces with various waste patterns
- Retry loops (3-5 retries on identical prompts)
- Model overkill (GPT-4 for simple tasks)
- Fallback storms (cascading failures)
- Successful and failed traces
- Multiple models (GPT-4, GPT-3.5, Claude)
- Cost data calculated automatically

---

## Input Sources

### 1. Local Files

```bash
# Single file
crashlens scan logs.jsonl

# Multiple files
crashlens scan logs1.jsonl logs2.jsonl logs3.jsonl

# Glob patterns
crashlens scan logs/*.jsonl
crashlens scan --log-paths "**/*.jsonl"
```

### 2. Standard Input (Stdin)

**Read from pipes**:

```bash
# From cat
cat logs.jsonl | crashlens scan --stdin

# From curl
curl https://api.example.com/logs | crashlens scan --stdin

# From another command
generate-logs | crashlens scan --stdin

# With jq filtering
cat logs.jsonl | jq 'select(.model == "gpt-4")' | crashlens scan --stdin
```

### 3. Clipboard

**Paste logs from clipboard**:

```bash
# Read from clipboard
crashlens scan --paste

# Useful for quick analysis of copied logs
```

### 4. Langfuse API

**Fetch directly from Langfuse**:

```bash
# Fetch last 24 hours
crashlens scan --from-langfuse --hours-back 24

# Fetch last 48 hours, limit 500 traces
crashlens scan --from-langfuse --hours-back 48 --limit 500

# Fetch and save to file
crashlens scan --from-langfuse --hours-back 24 --limit 1000 > output.json
```

**Required environment variables**:
```bash
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...
export LANGFUSE_HOST=https://cloud.langfuse.com  # Optional
```

### 5. Helicone API

**Fetch directly from Helicone**:

```bash
# Fetch last 24 hours
crashlens scan --from-helicone --hours-back 24

# Fetch with limit
crashlens scan --from-helicone --hours-back 48 --limit 500
```

**Required environment variables**:
```bash
export HELICONE_API_KEY=sk-helicone-...
```

### Input Source Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `LOGFILE` | Path | None | Path to JSONL log file(s) |
| `--demo` | Flag | False | Use built-in demo data |
| `--stdin` | Flag | False | Read from standard input |
| `--paste` | Flag | False | Read from clipboard |
| `--log-paths` | String | None | Glob pattern for recursive search |
| `--from-langfuse` | Flag | False | Fetch from Langfuse API |
| `--from-helicone` | Flag | False | Fetch from Helicone API |
| `--hours-back` | Int | 24 | Hours to fetch (API sources) |
| `--limit` | Int | 1000 | Max traces to fetch (API sources) |

---

## Output Formats

### 1. Slack Format (Default)

**Slack Block Kit format for webhooks**:

```bash
crashlens scan logs.jsonl
crashlens scan logs.jsonl --format slack
```

**Features**:
- Color-coded severity indicators
- Formatted blocks for easy reading
- Cost summaries
- Ready for Slack webhook posting

**Example output**:
```
🔍 CrashLens Scan Complete

📊 Summary
• Total Traces: 156
• Issues Found: 12
• Potential Savings: $2.45

⚠️ Issues by Type
• Retry Loops: 5 ($1.20)
• Model Overkill: 4 ($0.80)
• Fallback Storms: 3 ($0.45)
```

### 2. Markdown Format

**Human-readable Markdown reports**:

```bash
crashlens scan logs.jsonl --format markdown
```

**Features**:
- Clean, readable formatting
- Tables and lists
- Code blocks for examples
- Easy to read in terminal or save to file

**Example output**:
```markdown
# CrashLens Analysis Report

## Summary
- **Total Traces**: 156
- **Issues Found**: 12
- **Potential Savings**: $2.45

## Retry Loop Detector (5 issues)
### Issue 1: Multiple retries on identical prompt
- **Trace ID**: abc123
- **Cost**: $0.24
- **Retries**: 4
```

### 3. JSON Format

**Structured JSON for automation**:

```bash
crashlens scan logs.jsonl --format json
```

**Features**:
- Machine-readable
- Complete data structure
- Easy to parse programmatically
- Integrates with dashboards

**Example output**:
```json
{
  "summary": {
    "total_traces": 156,
    "issues_found": 12,
    "potential_savings": 2.45,
    "total_cost": 15.60
  },
  "issues": {
    "retry_loops": [...],
    "model_overkill": [...],
    "fallback_storms": [...]
  }
}
```

### Output Format Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-f`, `--format` | Choice | `slack` | Output format: `slack`, `markdown`, `json` |
| `--summary` | Flag | False | Show cost summary with breakdown |
| `--summary-only` | Flag | False | Summary without trace IDs (privacy-safe) |

---

## Detection & Analysis

### 4 Core Detectors

CrashLens includes 4 production-grade detectors:

#### 1. Retry Loop Detector (Priority 1)
**Detects**: Identical prompts retried multiple times

```bash
crashlens scan logs.jsonl --format markdown
```

**Identifies**:
- Exact duplicate prompts within time windows
- Exponential backoff failures
- Redundant API calls
- Cost impact of unnecessary retries

#### 2. Fallback Storm Detector (Priority 2)
**Detects**: Cascading failures across model fallbacks

**Identifies**:
- Excessive fallback chains (>3 models)
- Time-window based fallback patterns
- Failed attempts before success
- Cost of all failed attempts

#### 3. Model Overkill Detector (Priority 3)
**Detects**: Expensive models used for simple tasks

**Identifies**:
- GPT-4 calls generating <10 tokens
- Mismatched model selection
- Overpowered models for simple queries
- Cost difference vs. suitable model

#### 4. Fallback Failure Detector (Priority 4)
**Detects**: Failed fallback chains (all models failed)

**Identifies**:
- Exhausted retry attempts
- Complete fallback chain failures
- Wasted cost on failed attempts
- Systemic issues requiring intervention

### Priority-Based Suppression

Detectors run in priority order to avoid double-counting:
1. Higher-priority detector claims trace first
2. Lower-priority detectors skip already-flagged traces
3. Ensures accurate cost calculations

---

## Detailed Reports

### Comprehensive Per-Trace Reports

**Generate detailed JSON reports for each detection**:

```bash
# Enable detailed reports
crashlens scan logs.jsonl --detailed

# Custom output directory
crashlens scan logs.jsonl --detailed --detailed-dir ./reports/

# With demo data
crashlens scan --demo --detailed --detailed-dir ./demo-reports/
```

**What detailed reports include**:
- Complete trace information
- All related log entries
- Cost calculations breakdown
- Token usage details
- Timestamps and latency
- Model information
- Metadata and context

**Output structure**:
```
detailed_output/
├── retry_loops/
│   ├── trace-abc123.json
│   └── trace-def456.json
├── fallback_storms/
│   ├── trace-ghi789.json
│   └── trace-jkl012.json
├── model_overkill/
└── fallback_failures/
```

**Example detailed report** (`trace-abc123.json`):
```json
{
  "trace_id": "abc123",
  "detector": "Retry Loop Detector",
  "severity": "high",
  "waste_cost": 0.24,
  "waste_tokens": 2400,
  "retry_count": 4,
  "description": "Identical prompt retried 4 times",
  "suggestion": "Implement exponential backoff",
  "records": [
    {
      "timestamp": "2025-01-15T10:00:00Z",
      "model": "gpt-4",
      "prompt_tokens": 600,
      "completion_tokens": 100,
      "cost": 0.06
    },
    ...
  ],
  "cost_breakdown": {
    "original_cost": 0.06,
    "retry_cost": 0.24,
    "total_waste": 0.24
  }
}
```

### Detailed Report Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--detailed` | Flag | False | Generate detailed per-trace JSON reports |
| `--detailed-dir` | Path | `detailed_output` | Directory for detailed reports |

---

## Policy Enforcement

### Built-in Policy Templates

**Use pre-configured policies**:

```bash
# Single template
crashlens scan logs.jsonl --policy-template retry-loop-prevention

# Multiple templates
crashlens scan logs.jsonl --policy-template "retry-loop-prevention,model-overkill-detection"

# All templates
crashlens scan logs.jsonl --policy-template all

# List available templates
crashlens list-policy-templates
```

**Available templates**:
- `retry-loop-prevention`: Detect excessive retries
- `model-overkill-detection`: Flag expensive models on simple tasks
- `fallback-chain-detector`: Monitor fallback patterns
- `budget-protection`: Cost cap enforcement
- `rate-limit-management`: Rate limit detection
- `all`: All templates combined

### Custom Policy Files

**Use custom YAML rules**:

```bash
crashlens scan logs.jsonl --policy-file my-policy.yaml
```

**Example policy** (`my-policy.yaml`):
```yaml
version: 1
rules:
  - id: RL001
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"
    action: warn
    severity: high
```

### Policy Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--policy-template` | String | None | Built-in template(s) to use |
| `--policy-file` | Path | None | Custom policy YAML file |
| `--list-templates` | Flag | False | List available templates |

---

## Reporting Options

### Report Output Control

```bash
# Save to directory (auto-generates filenames)
crashlens scan logs.jsonl --format markdown --report-dir ./reports/

# Save to specific file
crashlens scan logs.jsonl --format json --report-file output.json

# Overwrite without prompting
crashlens scan logs.jsonl --report-file output.json --force

# Flatten directory structure
crashlens scan logs/*.jsonl --report-dir ./reports/ --flatten
```

### Report Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--report-dir` | Path | None | Directory to write reports |
| `--report-file` | Path | None | Explicit path for single report |
| `--force` | Flag | False | Overwrite without prompting |
| `--flatten` | Flag | False | Flatten directory structure |

---

## Prometheus Metrics

### Enable Metrics Export

**Push to Prometheus Pushgateway**:

```bash
# Basic metrics push
crashlens scan logs.jsonl --push-metrics

# Custom Pushgateway URL
crashlens scan logs.jsonl --push-metrics \
  --pushgateway-url http://prometheus:9091

# Custom job name
crashlens scan logs.jsonl --push-metrics \
  --metrics-job crashlens_production
```

### HTTP Server Mode

**Expose metrics endpoint for scraping**:

```bash
# Start HTTP server
crashlens scan logs.jsonl --metrics-http --metrics-port 9090

# Bind to all interfaces
crashlens scan logs.jsonl --metrics-http \
  --metrics-addr 0.0.0.0 \
  --metrics-port 9090

# With authentication
crashlens scan logs.jsonl --metrics-http \
  --metrics-port 9090 \
  --metrics-auth-user admin \
  --metrics-auth-pass secretpass
```

### Metrics Configuration

**Control metrics behavior**:

```bash
# Sample 10% of violations (high-volume production)
crashlens scan logs.jsonl --push-metrics --metrics-sample-rate 0.1

# Cap rule cardinality
crashlens scan logs.jsonl --push-metrics --metrics-max-rules 1000

# Skip TTY check (for CI/CD)
crashlens scan logs.jsonl --push-metrics --skip-tty-check
```

### Metrics Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--push-metrics` | Flag | False | Enable Prometheus metrics push |
| `--pushgateway-url` | String | `http://localhost:9091` | Pushgateway URL |
| `--metrics-job` | String | `crashlens_scan` | Job name |
| `--metrics-max-rules` | Int | 500 | Max unique rule names |
| `--metrics-sample-rate` | Float | 1.0 | Sampling rate (0.0-1.0) |
| `--metrics-http` | Flag | False | Enable HTTP server |
| `--metrics-port` | Int | 9090 | HTTP server port |
| `--metrics-addr` | String | `127.0.0.1` | Bind address |
| `--metrics-auth-user` | String | None | Basic auth username |
| `--metrics-auth-pass` | String | None | Basic auth password |
| `--skip-tty-check` | Flag | False | Skip TTY check (CI/CD) |

### Exported Metrics

**Metrics available in Prometheus**:
- `crashlens_violations_total{severity, rule}`: Total violations by severity
- `crashlens_rule_hits_total{rule, severity}`: Hits per rule
- `crashlens_cost_savings_total`: Potential cost savings
- `crashlens_tokens_wasted_total`: Wasted tokens
- `crashlens_last_run_timestamp_seconds`: Last run timestamp
- `crashlens_metrics_push_status`: Push success/failure

---

## Configuration

### Custom Pricing

**Override default model pricing**:

```bash
crashlens scan logs.jsonl --config custom-pricing.yaml
```

**Example** (`custom-pricing.yaml`):
```yaml
models:
  gpt-4:
    prompt_token_cost: 0.00003
    completion_token_cost: 0.00006
  gpt-3.5-turbo:
    prompt_token_cost: 0.0000015
    completion_token_cost: 0.000002
  claude-3-opus:
    prompt_token_cost: 0.000015
    completion_token_cost: 0.000075
```

### Schema Validation

**Validate log format**:

```bash
# Contract check
crashlens scan logs.jsonl --contract-check

# Specify format
crashlens scan logs.jsonl --contract-check --log-format langfuse-v1

# Show schema requirements
crashlens scan --contract-info
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-c`, `--config` | Path | None | Custom pricing config file |
| `--contract-check` | Flag | False | Validate schema contract |
| `--log-format` | Choice | `langfuse-v1` | Log format version |
| `--contract-info` | Flag | False | Show schema requirements |

---

## Complete Examples

### 1. Basic Analysis

```bash
# Simple scan
crashlens scan logs.jsonl

# With summary
crashlens scan logs.jsonl --summary --format markdown

# Multiple files
crashlens scan logs/*.jsonl --format json --summary
```

### 2. Demo & Testing

```bash
# Quick demo
crashlens scan --demo

# Demo with all policies
crashlens scan --demo --policy-template all --format markdown

# Demo with detailed reports
crashlens scan --demo --detailed --detailed-dir ./demo-reports/
```

### 3. Stdin Processing

```bash
# From file
cat logs.jsonl | crashlens scan --stdin --format markdown

# From API
curl https://api.example.com/logs | crashlens scan --stdin --format json

# Filtered with jq
cat logs.jsonl | jq 'select(.model == "gpt-4")' | crashlens scan --stdin

# Chained processing
generate-logs | filter-errors | crashlens scan --stdin --summary
```

### 4. Production Monitoring

```bash
# Fetch from Langfuse and analyze
crashlens scan --from-langfuse --hours-back 24 \
  --format json \
  --policy-template all \
  --detailed \
  --report-dir ./production-reports/ \
  --push-metrics \
  --pushgateway-url http://prometheus:9091 \
  --skip-tty-check

# With custom config
crashlens scan --from-langfuse --hours-back 48 --limit 5000 \
  --config custom-pricing.yaml \
  --format markdown \
  --summary \
  --report-file weekly-report.md
```

### 5. CI/CD Integration

```bash
# CI pipeline scan
crashlens scan logs.jsonl \
  --format json \
  --policy-template all \
  --summary-only \
  --report-file ci-report.json \
  --push-metrics \
  --skip-tty-check \
  --force

# With contract validation
crashlens scan logs.jsonl \
  --contract-check \
  --log-format langfuse-v1 \
  --format json \
  --push-metrics
```

### 6. Detailed Reporting

```bash
# Full analysis with detailed reports
crashlens scan logs.jsonl \
  --format markdown \
  --summary \
  --detailed \
  --detailed-dir ./detailed-reports/ \
  --report-file summary.md

# Demo with detailed output
crashlens scan --demo \
  --format json \
  --detailed \
  --detailed-dir ./demo-detailed/
```

### 7. High-Volume Production

```bash
# Production with sampling
crashlens scan --from-langfuse --hours-back 168 --limit 100000 \
  --format json \
  --summary-only \
  --push-metrics \
  --metrics-sample-rate 0.05 \
  --metrics-max-rules 2000 \
  --pushgateway-url http://pushgateway.prod:9091 \
  --metrics-job crashlens_weekly \
  --skip-tty-check

# HTTP metrics server
crashlens scan logs.jsonl \
  --metrics-http \
  --metrics-port 9090 \
  --metrics-addr 0.0.0.0 \
  --metrics-auth-user prometheus \
  --metrics-auth-pass $METRICS_PASSWORD \
  --format json
```

---

## Best Practices

### 1. Choose the Right Input Source

- **Local files**: Best for one-time analysis or archived logs
- **Stdin**: Great for piping and filtering
- **API fetch**: Ideal for live monitoring and scheduled scans
- **Demo**: Perfect for testing and learning

### 2. Select Appropriate Output Format

- **Slack**: For team notifications and webhooks
- **Markdown**: For readable reports and documentation
- **JSON**: For automation, dashboards, and data processing

### 3. Use Detailed Reports Wisely

- Enable for investigation and deep analysis
- Disable for high-volume production scans
- Store in dedicated directory for organization

### 4. Leverage Policies

- Start with built-in templates
- Create custom policies for your use case
- Test policies with `--demo` mode first

### 5. Configure Metrics Appropriately

**Development/Staging**:
```bash
crashlens scan logs.jsonl --push-metrics
```

**Production (high volume)**:
```bash
crashlens scan logs.jsonl \
  --push-metrics \
  --metrics-sample-rate 0.1 \
  --metrics-max-rules 1000 \
  --skip-tty-check
```

### 6. Handle Large Datasets

- Use `--summary-only` to reduce output
- Sample with `--metrics-sample-rate`
- Process in batches with `--limit`
- Use glob patterns for organized scanning

### 7. Privacy & Security

- Use `--summary-only` for safe sharing (hides trace IDs)
- Remove PII before scanning: `crashlens pii-remove logs.jsonl`
- Don't expose `--metrics-addr 0.0.0.0` without auth
- Store API keys in environment variables

---

## See Also

- **[Guard Command](./guard.md)**: CI/CD policy enforcement
- **[Report Command](./report.md)**: Cost digest reports
- **[Integrations Guide](./integrations.md)**: Slack, email, webhooks
- **[Observability Guide](./observability.md)**: Prometheus & Grafana
- **[Inputs & Config Guide](./inputs-and-config.md)**: Configuration reference
- **[CLI Command Reference](../CLI_COMMAND_REFERENCE.md)**: All commands

---

**Quick Start**: `crashlens scan --demo --format markdown --summary`
