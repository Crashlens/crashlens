# CrashLens CLI Command Reference

**Complete guide to all CrashLens commands, options, and usage examples**

**Version**: 2.10.1  
**Last Updated**: 2025-11-09

---

## Table of Contents

1. [Overview](#overview)
2. [Global Options](#global-options)
3. [Main Commands](#main-commands)
   - [scan](#scan) - Detect token waste patterns
   - [guard](#guard) - Policy enforcement
   - [report](#report) - Cost digest reports
   - [simulate](#simulate) - Generate test data
4. [Data Source Commands](#data-source-commands)
   - [fetch-langfuse](#fetch-langfuse)
   - [fetch-helicone](#fetch-helicone)
5. [PII Commands](#pii-commands)
   - [pii-remove](#pii-remove)
   - [pii-clean](#pii-clean)
6. [Configuration Commands](#configuration-commands)
   - [init](#init)
   - [config smtp-example](#config-smtp-example)
   - [validate-metrics-config](#validate-metrics-config)
   - [show-metrics-config](#show-metrics-config)
7. [Utility Commands](#utility-commands)
   - [list-policy-templates](#list-policy-templates)
8. [Slack Integration](#slack-integration)
   - [slack notify](#slack-notify)
9. [Environment Variables](#environment-variables)
10. [Exit Codes](#exit-codes)

---

## Overview

CrashLens is a CLI tool for detecting token waste in LLM API logs with production-grade policy enforcement.

**Basic Usage**:
```bash
crashlens <command> [options] [arguments]
```

**Get Help**:
```bash
crashlens --help                # List all commands
crashlens <command> --help      # Help for specific command
crashlens --version             # Show version
```

---

## Global Options

Available for all commands:

| Option | Description |
|--------|-------------|
| `--version` | Show the version and exit |
| `--help` | Show help message and exit |

---

## Main Commands

### `scan`

**Purpose**: Scan logs for token waste patterns (retry loops, fallback storms, model overkill, fallback failures)

**Syntax**:
```bash
crashlens scan [LOGFILE] [EXTRA_FILES...] [OPTIONS]
```

#### Basic Usage

```bash
# Scan single file
crashlens scan logs.jsonl

# Scan multiple files
crashlens scan file1.jsonl file2.jsonl file3.jsonl

# Scan with demo data
crashlens scan --demo

# Read from stdin
cat logs.jsonl | crashlens scan --stdin

# Read from clipboard
crashlens scan --paste
```

#### Input Sources

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `LOGFILE` | Path | None | Path to JSONL log file(s) |
| `--demo` | Flag | False | Use built-in demo data |
| `--stdin` | Flag | False | Read from standard input |
| `--paste` | Flag | False | Read from clipboard |
| `--log-paths` | String | None | Glob pattern (supports `**`) for recursive file search |
| `--from-langfuse` | Flag | False | Fetch traces from Langfuse API |
| `--from-helicone` | Flag | False | Fetch requests from Helicone API |

**Examples**:
```bash
# Recursive scan
crashlens scan --log-paths "logs/**/*.jsonl"

# Fetch from Langfuse and scan
crashlens scan --from-langfuse --hours-back 48 --limit 500

# Fetch from Helicone
crashlens scan --from-helicone --hours-back 24
```

#### Output Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-f`, `--format` | Choice | `slack` | Output format: `slack`, `markdown`, `json` |
| `--summary` | Flag | False | Show cost summary with breakdown |
| `--summary-only` | Flag | False | Summary without trace IDs |
| `--detailed` | Flag | False | Generate detailed per-trace JSON reports |
| `--detailed-dir` | Path | `detailed_output` | Directory for detailed reports |
| `--report-dir` | Path | None | Directory to write report files |
| `--report-file` | Path | None | Explicit path to write single report |
| `--force` | Flag | False | Overwrite existing reports without prompting |
| `--flatten` | Flag | False | Flatten directory structure in reports |

**Examples**:
```bash
# Markdown output with summary
crashlens scan logs.jsonl --format markdown --summary

# JSON output to specific file
crashlens scan logs.jsonl --format json --report-file output.json

# Detailed per-trace reports
crashlens scan logs.jsonl --detailed --detailed-dir ./traces/
```

#### Policy Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--policy-template` | String | None | Use built-in template(s): `retry-loop-prevention`, `model-overkill-detection`, `all`, etc. |
| `--policy-file` | Path | None | Use custom policy YAML file |
| `--list-templates` | Flag | False | List available templates and exit |

**Examples**:
```bash
# Use single template
crashlens scan logs.jsonl --policy-template retry-loop-prevention

# Use multiple templates
crashlens scan logs.jsonl --policy-template "retry-loop-prevention,model-overkill-detection"

# Use all templates
crashlens scan logs.jsonl --policy-template all

# Custom policy file
crashlens scan logs.jsonl --policy-file my-policy.yaml
```

#### Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-c`, `--config` | Path | None | Custom pricing config file |
| `--hours-back` | Int | 24 | Hours back to fetch (for API sources) |
| `--limit` | Int | 1000 | Max traces/requests to fetch (for API sources) |

#### Schema Validation

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--contract-check` | Flag | False | Validate logs against schema contract |
| `--log-format` | Choice | `langfuse-v1` | Log format: `langfuse-v1`, `langfuse-v2` |
| `--contract-info` | Flag | False | Display schema requirements and exit |

**Examples**:
```bash
# Validate schema
crashlens scan logs.jsonl --contract-check --log-format langfuse-v1

# Show schema info
crashlens scan --contract-info
```

#### Prometheus Metrics

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--push-metrics` | Flag | False | Enable Prometheus metrics push |
| `--pushgateway-url` | String | `http://localhost:9091` | Pushgateway URL |
| `--metrics-job` | String | `crashlens_scan` | Job name for metrics grouping |
| `--metrics-max-rules` | Int | 500 | Max unique rule names (overflow protection) |
| `--metrics-sample-rate` | Float | 1.0 | Sampling rate (0.0-1.0) |
| `--metrics-http` | Flag | False | Enable HTTP server for scraping |
| `--metrics-port` | Int | 9090 | HTTP server port (1024-65535) |
| `--metrics-addr` | String | `127.0.0.1` | HTTP server bind address |
| `--metrics-auth-user` | String | None | Basic auth username |
| `--metrics-auth-pass` | String | None | Basic auth password |
| `--skip-tty-check` | Flag | False | Skip TTY check (for CI/CD) |

**Examples**:
```bash
# Push metrics to Pushgateway
crashlens scan logs.jsonl --push-metrics

# Custom Pushgateway
crashlens scan logs.jsonl --push-metrics --pushgateway-url http://metrics.company.com:9091

# HTTP server with auth
crashlens scan logs.jsonl --metrics-http --metrics-port 9090 \
  --metrics-addr 0.0.0.0 \
  --metrics-auth-user admin \
  --metrics-auth-pass secretpass
```

#### Complete Examples

```bash
# Basic scan with Markdown output
crashlens scan logs.jsonl --format markdown

# Production scan with all features
crashlens scan logs.jsonl \
  --format json \
  --policy-template all \
  --summary \
  --detailed \
  --report-dir ./reports/ \
  --push-metrics \
  --contract-check

# CI/CD scan
crashlens scan --from-langfuse \
  --hours-back 24 \
  --limit 1000 \
  --format json \
  --policy-file .crashlens/policies.yaml \
  --push-metrics \
  --pushgateway-url http://pushgateway:9091 \
  --skip-tty-check
```

---

### `guard`

**Purpose**: CI-friendly policy enforcement - evaluate logs against rules and fail builds on violations

**Syntax**:
```bash
crashlens guard [LOGFILE] [OPTIONS]
```

#### Basic Usage

```bash
# Basic guard with rules
crashlens guard logs.jsonl --rules rules.yaml

# Dry run (don't fail build)
crashlens guard logs.jsonl --rules rules.yaml --dry-run

# Auto-discover rules
crashlens guard logs.jsonl  # Searches for .crashlens/rules.yaml
```

#### Input/Output

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `LOGFILE` | Path | Required | Path to JSONL log file or directory |
| `--rules` | Path | Auto-discover | Path to rules YAML file |
| `--output` | Choice | `text` | Output format: `json`, `md`, `text`, `html` |
| `--report-path` | Path | `crashlens-report.json` | Path to write structured report |

**Examples**:
```bash
# JSON output
crashlens guard logs.jsonl --rules rules.yaml --output json

# HTML report
crashlens guard logs.jsonl --output html

# Custom report path
crashlens guard logs.jsonl --report-path ./ci-reports/violations.json
```

#### Policy Control

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `-s`, `--suppress` | String | None | Suppress specific rule(s) by ID (repeatable) |
| `--severity` | Choice | `error` | Minimum severity threshold: `warn`, `error`, `fatal` |
| `--fail-on-violations` | Flag | False | Exit with non-zero code on violations |
| `--dry-run` | Flag | False | Show violations but don't fail build |

**Examples**:
```bash
# Suppress noisy rules
crashlens guard logs.jsonl --suppress RL001 --suppress RL002

# Only fatal violations fail build
crashlens guard logs.jsonl --severity fatal --fail-on-violations

# See violations without failing
crashlens guard logs.jsonl --dry-run
```

#### Privacy & Content

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--no-content` | Flag | False | Exclude log content from reports (privacy mode) |
| `--strip-pii` | Flag | False | Remove PII (emails, phones, SSNs) from output |
| `--summary-only` | Flag | False | Suppress trace IDs for safe internal sharing |

**Examples**:
```bash
# Privacy-safe report
crashlens guard logs.jsonl --no-content --strip-pii --summary-only

# Remove PII only
crashlens guard logs.jsonl --strip-pii
```

#### Baseline Comparison

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--baseline-logs` | Path | None | Historical logs for P95/P99 comparison |
| `--baseline-deviation` | Float | 0.50 | Deviation threshold (0.50 = 50%) |

**Examples**:
```bash
# Alert on 50% deviation from baseline
crashlens guard current.jsonl \
  --baseline-logs historical.jsonl \
  --baseline-deviation 0.50
```

#### Cost Control

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--cost-cap` | Float | None | Maximum allowed total cost in USD (fails if exceeded) |

**Examples**:
```bash
# Fail if total cost > $100
crashlens guard logs.jsonl --cost-cap 100.0 --fail-on-violations
```

#### Hooks & Automation

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--annotation-hook` | String | None | Command to run after report (receives report path as arg) |

**Examples**:
```bash
# Post-process report
crashlens guard logs.jsonl --annotation-hook "./process-report.sh"
```

#### Prometheus Metrics

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--push-metrics` | Flag | False | Push metrics to Prometheus Pushgateway |
| `--pushgateway-url` | String | `http://localhost:9091` or `$CRASHLENS_PUSHGATEWAY` | Pushgateway URL |
| `--metrics-job` | String | `crashlens-guard` or `$CRASHLENS_METRICS_JOB` | Job name for metrics |

**Examples**:
```bash
# Push metrics with environment variables
export CRASHLENS_PUSHGATEWAY=http://pushgateway:9091
export CRASHLENS_METRICS_JOB=guard_production
crashlens guard logs.jsonl --push-metrics

# CLI flags override env vars
crashlens guard logs.jsonl --push-metrics \
  --pushgateway-url http://localhost:9091 \
  --metrics-job my-job
```

#### Complete Examples

```bash
# CI/CD pipeline
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --severity error \
  --fail-on-violations \
  --output json \
  --report-path ci-report.json \
  --push-metrics

# Local development
crashlens guard logs.jsonl --dry-run --output text

# Production with all features
crashlens guard logs/ \
  --rules policies/prod.yaml \
  --suppress TEMP_EXEMPT_001 \
  --severity error \
  --fail-on-violations \
  --baseline-logs historical/ \
  --baseline-deviation 0.30 \
  --cost-cap 500.0 \
  --strip-pii \
  --summary-only \
  --push-metrics \
  --annotation-hook "./notify-team.sh"
```

---

### `report`

**Purpose**: Generate cost digest reports with trend analysis

**Syntax**:
```bash
crashlens report LOGFILE [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `LOGFILE` | Path | Required | Path to JSONL log file |
| `--output` | Choice | `markdown` | Output format: `markdown`, `slack` |
| `--webhook-url` | String | `$CRASHLENS_SLACK_WEBHOOK` | Slack webhook URL |
| `--email` | String | None | Email address for report delivery |
| `--attach-html` | Path | None | Path to HTML attachment |
| `--previous-logs` | Path | None | Previous logs for trend comparison |

#### Examples

```bash
# Markdown report to stdout
crashlens report logs.jsonl

# Send to Slack
crashlens report logs.jsonl --output slack --webhook-url $SLACK_WEBHOOK

# Email report
crashlens report logs.jsonl --email team@company.com

# With trend analysis
crashlens report current.jsonl --previous-logs last-week.jsonl

# Email with HTML attachment
crashlens report logs.jsonl \
  --email cfo@company.com \
  --attach-html detailed-report.html
```

---

### `simulate`

**Purpose**: Generate realistic Langfuse-style test data for policy testing

**Syntax**:
```bash
crashlens simulate --output FILE [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | Path | Required | Path to write JSONL file |
| `--count` | Int | 100 | Number of traces to generate |
| `--scenario` | Choice | `normal` | Scenario: `normal`, `retry-loop`, `model-overkill`, `slow`, `mixed-errors` |
| `--models` | String | (common models) | Comma-separated list of model names |
| `--error-rate` | Float | 0.2 | Probability of generating errors (0-1) |
| `--seed` | Int | None | Random seed for deterministic output |
| `--force` | Flag | False | Overwrite existing file without prompting |
| `--open` | Flag | False | Run `guard` on generated file after creation |

#### Examples

```bash
# Basic generation
crashlens simulate --output test.jsonl --count 500

# Retry loop scenario
crashlens simulate --output retry-test.jsonl \
  --scenario retry-loop \
  --count 200

# Deterministic output
crashlens simulate --output deterministic.jsonl --seed 42

# Generate and test
crashlens simulate --output test.jsonl --scenario mixed-errors --open

# High error rate
crashlens simulate --output errors.jsonl \
  --scenario slow \
  --error-rate 0.5 \
  --force
```

---

## Data Source Commands

### `fetch-langfuse`

**Purpose**: Fetch traces from Langfuse API and optionally analyze them

**Syntax**:
```bash
crashlens fetch-langfuse [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--hours-back` | Int | 24 | Hours back to fetch traces |
| `--limit` | Int | 1000 | Maximum number of traces |
| `--output` | Path | None | Save to file (if not provided, analyze directly) |
| `--analyze` | Flag | False | Analyze fetched traces immediately |
| `--public-key` | String | `$LANGFUSE_PUBLIC_KEY` | Langfuse public key |
| `--secret-key` | String | `$LANGFUSE_SECRET_KEY` | Langfuse secret key |
| `--base-url` | String | `$LANGFUSE_HOST` | Langfuse base URL |

#### Examples

```bash
# Fetch last 24h and analyze
crashlens fetch-langfuse

# Fetch 48 hours
crashlens fetch-langfuse --hours-back 48

# Save to file
crashlens fetch-langfuse --output logs.jsonl

# Fetch 500 and analyze
crashlens fetch-langfuse --analyze --limit 500

# Custom credentials
crashlens fetch-langfuse \
  --public-key pk-xxx \
  --secret-key sk-xxx \
  --base-url https://cloud.langfuse.com
```

---

### `fetch-helicone`

**Purpose**: Fetch requests from Helicone API and optionally analyze them

**Syntax**:
```bash
crashlens fetch-helicone [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--hours-back` | Int | 24 | Hours back to fetch requests |
| `--limit` | Int | 1000 | Maximum number of requests |
| `--output` | Path | None | Save to file (if not provided, analyze directly) |
| `--analyze` | Flag | False | Analyze fetched requests immediately |
| `--api-key` | String | `$HELICONE_API_KEY` | Helicone API key |
| `--base-url` | String | (production) | Helicone base URL |

#### Examples

```bash
# Fetch last 24h and analyze
crashlens fetch-helicone

# Fetch 48 hours
crashlens fetch-helicone --hours-back 48

# Save to file
crashlens fetch-helicone --output logs.jsonl --limit 500
```

---

## PII Commands

### `pii-remove`

**Purpose**: Remove personally identifiable information from JSONL logs

**Syntax**:
```bash
crashlens pii-remove INPUT [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `INPUT` | Path | Required | Input JSONL file |
| `--output` | Path | `<input>-cleaned.jsonl` | Output file path |
| `--types` | String | `all` | PII types: `email`, `phone`, `ssn`, `credit-card`, `ip`, `all` |
| `--dry-run` | Flag | False | Show what would be removed without writing |

#### Examples

```bash
# Remove all PII types
crashlens pii-remove logs.jsonl

# Remove specific types
crashlens pii-remove logs.jsonl --types email,phone

# Custom output
crashlens pii-remove logs.jsonl --output clean.jsonl

# Dry run (preview)
crashlens pii-remove logs.jsonl --dry-run
```

---

### `pii-clean`

**Purpose**: Alias for `pii-remove` (same functionality)

**Syntax**:
```bash
crashlens pii-clean INPUT [OPTIONS]
```

Same options as `pii-remove`.

---

## Configuration Commands

### `init`

**Purpose**: Interactive setup wizard to initialize CrashLens configuration

**Syntax**:
```bash
crashlens init [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--non-interactive` | Flag | False | Run in non-interactive mode (uses env vars) |
| `--dry-run-workflow` | Flag | False | Print workflow YAML instead of writing to disk |

#### Interactive Prompts

1. **Policy Templates**: Which templates to use?
2. **Severity Threshold**: Minimum severity level
3. **Fail on Violations**: Should CI fail on violations?
4. **Logs Source**: local, langfuse, helicone, other
5. **GitHub Actions**: Generate workflow file?

#### Environment Variables (Non-Interactive Mode)

| Variable | Default | Description |
|----------|---------|-------------|
| `CRASHLENS_TEMPLATES` | `all` | Comma-separated template names |
| `CRASHLENS_SEVERITY` | `high` | Severity threshold |
| `CRASHLENS_FAIL_ON_VIOLATIONS` | `true` | Fail on violations |
| `CRASHLENS_LOGS_SOURCE` | `local` | Logs source type |
| `CRASHLENS_CREATE_WORKFLOW` | `false` | Create GitHub workflow |

#### Examples

```bash
# Interactive mode
crashlens init

# Non-interactive for CI
export CRASHLENS_TEMPLATES="retry-loop-prevention,model-overkill-detection"
export CRASHLENS_SEVERITY=high
export CRASHLENS_FAIL_ON_VIOLATIONS=true
crashlens init --non-interactive

# Print workflow without writing
crashlens init --dry-run-workflow
```

---

### `config smtp-example`

**Purpose**: Generate example SMTP configuration file for email reports

**Syntax**:
```bash
crashlens config smtp-example [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--output` | Path | `.crashlens/smtp.yaml` | Output path for config file |

#### Examples

```bash
# Generate example config
crashlens config smtp-example

# Custom path
crashlens config smtp-example --output my-smtp.yaml
```

---

### `validate-metrics-config`

**Purpose**: Validate a metrics configuration file

**Syntax**:
```bash
crashlens validate-metrics-config FILE
```

#### Examples

```bash
crashlens validate-metrics-config metrics-config.yaml
```

---

### `show-metrics-config`

**Purpose**: Display current metrics configuration with resolved values

**Syntax**:
```bash
crashlens show-metrics-config
```

Shows effective configuration from environment variables and defaults.

---

## Utility Commands

### `list-policy-templates`

**Purpose**: List all available built-in policy templates

**Syntax**:
```bash
crashlens list-policy-templates
```

#### Output

Lists templates with descriptions:
- `retry-loop-prevention`
- `model-overkill-detection`
- `fallback-storm-detection`
- `chain-recursion-prevention`
- `budget-protection`
- `rate-limit-management`
- etc.

---

## Slack Integration

### `slack notify`

**Purpose**: Send CrashLens report to Slack via webhook

**Syntax**:
```bash
crashlens slack notify [OPTIONS]
```

#### Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--webhook-url` | String | `$CRASHLENS_SLACK_WEBHOOK` | Slack webhook URL |
| `--report-file` | Path | `report.md` | Path to report file |

#### Examples

```bash
# Send report
crashlens slack notify --webhook-url $SLACK_WEBHOOK

# Custom report file
crashlens slack notify \
  --webhook-url $SLACK_WEBHOOK \
  --report-file custom-report.md
```

---

## Environment Variables

### Authentication

| Variable | Used By | Description |
|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | `fetch-langfuse` | Langfuse public API key |
| `LANGFUSE_SECRET_KEY` | `fetch-langfuse` | Langfuse secret API key |
| `LANGFUSE_HOST` | `fetch-langfuse` | Langfuse base URL |
| `HELICONE_API_KEY` | `fetch-helicone` | Helicone API key |

### Notifications

| Variable | Used By | Description |
|----------|---------|-------------|
| `CRASHLENS_SLACK_WEBHOOK` | `slack notify`, `report` | Slack webhook URL |
| `SMTP_SERVER` | `report` | SMTP server hostname |
| `SMTP_PORT` | `report` | SMTP server port |
| `SMTP_USERNAME` | `report` | SMTP username |
| `SMTP_PASSWORD` | `report` | SMTP password |
| `SMTP_FROM` | `report` | Email sender address |
| `SMTP_USE_TLS` | `report` | Enable TLS (true/false) |

### Metrics (Prometheus)

| Variable | Used By | Description |
|----------|---------|-------------|
| `CRASHLENS_PUSH_METRICS` | `scan`, `guard` | Enable metrics push |
| `CRASHLENS_PUSHGATEWAY` | `guard` | Pushgateway URL (guard only) |
| `CRASHLENS_PUSHGATEWAY_URL` | `scan` | Pushgateway URL (scan only) |
| `CRASHLENS_METRICS_JOB` | `scan`, `guard` | Job name for metrics |
| `CRASHLENS_METRICS_MAX_RULES` | `scan` | Max unique rule names |
| `CRASHLENS_METRICS_SAMPLE_RATE` | `scan` | Sampling rate (0.0-1.0) |
| `CRASHLENS_METRICS_HTTP` | `scan` | Enable HTTP server |
| `CRASHLENS_METRICS_PORT` | `scan` | HTTP server port |
| `CRASHLENS_METRICS_ADDR` | `scan` | HTTP server bind address |
| `CRASHLENS_METRICS_AUTH_USER` | `scan` | HTTP basic auth username |
| `CRASHLENS_METRICS_AUTH_PASS` | `scan` | HTTP basic auth password |
| `CRASHLENS_ALLOW_HTTP_METRICS` | `scan` | Allow HTTP metrics (security) |
| `CRASHLENS_SKIP_TTY_CHECK` | `scan` | Skip TTY check for CI |

### Configuration (init command)

| Variable | Used By | Description |
|----------|---------|-------------|
| `CRASHLENS_TEMPLATES` | `init` | Policy templates (comma-separated) |
| `CRASHLENS_SEVERITY` | `init` | Severity threshold |
| `CRASHLENS_FAIL_ON_VIOLATIONS` | `init` | Fail on violations (true/false) |
| `CRASHLENS_LOGS_SOURCE` | `init` | Logs source type |
| `CRASHLENS_CREATE_WORKFLOW` | `init` | Create GitHub workflow |

---

## Exit Codes

| Code | Meaning | When |
|------|---------|------|
| `0` | Success | No errors, or violations found but not failing |
| `1` | General error | File not found, invalid config, API error |
| `2` | Policy violations | `guard` with `--fail-on-violations` and violations found |

---

## Common Workflows

### 1. Local Development

```bash
# Generate test data
crashlens simulate --output test.jsonl --scenario retry-loop

# Test with guard (dry run)
crashlens guard test.jsonl --rules policies/dev.yaml --dry-run

# Scan for waste
crashlens scan test.jsonl --format markdown --summary
```

### 2. CI/CD Pipeline

```bash
# Fetch from Langfuse
crashlens fetch-langfuse --hours-back 24 --output logs.jsonl

# Run guard (fail on violations)
crashlens guard logs.jsonl \
  --rules .crashlens/rules.yaml \
  --fail-on-violations \
  --push-metrics \
  --output json

# Send report to Slack
crashlens slack notify --webhook-url $SLACK_WEBHOOK
```

### 3. Production Monitoring

```bash
# Fetch logs
crashlens fetch-langfuse --hours-back 168 --limit 10000 --output weekly.jsonl

# Generate report with trends
crashlens report weekly.jsonl \
  --previous-logs last-week.jsonl \
  --email finance@company.com

# Scan with metrics
crashlens scan weekly.jsonl \
  --format json \
  --policy-template all \
  --detailed \
  --push-metrics \
  --pushgateway-url http://pushgateway.prod:9091
```

### 4. Privacy-Safe Analysis

```bash
# Remove PII
crashlens pii-remove sensitive-logs.jsonl --output clean-logs.jsonl

# Scan with privacy options
crashlens scan clean-logs.jsonl \
  --format json \
  --summary-only \
  --report-dir safe-reports/

# Guard with content filtering
crashlens guard clean-logs.jsonl \
  --no-content \
  --strip-pii \
  --summary-only
```

---

## Tips & Best Practices

### Performance

- Use `--metrics-sample-rate 0.1` in high-volume production (10% sampling)
- Use `--log-paths` with specific patterns to avoid scanning unnecessary files
- Enable `--summary-only` to reduce report size

### Security

- Never expose `--metrics-addr 0.0.0.0` without authentication
- Use `--strip-pii` for external sharing
- Store API keys in environment variables, not CLI flags
- Use `--no-content` in CI logs to avoid leaking sensitive data

### CI/CD

- Always use `--fail-on-violations` in production pipelines
- Set `--severity` appropriately per environment (fatal for prod, error for staging)
- Use `--suppress` for temporary exemptions during migrations
- Enable `--push-metrics` for observability

### Policy Management

- Start with built-in templates via `--policy-template`
- Use `--suppress` for gradual rollout of new rules
- Test policies with `simulate` before deploying
- Version control your `rules.yaml` files

---

## Quick Reference

```bash
# Most common commands
crashlens scan logs.jsonl                          # Basic scan
crashlens guard logs.jsonl --rules rules.yaml     # Policy check
crashlens fetch-langfuse                           # Fetch and analyze
crashlens simulate --output test.jsonl            # Generate test data
crashlens init                                     # Setup wizard
crashlens --help                                   # Get help

# Useful flags
--format json|markdown|slack|text                 # Output format
--dry-run                                          # Preview without failing
--push-metrics                                     # Enable Prometheus
--strip-pii                                        # Remove sensitive data
--fail-on-violations                              # CI gate
--summary-only                                     # Safe sharing
```

---

**Documentation**:
- Full User Manual: `docs/USER_MANUAL.md`
- Command Reference: `docs/COMMAND-REFERENCE.md`
- Prometheus Setup: `PROMETHEUS_INTEGRATION.md`
- GitHub: https://github.com/Crashlens/crashlens

**Support**: Create issues at https://github.com/Crashlens/crashlens/issues
