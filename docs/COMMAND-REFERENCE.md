# CrashLens Command Reference

Complete reference for all CrashLens CLI commands.

**Version**: 1.x  
**Updated**: 2025-01-12

---

## Table of Contents

- [Core Commands](#core-commands)
  - [scan](#scan)
  - [guard](#guard)
  - [pii-remove](#pii-remove)
  - [report](#report)
- [Command Groups](#command-groups)
  - [schema](#schema-group)
  - [config](#config-group)
  - [reports](#reports-group)
  - [slack](#slack-group)
- [Utility Commands](#utility-commands)
- [Deprecated Commands](#deprecated-commands)

---

## Core Commands

### `scan`

Scan JSONL logs for token waste patterns with built-in detectors.

**Usage**:
```bash
crashlens scan [LOGFILE] [OPTIONS]
```

**Options**:
- `--format, -f`: Output format (`slack`, `markdown`, `json`)
- `--demo`: Use built-in demo logs
- `--from-langfuse`: Fetch from Langfuse API
- `--from-helicone`: Fetch from Helicone API
- `--from-clipboard`: Read from clipboard
- `--config`: Custom pricing configuration
- `--policy-file`: Policy file for additional checks
- `--policy-template`: Built-in policy template
- `--summary-only`: Hide trace IDs (privacy mode)
- `--push-metrics`: Push metrics to Prometheus
- `--metrics-config`: Metrics configuration file
- `--log-format`: Specify log schema (`langfuse-v1`, etc.)

**Examples**:
```bash
# Basic scan with Slack output
crashlens scan logs.jsonl --format slack

# Demo mode
crashlens scan --demo

# Fetch from Langfuse and scan
crashlens scan --from-langfuse --hours-back 24

# Scan with policy enforcement
crashlens scan logs.jsonl --policy-file policies/production.yaml

# Privacy mode (no trace IDs)
crashlens scan logs.jsonl --summary-only
```

---

### `guard`

Guard against policy violations with fail-fast enforcement.

**Usage**:
```bash
crashlens guard LOGFILE [OPTIONS]
```

**Options**:
- `--policy-file`: Policy YAML file (required or use `--policy-template`)
- `--policy-template`: Built-in policy template
- `--fail-fast`: Stop on first violation
- `--output-dir`: Directory for violation reports
- `--format`: Output format (`json`, `markdown`)
- `--push-metrics`: Push metrics to Prometheus
- `--metrics-config`: Metrics configuration

**Examples**:
```bash
# Guard with custom policy
crashlens guard logs.jsonl --policy-file policies/strict.yaml

# Guard with built-in template
crashlens guard logs.jsonl --policy-template retry-loop-prevention

# Fail-fast mode for CI/CD
crashlens guard logs.jsonl --policy-file ci-policy.yaml --fail-fast

# Save violations to reports
crashlens guard logs.jsonl --policy-file policy.yaml --output-dir ./violations
```

---

### `pii-remove`

Remove personally identifiable information (PII) from JSONL logs.

**Usage**:
```bash
crashlens pii-remove [INPUT_FILE] [OPTIONS]
```

**Options**:
- `--output, -o`: Output file path
- `--dry-run`: Preview without creating output
- `--types, -t`: Specific PII types to remove (repeatable)
- `--list-types`: List available PII types
- `--verbose, -v`: Show detailed statistics

**Supported PII Types**:
- `email`: Email addresses
- `phone_us`: US phone numbers
- `ssn`: Social Security Numbers
- `credit_card`: Credit card numbers
- `ip_address`: IP addresses
- `api_key`: API keys
- `street_address`: Street addresses
- `date`: Date patterns

**Examples**:
```bash
# Remove all PII types
crashlens pii-remove logs.jsonl

# Remove only emails and phone numbers
crashlens pii-remove logs.jsonl --types email --types phone_us

# Dry run to preview
crashlens pii-remove logs.jsonl --dry-run --verbose

# Custom output path
crashlens pii-remove logs.jsonl --output clean/sanitized.jsonl

# List available PII types
crashlens pii-remove --list-types
```

---

### `report`

Generate cost digest email report from logs.

**Usage**:
```bash
crashlens report LOGFILE [OPTIONS]
```

**Options**:
- `--email`: Recipient email address
- `--subject`: Email subject line
- `--smtp-config`: SMTP configuration file
- `--attach-logs`: Attach original logs
- `--summary-only`: Privacy mode
- `--format`: Output format if not emailing

**Examples**:
```bash
# Send email report
crashlens report logs.jsonl --email team@example.com

# Custom subject
crashlens report logs.jsonl --email ops@example.com --subject "Daily LLM Cost Report"

# With custom SMTP config
crashlens report logs.jsonl --email alerts@example.com --smtp-config smtp.yaml

# Generate report without emailing
crashlens report logs.jsonl --format markdown > report.md
```

---

## Command Groups

### `schema` Group

Schema detection and parser registry tools.

#### `schema list`

List all supported log schema formats.

**Usage**:
```bash
crashlens schema list [OPTIONS]
```

**Options**:
- `--stable-only`: Only show stable/production-ready schemas

**Examples**:
```bash
# List all schemas
crashlens schema list

# List only stable schemas
crashlens schema list --stable-only
```

#### `schema detect`

Auto-detect log schema format (experimental).

**Usage**:
```bash
crashlens schema detect LOGFILE [OPTIONS]
```

**Options**:
- `--sample-size`: Number of lines to sample (default: 10)

**Examples**:
```bash
# Detect schema
crashlens schema detect logs.jsonl

# Use larger sample
crashlens schema detect logs.jsonl --sample-size 50
```

---

### `config` Group

Configuration management and validation commands.

#### `config validate`

Validate configuration files for syntax and semantic correctness.

**Usage**:
```bash
crashlens config validate CONFIG_FILE [OPTIONS]
```

**Options**:
- `--type, -t`: Config type (`metrics`, `policy`, `smtp`)
- `--verbose, -v`: Show detailed validation output

**Examples**:
```bash
# Validate metrics config
crashlens config validate metrics.yaml

# Validate policy with details
crashlens config validate policy.yaml --type policy --verbose

# Validate SMTP config
crashlens config validate smtp.yaml --type smtp
```

#### `config smtp-example`

Generate example SMTP configuration file.

**Usage**:
```bash
crashlens config smtp-example [OPTIONS]
```

**Options**:
- `--output`: Output path (default: `.crashlens/smtp.yaml`)

**Examples**:
```bash
# Generate example
crashlens config smtp-example

# Custom output path
crashlens config smtp-example --output my-smtp.yaml
```

---

### `reports` Group

Manage CrashLens reports and archives.

#### `reports archive`

Archive old reports to timestamped directories.

**Usage**:
```bash
crashlens reports archive [OPTIONS]
```

**Options**:
- `--days`: Archive reports older than N days (default: 30)
- `--base-dir`: Base directory for reports (default: `policy-violations`)

**Examples**:
```bash
# Archive reports older than 30 days
crashlens reports archive

# Archive reports older than 7 days
crashlens reports archive --days 7

# Custom base directory
crashlens reports archive --base-dir ./violations --days 14
```

#### `reports prune`

Delete archived reports older than specified days.

**Usage**:
```bash
crashlens reports prune [OPTIONS]
```

**Options**:
- `--days`: Delete archives older than N days (default: 90)
- `--base-dir`: Base directory for reports

**Examples**:
```bash
# Delete archives older than 90 days
crashlens reports prune

# Delete archives older than 30 days
crashlens reports prune --days 30
```

#### `reports stats`

Show statistics about stored reports.

**Usage**:
```bash
crashlens reports stats [OPTIONS]
```

**Options**:
- `--base-dir`: Base directory for reports

**Examples**:
```bash
# Show report statistics
crashlens reports stats

# Custom directory
crashlens reports stats --base-dir ./violations
```

#### `reports readme`

Generate README.md in reports directory.

**Usage**:
```bash
crashlens reports readme [OPTIONS]
```

**Options**:
- `--base-dir`: Base directory for reports

**Examples**:
```bash
# Generate README
crashlens reports readme

# Custom directory
crashlens reports readme --base-dir ./violations
```

---

### `slack` Group

Slack integration commands.

#### `slack notify`

Send report to Slack webhook.

**Usage**:
```bash
crashlens slack notify [OPTIONS]
```

**Options**:
- `--webhook-url`: Slack webhook URL (required)
- `--report`: Report file to send
- `--summary-only`: Privacy mode (hide trace IDs)

**Examples**:
```bash
# Send report to Slack
crashlens slack notify --webhook-url $SLACK_WEBHOOK --report report.md

# Privacy mode
crashlens slack notify --webhook-url $SLACK_WEBHOOK --report report.md --summary-only
```

---

## Utility Commands

### `init`

Setup wizard to initialize CrashLens configuration.

**Usage**:
```bash
crashlens init
```

### `simulate`

Generate realistic Langfuse-style test traces.

**Usage**:
```bash
crashlens simulate [OPTIONS]
```

**Options**:
- `--output`: Output file path
- `--count`: Number of traces to generate

### `fetch-langfuse`

Fetch traces from Langfuse API.

**Usage**:
```bash
crashlens fetch-langfuse [OPTIONS]
```

**Options**:
- `--hours-back`: Hours of history to fetch
- `--limit`: Maximum number of traces
- `--output`: Save to file

### `fetch-helicone`

Fetch requests from Helicone API.

**Usage**:
```bash
crashlens fetch-helicone [OPTIONS]
```

**Options**:
- `--hours-back`: Hours of history to fetch
- `--limit`: Maximum number of requests
- `--output`: Save to file

### `list-policy-templates`

List all available built-in policy templates.

**Usage**:
```bash
crashlens list-policy-templates
```

### `show-metrics-config`

Display current metrics configuration.

**Usage**:
```bash
crashlens show-metrics-config [OPTIONS]
```

**Options**:
- `--config, -c`: Path to metrics config file

### `validate`

Validate JSON report against schema.

**Usage**:
```bash
crashlens validate REPORT_FILE [OPTIONS]
```

**Options**:
- `--schema-version`: Schema version (default: v1)
- `--strict`: Strict validation mode

---

## Deprecated Commands

⚠️ **These commands are deprecated and will be removed in v2.0.**  
Use the replacement commands shown below.

| Deprecated | Replacement | Notes |
|------------|-------------|-------|
| `crashlens pii-clean` | `crashlens pii-remove` | Hidden from `--help`, shows warning |
| `crashlens list-schemas` | `crashlens schema list` | Hidden from `--help`, shows warning |
| `crashlens detect-schema` | `crashlens schema detect` | Hidden from `--help`, shows warning |
| `crashlens validate-metrics-config` | `crashlens config validate --type metrics` | Hidden from `--help`, shows warning |

**Migration Example**:
```bash
# OLD (deprecated)
crashlens pii-clean logs.jsonl
crashlens list-schemas
crashlens detect-schema logs.jsonl
crashlens validate-metrics-config metrics.yaml

# NEW (recommended)
crashlens pii-remove logs.jsonl
crashlens schema list
crashlens schema detect logs.jsonl
crashlens config validate metrics.yaml --type metrics
```

---

## Environment Variables

### Metrics Collection
- `CRASHLENS_DISABLE_METRICS`: Set to `true`/`1`/`yes` to disable metrics

### Langfuse API
- `LANGFUSE_PUBLIC_KEY`: Langfuse public key
- `LANGFUSE_SECRET_KEY`: Langfuse secret key
- `LANGFUSE_HOST`: Langfuse host URL

### Helicone API
- `HELICONE_API_KEY`: Helicone API key

### SMTP Configuration
- `SMTP_SERVER`: SMTP server hostname
- `SMTP_PORT`: SMTP server port
- `SMTP_USERNAME`: SMTP authentication username
- `SMTP_PASSWORD`: SMTP authentication password
- `SMTP_FROM`: Email sender address

---

## Configuration Files

### Metrics Configuration
**Location**: `.crashlens/metrics.yaml`, `~/.crashlens/metrics.yaml`

**Example**:
```yaml
enabled: true
push_gateway:
  url: "http://localhost:9091"
  job_name: "crashlens"
  timeout_seconds: 5

sampling:
  enabled: true
  default_rate: 0.1  # 10% sampling
  per_rule:
    expensive_rule: 0.01  # 1% sampling
    rare_event: 1.0       # 100% sampling
```

### Policy Configuration
**Location**: `policies/*.yaml`

**Example**:
```yaml
version: 1
global:
  max_violations_per_rule: 100

rules:
  - id: excessive_retries
    description: "Block traces with >3 retries"
    match:
      retry_count: ">3"
    action: fail
    severity: critical
    suggestion: "Implement exponential backoff"
```

### SMTP Configuration
**Location**: `.crashlens/smtp.yaml`

**Example**:
```yaml
server: smtp.gmail.com
port: 587
username: your-email@gmail.com
password: your-app-password
from_addr: alerts@example.com
use_tls: true
```

---

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Policy violation (when using `--fail-fast`)
- `3`: Configuration error
- `4`: API error

---

## Related Documentation

- [CLI Reorganization Guide](CLI_REORGANIZATION.md) - Migration guide for deprecated commands
- [User Manual](USER_MANUAL.md) - End-user guide
- [Policy Guide](GUARD.md) - Policy enforcement documentation
- [Observability Guide](OBSERVABILITY.md) - Metrics and monitoring

---

**Last Updated**: 2025-01-12  
**Version**: CrashLens v1.x
