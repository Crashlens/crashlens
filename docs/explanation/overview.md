# What is CrashLens?

**CrashLens** is a privacy-first CLI tool that analyzes AI API logs to detect and prevent costly token waste patterns before they impact your budget.

---

## The Problem

AI applications commonly waste 40-60% of their token budget due to hidden inefficiencies:

- **Retry Loops**: Identical prompts retried multiple times due to errors
- **Model Overkill**: Using GPT-4 for simple tasks that GPT-3.5 could handle  
- **Fallback Storms**: Cascading failures across multiple model fallbacks
- **Fallback Failures**: Exhausted retry chains where all models fail

Traditional monitoring shows you THAT spending is high, but not WHY. CrashLens identifies root causes at the trace level.

---

## The Solution

CrashLens scans your Langfuse/Helicone JSONL logs locally and:

✅ **Detects** 4 core waste patterns with exact string matching  
✅ **Quantifies** cost impact in USD for each detection  
✅ **Provides** actionable optimization recommendations  
✅ **Enforces** custom policies in CI/CD pipelines  
✅ **Protects** privacy with 100% local processing (no data egress)

---

## Core Features

### 🕵️ Intelligent Detection

Four production-grade detectors with priority-based suppression:

1. **Retry Loop Detector** - Identical prompts retried within time windows
2. **Fallback Storm Detector** - Cascading failures across model fallbacks  
3. **Model Overkill Detector** - Expensive models on simple tasks
4. **Fallback Failure Detector** - Failed chains where all models fail

**Cost Calculation**: Each detector computes exact waste cost by comparing actual spend vs. optimal cost.

### 🛡️ Policy Enforcement

Define custom rules in YAML and enforce them in CI/CD:

```yaml
rules:
  - id: RL001
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"
    action: fail
    severity: critical
```

**Guard Mode** (`crashlens guard`) blocks policy violations before production deployment.

### 📊 Multiple Output Formats

- **Markdown**: Human-readable reports with cost breakdowns
- **JSON**: Structured data for dashboards and automation  
- **Slack**: Block Kit messages for team notifications
- **Prometheus**: Metrics for Grafana monitoring
- **HTML**: Rich formatted reports for CI artifacts

### 🔒 Privacy-First Design

- **100% local processing** - no API calls to external services
- **Optional PII scrubbing** - remove emails, phone numbers, SSNs
- **Summary-only mode** - redact trace IDs for safe sharing
- **No telemetry** - zero data collection

---

## How It Works

### 1. Input Sources

Supports multiple log formats:
- Langfuse JSONL exports
- Helicone JSONL exports  
- Langfuse API (direct fetch with `--from-langfuse`)
- Helicone API (direct fetch with `--from-helicone`)
- Stdin/clipboard for quick analysis

### 2. Detection Pipeline

```
JSONL Logs → Parser → 4 Detectors (priority-ordered) → Policy Engine → Formatters → Output
```

- **Parser**: Validates schema, groups by traceId, detects drift
- **Detectors**: Run in priority order with suppression to avoid double-counting
- **Policy Engine**: Evaluates custom YAML rules with constant memory
- **Formatters**: Render results in multiple formats

### 3. Cost Calculation

Each detector calculates waste cost using model pricing:

**Retry Loop Example**:
```
Duplicate tokens: 2,000 (prompt) + 500 (completion) = 2,500
Retry count: 3
Model: gpt-4 ($0.03/1K prompt, $0.06/1K completion)
Waste cost: (2,000 × $0.03/1K × 3) + (500 × $0.06/1K × 3) = $0.27
```

Custom pricing supported via `--config custom-pricing.yaml`.

---

## Quick Start

```bash
# Install
pip install crashlens

# Scan local logs
crashlens scan logs.jsonl

# Fetch from Langfuse and scan
crashlens scan --from-langfuse --hours-back 24

# Enforce policies in CI/CD
crashlens guard logs.jsonl --policy-file policies/production.yaml --fail-on-violations

# Generate weekly cost report
crashlens report week.jsonl --previous-logs last-week.jsonl --output slack --webhook-url $SLACK_WEBHOOK

# Push metrics to Prometheus
crashlens scan logs.jsonl --push-metrics --pushgateway-url http://localhost:9091
```

---

## Key Use Cases

### 1. Development - Catch Waste Early
```bash
# Before committing changes
crashlens scan test-logs.jsonl --summary-only
```

### 2. CI/CD - Policy Gates
```yaml
# GitHub Actions
- name: Policy Check
  run: |
    crashlens guard logs.jsonl \
      --policy-file policies/max-cost.yaml \
      --fail-on-violations \
      --severity error
```

### 3. Production - Continuous Monitoring
```bash
# Daily Langfuse scan → Slack notification
crashlens scan --from-langfuse --hours-back 24 --format slack --webhook-url $SLACK_WEBHOOK
```

### 4. FinOps - Cost Tracking
```bash
# Weekly digest with week-over-week delta
crashlens report current-week.jsonl --previous-logs last-week.jsonl --email finops@company.com
```

---

## Technical Stack

- **Language**: Python 3.12+
- **Package Manager**: Poetry
- **CLI Framework**: Click 8.2.1+
- **Config Format**: YAML
- **Log Format**: JSONL (Langfuse/Helicone schema)
- **Testing**: pytest with 80%+ coverage
- **Type Checking**: mypy with strict mode
- **Metrics**: Prometheus client + Pushgateway

---

## Privacy & Security

✅ **No data egress** - All processing happens locally  
✅ **No telemetry** - Zero data collection or tracking  
✅ **PII removal** - Optional scrubbing of sensitive data  
✅ **Open source** - Full transparency via MIT license  
✅ **Audit-friendly** - Complete trace of what's analyzed

---

## Get Started

📖 **Documentation**: See [docs/](../docs/) for complete guides  
🚀 **Quick Start**: [QUICKSTART.md](./QUICKSTART.md)  
💻 **CLI Reference**: [CLI_COMMAND_REFERENCE.md](./CLI_COMMAND_REFERENCE.md)  
🛡️ **Policy Guide**: [how-to-guides/guard.md](./how-to-guides/guard.md)  
📊 **Observability**: [how-to-guides/observability.md](./how-to-guides/observability.md)

---

**Word Count**: ~750 words
