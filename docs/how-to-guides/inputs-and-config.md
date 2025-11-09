# Inputs and Configuration Guide

This guide covers how to provide input to CrashLens and configure its behavior through various methods.

---

## Table of Contents

1. [Input Sources](#input-sources)
2. [Log Format Requirements](#log-format-requirements)
3. [Platform-Specific Setup](#platform-specific-setup)
4. [File Handling](#file-handling)
5. [Configuration Precedence](#configuration-precedence)
6. [Configuration Methods](#configuration-methods)
7. [Best Practices](#best-practices)

---

## Input Sources

CrashLens accepts log data from multiple sources:

### 1. Local JSONL Files

**Basic usage**:
```bash
crashlens scan logs.jsonl
```

**Recommended locations**:
- `.llm_logs/` (recommended)
- `logs/`
- Any directory with `*.jsonl` files

### 2. Langfuse API

**Direct fetch from Langfuse**:
```bash
crashlens scan --from-langfuse --hours-back 24 --limit 1000
```

**Environment variables required**:
```bash
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...
export LANGFUSE_HOST=https://cloud.langfuse.com  # Optional
```

### 3. Helicone API

**Direct fetch from Helicone**:
```bash
crashlens scan --from-helicone --hours-back 24 --limit 1000
```

**Environment variables required**:
```bash
export HELICONE_API_KEY=sk-helicone-...
```

### 4. Stdin/Clipboard

**From stdin**:
```bash
cat logs.jsonl | crashlens scan --from-stdin
```

**From clipboard**:
```bash
crashlens scan --from-clipboard
```

---

## Log Format Requirements

### Required JSONL Format

Each line must be a valid JSON object:

```json
{
  "trace_id": "abc123",
  "model": "gpt-4", 
  "usage": {"total_tokens": 1500, "prompt_tokens": 100, "completion_tokens": 1400},
  "cost": 0.03,
  "timestamp": "2025-01-15T10:30:00Z",
  "status": "success"
}
```

### Required Fields

- `model`: Model name (e.g., "gpt-4", "gpt-3.5-turbo", "claude-3")
- `usage.total_tokens` or `usage.prompt_tokens` + `usage.completion_tokens`

### Optional But Recommended Fields

- `cost` or `totalCost`: Cost of the API call in USD
- `trace_id` or `traceId`: Unique identifier for the request
- `timestamp` or `startTime`/`endTime`: When the request occurred
- `status` or `level`: Success/error status
- `metadata`: Additional context (team, route, etc.)

### Langfuse-Compatible Schema

CrashLens validates against Langfuse schema and warns about unknown fields to detect schema drift:

```json
{
  "traceId": "trace-123",
  "startTime": "2024-01-01T10:00:00Z",
  "endTime": "2024-01-01T10:00:05Z",
  "model": "gpt-4",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 50,
    "total_tokens": 150
  },
  "cost": 0.015,
  "level": "success",
  "metadata": {
    "fallback_attempted": false,
    "route": "api/chat"
  }
}
```

---

## Platform-Specific Setup

### LangFuse Integration

#### Export from Dashboard
1. Go to your LangFuse project dashboard
2. Navigate to "Traces" section
3. Export traces as JSONL format
4. Save to `.llm_logs/langfuse-traces.jsonl`

#### Using LangFuse API
```bash
mkdir -p .llm_logs
curl -X GET "https://cloud.langfuse.com/api/public/traces" \
  -H "Authorization: Bearer YOUR_LANGFUSE_SECRET_KEY" \
  -H "Content-Type: application/json" \
  > .llm_logs/langfuse-traces.jsonl
```

#### Using Python SDK
```python
from langfuse import Langfuse
import json

langfuse = Langfuse(
    secret_key="your-secret-key",
    public_key="your-public-key"
)

# Get traces and save to log file
traces = langfuse.get_traces(limit=1000)
with open('.llm_logs/langfuse-traces.jsonl', 'w') as f:
    for trace in traces.data:
        f.write(json.dumps(trace.dict()) + '\n')
```

### OpenAI Direct Integration

**Manual Logging**:
```python
import json
import os
from datetime import datetime
from openai import OpenAI

client = OpenAI()

def log_openai_call(response, model, prompt):
    """Log OpenAI API call to .llm_logs/"""
    os.makedirs('.llm_logs', exist_ok=True)
    
    log_entry = {
        "trace_id": f"openai_{int(datetime.now().timestamp())}",
        "model": model,
        "usage": {
            "total_tokens": response.usage.total_tokens,
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens
        },
        "cost": calculate_cost(model, response.usage),
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success"
    }
    
    with open('.llm_logs/openai.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')

# Usage
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}]
)
log_openai_call(response, "gpt-4", "Hello!")
```

### Anthropic Integration

```python
import json
import os
from datetime import datetime
import anthropic

client = anthropic.Anthropic(api_key="your-api-key")

def log_anthropic_call(response, model):
    """Log Anthropic API call to .llm_logs/"""
    os.makedirs('.llm_logs', exist_ok=True)
    
    log_entry = {
        "trace_id": f"anthropic_{response.id}",
        "model": model,
        "usage": {
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens
        },
        "timestamp": datetime.utcnow().isoformat(),
        "status": "success"
    }
    
    with open('.llm_logs/anthropic.jsonl', 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
```

---

## File Handling

### Single File Handling

**Basic scan**:
```bash
crashlens scan my-logs.jsonl
```

**With custom output location**:
```bash
crashlens scan my-logs.jsonl --format markdown --report-dir ./reports/
```

**With specific report name**:
```bash
crashlens scan logs/prod.jsonl --report-file ./reports/production-analysis.md
```

### Multi-File Batch Operations

**Scan all files in directory**:
```bash
crashlens scan logs/*.jsonl
```

**Scan recursively**:
```bash
find logs/ -name "*.jsonl" -exec crashlens scan {} \;
```

**Generate unique reports for each file**:
```bash
# Automatic naming based on input file
for file in logs/*.jsonl; do
  crashlens scan "$file" --format markdown --report-dir ./reports/
done
```

### Glob Patterns

**All JSONL files in current directory**:
```bash
crashlens scan *.jsonl
```

**All JSONL files in logs/ and subdirectories**:
```bash
crashlens scan logs/**/*.jsonl
```

**Date-based patterns**:
```bash
# Scan logs from January 2025
crashlens scan logs/2025-01-*.jsonl
```

### Directory Structure Management

**Recommended structure**:
```
project/
├── .llm_logs/                 # Input logs
│   ├── production/
│   │   ├── 2025-01.jsonl
│   │   └── 2025-02.jsonl
│   ├── staging/
│   └── development/
├── reports/                   # Generated reports
│   ├── production/
│   ├── staging/
│   └── development/
└── policies/                  # Policy rules
    ├── production.yaml
    └── staging.yaml
```

**Create structure**:
```bash
mkdir -p .llm_logs/{production,staging,development}
mkdir -p reports/{production,staging,development}
mkdir -p policies
```

---

## Configuration Precedence

CrashLens uses a **strict precedence order** for configuration:

```
1. CLI Flags           (highest priority)
2. Environment Variables
3. YAML Config File
4. Hardcoded Defaults  (lowest priority)
```

**Rule**: The highest-priority source that provides a value wins.

### Examples

#### CLI Flags Override Everything

```bash
# Even if env vars or config file set different values,
# CLI flags take precedence
crashlens scan logs.jsonl \
  --push-metrics \
  --metrics-sample-rate 0.1 \
  --pushgateway-url http://custom:9091
```

#### Environment Variables Override Config File

```bash
# These override values in metrics.yaml
export CRASHLENS_PUSH_METRICS=true
export CRASHLENS_METRICS_SAMPLE_RATE=0.5

crashlens scan logs.jsonl  # Uses env var values
```

#### Config File Provides Defaults

```yaml
# .crashlens/metrics.yaml
# Used only if not overridden by env vars or CLI flags
push_metrics: true
sample_rate: 1.0
pushgateway_url: http://localhost:9091
```

---

## Configuration Methods

### 1. CLI Flags (Highest Priority)

Use for one-off testing and ad-hoc adjustments:

```bash
crashlens scan logs.jsonl \
  --format markdown \
  --report-dir ./reports/ \
  --push-metrics \
  --metrics-sample-rate 0.1 \
  --policy-file policies/production.yaml
```

**Common flags**:
- `--format`: Output format (slack, markdown, json)
- `--report-dir`: Output directory for reports
- `--report-file`: Specific output file path
- `--push-metrics`: Enable Prometheus metrics
- `--policy-file`: Path to policy YAML file
- `--config`: Path to custom pricing config

### 2. Environment Variables

Use for CI/CD and container deployments:

```bash
# Langfuse credentials
export LANGFUSE_PUBLIC_KEY=pk-...
export LANGFUSE_SECRET_KEY=sk-...

# Helicone credentials
export HELICONE_API_KEY=sk-helicone-...

# SMTP for email reports
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your-email@example.com
export SMTP_PASSWORD=your-app-password

# Metrics configuration
export CRASHLENS_PUSH_METRICS=true
export CRASHLENS_METRICS_SAMPLE_RATE=0.1
export CRASHLENS_PUSHGATEWAY_URL=http://prometheus:9091

# Config file override
export CRASHLENS_METRICS_CONFIG=/path/to/config.yaml
```

### 3. YAML Config Files

Use for persistent, version-controlled settings:

#### Model Pricing Config

**File**: `custom-pricing.yaml`

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

**Usage**:
```bash
crashlens scan logs.jsonl --config custom-pricing.yaml
```

#### Metrics Config

**File**: `.crashlens/metrics.yaml`

```yaml
# Global metrics configuration
push_metrics: true
sample_rate: 1.0
pushgateway_url: http://localhost:9091
job_name: crashlens_production

# HTTP server mode
http_enabled: false
http_port: 9090
http_addr: 127.0.0.1

# Per-rule sampling overrides
per_rule_sample_rates:
  RL001: 0.1  # Sample 10% of RL001 violations
  RL002: 1.0  # Sample 100% of RL002 violations
```

#### Policy Rules

**File**: `policies/production.yaml`

```yaml
version: 1
rules:
  - id: RL001
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"
    action: fail
    severity: critical
```

**Usage**:
```bash
crashlens guard logs.jsonl --policy-file policies/production.yaml
```

#### SMTP Config

**File**: `.crashlens/smtp.yaml`

```yaml
server: smtp.gmail.com
port: 587
user: alerts@example.com
password: your-app-specific-password
from: CrashLens Alerts <alerts@example.com>
use_tls: true
timeout: 30
```

**Generate example**:
```bash
crashlens config smtp-example
```

### Config File Search Locations

CrashLens searches for config files in this order:

1. `--config <path>` or `--policy-file <path>` (CLI flag)
2. `$CRASHLENS_METRICS_CONFIG` (environment variable)
3. `./.crashlens/metrics.yaml` (current directory)
4. `../.crashlens/metrics.yaml` (parent directories, up to 5 levels)
5. `~/.crashlens/metrics.yaml` (home directory)

---

## Best Practices

### 1. Organize Logs by Environment

```
.llm_logs/
├── production/
│   ├── 2025-01.jsonl
│   └── 2025-02.jsonl
├── staging/
└── development/
```

### 2. Use Environment-Specific Policies

```
policies/
├── production.yaml    # Strict rules
├── staging.yaml       # Moderate rules
└── development.yaml   # Lenient rules
```

### 3. Secure Credentials

**Never commit credentials**:
```bash
# Add to .gitignore
.env
.crashlens/smtp.yaml
.crashlens/credentials.yaml
```

**Use environment variables in CI/CD**:
```yaml
# GitHub Actions
env:
  LANGFUSE_PUBLIC_KEY: ${{ secrets.LANGFUSE_PUBLIC_KEY }}
  LANGFUSE_SECRET_KEY: ${{ secrets.LANGFUSE_SECRET_KEY }}
```

### 4. Consistent Naming Patterns

**Date-based logs**:
```
logs/
├── 2025-01-15.jsonl
├── 2025-01-16.jsonl
└── 2025-01-17.jsonl
```

**Week-based logs**:
```
logs/
├── 2025-W01.jsonl  # Week 1
├── 2025-W02.jsonl  # Week 2
└── 2025-W03.jsonl  # Week 3
```

### 5. Validate Log Format

Before running full analysis:

```bash
# Check first 10 lines
head -10 logs.jsonl | jq .

# Validate JSON syntax
cat logs.jsonl | jq empty
```

### 6. Regular Cleanup

```bash
# Remove logs older than 90 days
find .llm_logs/ -name "*.jsonl" -mtime +90 -delete

# Archive old reports
tar -czf reports-$(date +%Y%m).tar.gz reports/
mv reports-$(date +%Y%m).tar.gz archives/
```

---

## Troubleshooting

### Issue: "No such file or directory"

**Cause**: File path incorrect or file doesn't exist

**Solution**:
```bash
# Check if file exists
ls -la logs.jsonl

# Use absolute path
crashlens scan /full/path/to/logs.jsonl
```

### Issue: "Invalid JSON" errors

**Cause**: Malformed JSON in log file

**Solution**:
```bash
# Find invalid lines
cat logs.jsonl | jq empty 2>&1 | grep "parse error"

# Validate each line
while IFS= read -r line; do
  echo "$line" | jq empty || echo "Invalid: $line"
done < logs.jsonl
```

### Issue: "No data in report"

**Cause**: Log entries missing required fields

**Solution**:
```bash
# Check for required fields
head -1 logs.jsonl | jq 'has("model") and has("usage")'

# Inspect log structure
head -1 logs.jsonl | jq .
```

### Issue: Environment variables not working

**Cause**: Variables not exported or incorrect naming

**Solution**:
```bash
# Verify variables are set
env | grep CRASHLENS
env | grep LANGFUSE

# Export variables (don't just set them)
export LANGFUSE_PUBLIC_KEY=pk-...  # ✅ Correct
LANGFUSE_PUBLIC_KEY=pk-...          # ❌ Wrong (not exported)
```

### Issue: Config file not found

**Cause**: File in wrong location or incorrect name

**Solution**:
```bash
# Check current search path
crashlens scan logs.jsonl --verbose

# Create config in correct location
mkdir -p .crashlens
echo "sample_rate: 1.0" > .crashlens/metrics.yaml

# Or specify explicit path
crashlens scan logs.jsonl --metrics-config /path/to/config.yaml
```

---

## See Also

- [Guard Documentation](./guard.md) - Policy enforcement
- [CI/CD Integration](./ci-cd-integration.md) - Pipeline setup
- [Integrations Guide](./integrations.md) - Slack, email, webhooks
- [Observability Guide](./observability.md) - Metrics and monitoring
