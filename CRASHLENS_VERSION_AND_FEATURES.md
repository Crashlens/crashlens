# 🧠 CrashLens - Version & Features Overview

**Current Version:** `2.9.22`

**Last Updated:** January 2025

---

## 📋 Table of Contents

- [Version Information](#-version-information)
- [What is CrashLens?](#-what-is-crashlens)
- [Core Features](#-core-features)
- [CLI Commands](#-cli-commands)
- [Detection Capabilities](#-detection-capabilities)
- [Policy & Compliance](#-policy--compliance)
- [Observability & Monitoring](#-observability--monitoring)
- [Integration Options](#-integration-options)
- [Output Formats](#-output-formats)
- [Privacy & Security](#-privacy--security)
- [Technology Stack](#-technology-stack)

---

## 📌 Version Information

### Current Release: **v2.9.22**

**Release Type:** Stable Production Release  
**Python Support:** 3.12+  
**License:** MIT  
**Package Manager:** Poetry  

### Recent Version History

#### v2.9.21 (October 2025)
- Boolean logic for policy rules (AND, OR, NOT composition)
- Guard command enhancements (`--dry-run`, `--summary-only`)
- Recursive condition evaluation support
- 54 new tests for boolean logic validation

#### v2.9.20 (October 2025)
- Prometheus & Grafana integration (8 metrics, 12-panel dashboard)
- HTTP server mode for metrics scraping
- Per-rule sampling system for performance
- 5 Prometheus alert rules
- Guard critical fixes (schema validation, duplicate rule detection)
- PII detection enhancements
- Dynamic example limits via environment variables

---

## 🎯 What is CrashLens?

CrashLens is a **privacy-first AI token waste detection CLI tool** that analyzes LLM API logs (OpenAI, Anthropic, Langfuse, Helicone) to identify and prevent costly patterns in production.

### Key Value Propositions

- **💰 Cost Savings**: Identify 40-60% potential savings in AI spending
- **🔒 Privacy First**: 100% local analysis, no data egress
- **⚡ Production Ready**: Battle-tested policy engine with CI/CD integration
- **🎯 Actionable Insights**: Specific recommendations, not just analytics
- **📊 Observable**: Prometheus metrics + Grafana dashboards
- **🛡️ Compliance Ready**: Policy enforcement for governance

---

## 🚀 Core Features

### 1. 🕵️ Intelligent Waste Detection

CrashLens includes **4 production-grade detectors** with priority-based suppression:

#### **Retry Loop Detector** (Priority 1)
- Detects identical prompts retried multiple times
- Identifies exponential backoff failures
- Flags redundant API calls within time windows
- **Cost Impact**: Exact duplicate tokens × retry count

#### **Fallback Storm Detector** (Priority 2)
- Detects cascading failures across model fallbacks
- Identifies excessive fallback chains (>3 models)
- Tracks fallback patterns in time windows
- **Cost Impact**: Sum of all failed attempts before success

#### **Model Overkill Detector** (Priority 3)
- Flags expensive models used for simple tasks
- Detects GPT-4 calls generating <10 tokens
- Identifies mismatched model selection
- **Cost Impact**: Difference between expensive and suitable model

#### **Fallback Failure Detector** (Priority 4)
- Tracks failed fallback chains (all models failed)
- Identifies exhausted retry attempts
- Monitors complete failure scenarios
- **Cost Impact**: Total wasted tokens with no successful response

### 2. 🛡️ Policy Enforcement System

#### Built-in Policy Templates
- `retry-loop-prevention` - Block excessive retries
- `fallback-chain-detector` - Monitor fallback patterns
- `model-overkill-detection` - Prevent expensive model misuse
- `max-cost-per-trace` - Enforce budget limits
- `all` - Combined policy set

#### Custom Policy Features
- YAML-based rule definitions
- Boolean logic support (AND, OR, NOT)
- Severity levels: Critical, High, Medium, Low
- Dot notation for nested fields
- Regex pattern matching
- Fail-fast mode for CI/CD

#### Policy Rule Structure
```yaml
version: 1
rules:
  - id: excessive_retries
    description: "Block traces with >3 retries"
    match:
      and:
        - retry_count: ">3"
        - metadata.fallback_attempted: true
    action: fail  # fail | warn | block
    severity: critical
    suggestion: "Implement exponential backoff"
```

### 3. 📊 Analysis & Reporting

#### Report Formats
- **Markdown** - Human-readable reports with tables
- **JSON** - Structured output with 9 comprehensive sections
- **Slack** - Block Kit formatted messages
- **Summary** - Cost breakdown with aggregated metrics
- **Detailed** - Per-trace analysis with recommendations

#### Report Sections (JSON)
1. Metadata & scan information
2. Overall statistics
3. Detection summary by category
4. Cost analysis
5. Per-detection details with recommendations
6. Policy violations
7. Trace context
8. Schema validation
9. Sampling metadata

### 4. 🔗 Integration Options

#### Input Sources
- **Local Files**: JSONL files from disk
- **Standard Input**: Pipe logs via stdin
- **Clipboard**: Read JSONL data from clipboard
- **Langfuse API**: Fetch traces directly from Langfuse
- **Helicone API**: Fetch requests from Helicone
- **Glob Patterns**: Recursive scanning (`logs/**/*.jsonl`)
- **Demo Mode**: Built-in sample data for testing

#### Output Destinations
- **File System**: Local report files
- **Standard Output**: Terminal output
- **Slack Webhooks**: Real-time notifications
- **Email (SMTP)**: Email delivery with HTML attachments
- **Prometheus**: Metrics push to Pushgateway
- **HTTP Server**: Metrics endpoint for Prometheus scraping

### 5. 📈 Observability & Monitoring

#### Prometheus Metrics (8 Metrics)
- `crashlens_rule_hits_total` - Policy rule violations counter
- `crashlens_violations_total` - Total violations by severity
- `crashlens_traces_processed_total` - Trace processing counter
- `crashlens_traces_failed_total` - Failed traces with reasons
- `crashlens_decision_latency_avg_seconds` - Rule evaluation latency
- `crashlens_last_run_timestamp_seconds` - Last successful scan
- `crashlens_metrics_push_status` - Push health monitoring
- `crashlens_rule_label_overflow_total` - Cardinality protection

#### Grafana Dashboard (12 Panels)
- **Row 1**: Overview KPIs (violations, critical count, traces, failure rate)
- **Row 2**: Violations Analysis (rule hits, severity breakdown, distribution, top rules)
- **Row 3**: Performance & Health (processing rate, latency, scan status, failure reasons)
- **Features**: 5 template variables, auto-refresh, color-coded thresholds

#### Alert Rules (5 Rules)
- High critical violations (>5 in 5 minutes)
- High failure rate (>10%)
- Stale scan detection (>60 minutes)
- Slow rule evaluation (>100ms)
- Metrics push failures

### 6. 🔒 Privacy & Security

#### Privacy Features
- **100% Local Processing** - No data leaves your machine
- **PII Detection & Removal** - Scrub sensitive data
- **Summary-Only Mode** - Suppress trace IDs for sharing
- **No External API Calls** - Except user-configured integrations

#### PII Detection Patterns
- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- IP addresses
- Custom regex patterns

#### Security Features
- **HTTP Metrics**: Localhost-only by default
- **Basic Authentication**: Optional auth for metrics endpoints
- **TTY Checks**: Interactive prompts for sensitive operations
- **Schema Validation**: Prevent malformed configurations
- **Duplicate Rule Detection**: Prevent silent conflicts

---

## 🛠️ CLI Commands

### Core Commands

#### 1. `crashlens scan` - Token Waste Analysis
Analyze logs for token waste patterns with production-grade detection.

**Usage:**
```bash
crashlens scan [LOGFILE] [OPTIONS]
```

**Key Options:**
- `--format` / `-f` - Output format (slack, markdown, json)
- `--demo` - Use built-in demo data
- `--stdin` - Read from standard input
- `--paste` - Read from clipboard
- `--summary` - Show cost summary with breakdown
- `--summary-only` - Summary without trace IDs
- `--detailed` - Generate detailed per-trace JSON reports
- `--from-langfuse` - Fetch traces from Langfuse API
- `--from-helicone` - Fetch requests from Helicone API
- `--policy-template` - Use built-in policy template
- `--policy-file` - Use custom policy file
- `--log-paths` - Glob pattern for recursive scanning
- `--push-metrics` - Enable Prometheus metrics push
- `--metrics-http` - Enable HTTP server for metrics

**Examples:**
```bash
# Basic analysis
crashlens scan logs.jsonl

# Demo mode
crashlens scan --demo

# With cost summary and detailed reports
crashlens scan logs.jsonl --summary --detailed --format markdown

# Live API analysis
crashlens scan --from-langfuse --hours-back 48 --limit 500

# Policy enforcement with metrics
crashlens scan logs.jsonl --policy-template all --push-metrics
```

---

#### 2. `crashlens guard` - Policy Validation
Check logs against policy rules without running full waste detection.

**Usage:**
```bash
crashlens guard LOGFILE [OPTIONS]
```

**Key Options:**
- `--policy-template` - Built-in policy template
- `--policy-file` - Custom policy file
- `--fail-on-violations` - Exit with error on violations
- `--severity-threshold` - Minimum severity (low, medium, high, critical)

**Examples:**
```bash
# Check specific policy
crashlens guard logs.jsonl --policy-template retry-loop-prevention

# Strict enforcement for CI/CD
crashlens guard logs.jsonl --policy-template all --fail-on-violations

# Custom severity filtering
crashlens guard logs.jsonl --policy-file custom.yaml --severity-threshold high
```

---

#### 3. `crashlens guard` - Advanced Policy Enforcement
Production-grade policy enforcement with boolean logic and PII detection.

**Usage:**
```bash
crashlens guard [LOGFILE] [OPTIONS]
```

**Key Options:**
- `--rules` - Path to rules YAML file
- `--fail-on-violations` - Exit with error on violations
- `--severity-threshold` - Minimum severity to enforce
- `--dry-run` - Validate without failing (exit code 0)
- `--summary-only` - Condensed one-line-per-rule output
- `--max-examples` - Limit examples per rule (default: 5)
- `--output-format` - Output format (text, json, markdown)

**Examples:**
```bash
# Basic guard check
crashlens guard logs.jsonl --rules .crashlens/rules.yaml

# Dry run for testing
crashlens guard logs.jsonl --rules rules.yaml --dry-run --summary-only

# Production enforcement
crashlens guard logs.jsonl --rules rules.yaml --fail-on-violations --severity-threshold high
```

---

#### 4. `crashlens init` - Setup Wizard
Initialize CrashLens configuration and GitHub Actions workflow.

**Usage:**
```bash
crashlens init [OPTIONS]
```

**Key Options:**
- `--non-interactive` - Use environment variables instead of prompts
- `--dry-run-workflow` - Print workflow YAML without creating

**Environment Variables (Non-Interactive):**
- `CRASHLENS_TEMPLATES` - Policy templates (default: "retry-loop-prevention")
- `CRASHLENS_SEVERITY` - Severity threshold (default: "medium")
- `CRASHLENS_FAIL_ON_VIOLATIONS` - Fail on violations (default: "false")
- `CRASHLENS_LOGS_SOURCE` - Log source path (default: "logs/")
- `CRASHLENS_OUTPUT_FORMAT` - Report format (default: "markdown")
- `CRASHLENS_CREATE_WORKFLOW` - Create GitHub workflow (default: "true")

**Examples:**
```bash
# Interactive setup
crashlens init

# Non-interactive for CI/CD
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="medium"
crashlens init --non-interactive

# Preview workflow
crashlens init --dry-run-workflow
```

---

#### 5. `crashlens fetch-langfuse` - Langfuse Integration
Fetch traces from Langfuse API and optionally analyze them.

**Usage:**
```bash
crashlens fetch-langfuse [OPTIONS]
```

**Key Options:**
- `--hours-back` - Hours back to fetch (default: 24)
- `--limit` - Max traces to fetch (default: 1000)
- `--output` / `-o` - Save to file
- `--analyze` - Analyze fetched traces immediately
- `--public-key` - Langfuse public key (or `LANGFUSE_PUBLIC_KEY` env)
- `--secret-key` - Langfuse secret key (or `LANGFUSE_SECRET_KEY` env)
- `--base-url` - Langfuse base URL (or `LANGFUSE_HOST` env)

**Examples:**
```bash
# Fetch and analyze last 24 hours
crashlens fetch-langfuse

# Fetch last 48 hours and save
crashlens fetch-langfuse --hours-back 48 --output traces.jsonl

# Fetch limited traces and analyze
crashlens fetch-langfuse --limit 500 --analyze
```

---

#### 6. `crashlens fetch-helicone` - Helicone Integration
Fetch requests from Helicone API and optionally analyze them.

**Usage:**
```bash
crashlens fetch-helicone [OPTIONS]
```

**Key Options:**
- `--hours-back` - Hours back to fetch (default: 24)
- `--limit` - Max requests to fetch (default: 1000)
- `--output` / `-o` - Save to file
- `--analyze` - Analyze fetched requests immediately
- `--api-key` - Helicone API key (or `HELICONE_API_KEY` env)
- `--base-url` - Helicone base URL

**Examples:**
```bash
# Fetch and analyze last 24 hours
crashlens fetch-helicone

# Fetch last 48 hours and save
crashlens fetch-helicone --hours-back 48 --output requests.jsonl
```

---

#### 7. `crashlens pii-remove` - PII Sanitization
Remove personally identifiable information from logs.

**Usage:**
```bash
crashlens pii-remove [LOGFILE] [OPTIONS]
```

**Key Options:**
- `--output` / `-o` - Output file path
- `--redact-patterns` - Custom regex patterns (comma-separated)
- `--show-redactions` - Show what was redacted

**Examples:**
```bash
# Basic PII removal
crashlens pii-remove logs.jsonl --output clean-logs.jsonl

# With custom patterns
crashlens pii-remove logs.jsonl --output clean.jsonl --redact-patterns "API-\d+,SECRET_\w+"

# Show redactions
crashlens pii-remove logs.jsonl --output clean.jsonl --show-redactions
```

---

#### 8. `crashlens simulate` - Log Generation
Generate synthetic logs for testing and benchmarking.

**Usage:**
```bash
crashlens simulate [OPTIONS]
```

**Key Options:**
- `--output` / `-o` - Output file path
- `--count` - Number of log entries (default: 100)
- `--scenario` - Scenario type (retry-loop, fallback-storm, mixed)
- `--models` - Comma-separated model list
- `--include-pii` - Include PII patterns for testing

**Examples:**
```bash
# Generate 100 mixed scenario logs
crashlens simulate --output test-logs.jsonl --count 100 --scenario mixed

# Generate retry loop scenario
crashlens simulate --output retry-logs.jsonl --count 50 --scenario retry-loop
```

---

#### 9. `crashlens report` - Report Generation
Generate and send reports via multiple channels.

**Usage:**
```bash
crashlens report LOGFILE [OPTIONS]
```

**Key Options:**
- `--output` - Output format (markdown, json, slack)
- `--webhook-url` - Slack webhook URL for notifications
- `--email` - Email address for report delivery
- `--attach-html` - Attach HTML report to email
- `--previous-logs` - Compare with previous logs

**Examples:**
```bash
# Generate markdown report
crashlens report logs.jsonl --output markdown

# Send to Slack
crashlens report logs.jsonl --output slack --webhook-url $SLACK_WEBHOOK

# Email with HTML attachment
crashlens report logs.jsonl --email user@example.com --attach-html report.html
```

---

#### 10. `crashlens slack notify` - Slack Notifications
Send reports to Slack channels.

**Usage:**
```bash
crashlens slack notify [OPTIONS]
```

**Key Options:**
- `--webhook-url` - Slack webhook URL
- `--report` - Report file to send

**Examples:**
```bash
# Send report to Slack
crashlens slack notify --webhook-url $SLACK_WEBHOOK --report report.md
```

---

#### 11. `crashlens validate-metrics-config` - Metrics Validation
Validate Prometheus metrics configuration.

**Usage:**
```bash
crashlens validate-metrics-config [CONFIG_FILE]
```

**Examples:**
```bash
# Validate default config
crashlens validate-metrics-config

# Validate custom config
crashlens validate-metrics-config my-metrics-config.yaml
```

---

#### 12. `crashlens show-metrics-config` - Show Metrics Config
Display current metrics configuration.

**Usage:**
```bash
crashlens show-metrics-config [CONFIG_FILE]
```

**Examples:**
```bash
# Show default config
crashlens show-metrics-config

# Show custom config
crashlens show-metrics-config my-metrics-config.yaml
```

---

#### 13. `crashlens list-policy-templates` - List Templates
Display all available policy templates.

**Usage:**
```bash
crashlens list-policy-templates
```

---

#### 14. `crashlens config smtp-example` - SMTP Configuration
Generate example SMTP configuration file.

**Usage:**
```bash
crashlens config smtp-example [OPTIONS]
```

**Key Options:**
- `--output` - Output path (default: `.crashlens/smtp.yaml`)

---

## 🔍 Detection Capabilities

### Pattern Detection Matrix

| Pattern | Description | Priority | Typical Savings |
|---------|-------------|----------|-----------------|
| **Retry Loops** | Identical prompts retried multiple times | 1 (Highest) | 30-50% |
| **Fallback Storms** | Cascading failures across fallback chain | 2 | 20-30% |
| **Model Overkill** | Expensive models for simple tasks | 3 | 40-60% |
| **Fallback Failures** | Complete fallback chain failures | 4 | 10-20% |

### Detection Features

- **Exact String Matching** - Deterministic retry detection
- **Time Window Analysis** - Detect patterns within configurable windows
- **Exponential Backoff Detection** - Identify backoff failures
- **Model Suitability Scoring** - Match tasks to appropriate models
- **Priority-Based Suppression** - Prevent double-counting waste
- **Cost Calculation** - Exact USD impact per pattern
- **Recommendation Engine** - Actionable optimization suggestions

---

## 📊 Output Formats

### 1. Slack Format
- Block Kit formatted messages
- Color-coded severity indicators
- Collapsible sections
- Interactive buttons
- Team-friendly notifications

### 2. Markdown Format
- Human-readable tables
- Section headers and dividers
- Code blocks for trace details
- Summary statistics
- Cost breakdowns

### 3. JSON Format
**9 Comprehensive Sections:**
1. **Metadata**: Scan timestamp, version, configuration
2. **Statistics**: Total detections, cost impact, trace counts
3. **Detections Summary**: By category and severity
4. **Cost Analysis**: Per-model, per-pattern breakdown
5. **Detection Details**: Full detection objects with context
6. **Policy Violations**: Rule matches and examples
7. **Traces**: Relevant trace context
8. **Schema Info**: Validation results
9. **Sampling**: Metadata for sampled data

### 4. Summary Format
- Cost breakdown by detector
- Model usage statistics
- Severity distribution
- Top waste patterns
- Aggregated metrics

### 5. Detailed Format
- Per-trace analysis
- Individual detection reports
- Full context and recommendations
- Organized by category
- Separate JSON files per detection type

---

## 🌐 Integration Options

### CI/CD Integrations
- **GitHub Actions** - Automated workflow generation
- **Exit Codes** - Fail builds on policy violations
- **Artifact Upload** - Report storage with retention
- **Matrix Builds** - Multi-environment testing
- **Scheduled Scans** - Periodic monitoring

### Observability Platforms
- **Prometheus** - Metrics push or HTTP scraping
- **Grafana** - Pre-built dashboards
- **Alert Manager** - Alert rule definitions
- **Push Gateway** - Batch job metrics
- **HTTP Server** - Long-running service metrics

### Communication Platforms
- **Slack** - Webhook notifications
- **Email (SMTP)** - HTML email reports
- **GitHub Issues** - Automated issue creation (planned)
- **PagerDuty** - Incident management (planned)

### Data Sources
- **Langfuse** - Direct API integration
- **Helicone** - Direct API integration
- **OpenAI** - Log format support
- **Anthropic** - Log format support
- **Custom JSONL** - Generic JSONL parsing

---

## 🔒 Privacy & Security

### Privacy Guarantees
1. **Local Processing** - All analysis runs on your machine
2. **No Data Egress** - No logs sent to external services
3. **PII Detection** - Automatic sensitive data detection
4. **PII Removal** - Optional sanitization before sharing
5. **Summary Mode** - Share insights without trace IDs

### Security Features
1. **Schema Validation** - Prevent malformed configurations
2. **Duplicate Detection** - Avoid rule conflicts
3. **Localhost-Only Metrics** - HTTP server defaults to 127.0.0.1
4. **Basic Authentication** - Optional auth for metrics
5. **TTY Checks** - Interactive prompts for sensitive ops
6. **Environment Variables** - Secure credential management

### Compliance Support
1. **Audit Trails** - Provenance tracking with run IDs
2. **Report Retention** - Configurable artifact storage
3. **Rule Versioning** - Track policy changes over time
4. **Severity Escalation** - Safe rule promotion workflow
5. **Example Limits** - Prevent OOM on large logs

---

## 🛠️ Technology Stack

### Core Technologies
- **Python 3.12+** - Modern async support
- **Click 8.2.1+** - CLI framework
- **PyYAML 6.0.2+** - Configuration parsing
- **Jinja2 3.1.6+** - Template rendering
- **orjson 3.10.18+** - Fast JSON parsing
- **Rich 14.0.0+** - Terminal formatting

### Optional Dependencies
- **prometheus-client 0.20.0+** - Metrics collection
- **jsonschema 4.0.0+** - Schema validation
- **Faker 25.2.0+** - Test data generation
- **pydantic 2.12.3+** - Data validation
- **requests 2.31.0+** - HTTP client
- **pyperclip 1.8.2+** - Clipboard integration

### Development Tools
- **pytest 8.0.0+** - Testing framework
- **black 24.0.0+** - Code formatting
- **ruff 0.4.0+** - Linting
- **mypy** - Type checking
- **memory-profiler 0.61.0+** - Performance profiling
- **grafanalib 0.7.1+** - Dashboard generation

### Supported Platforms
- **Linux** - Full support
- **macOS** - Full support
- **Windows** - Full support (PowerShell & CMD)

---

## 📈 Performance Characteristics

### Benchmarks
- **Processing Speed**: <2 seconds for 1000 log entries
- **Memory Usage**: <100MB for 10,000 traces
- **Metrics Overhead**: <10% with sampling enabled
- **Rule Evaluation**: <100ns per rule (O(1) lookup)
- **Startup Time**: <500ms cold start

### Scalability
- **Log Volume**: Tested up to 1M traces
- **Rule Count**: Supports 500+ unique rules
- **Concurrent Scans**: Thread-safe operation
- **Cardinality Protection**: Overflow handling for high-cardinality labels

---

## 📚 Documentation

### Available Documentation
- `README.md` - Quick start and overview
- `COMMAND-REFERENCE.md` - Complete CLI command reference
- `WHAT_IS_CRASHLENS.md` - In-depth conceptual guide
- `QUICKSTART.md` - 5-minute getting started guide
- `USER_MANUAL.md` - Comprehensive user guide
- `GUARD.md` - Guard command documentation
- `OBSERVABILITY.md` - Prometheus/Grafana setup
- `SLACK_INTEGRATION.md` - Slack webhook setup
- `PII_REMOVAL_GUIDE.md` - Privacy and PII handling
- `CONTRIBUTING.md` - Contribution guidelines
- `CHANGELOG.md` - Version history

### Architecture Documentation
- `architecture-flow.md` - System architecture diagrams
- `DASHBOARD_IMPLEMENTATION_COMPLETE.md` - Grafana dashboard guide
- `GUARD_IMPLEMENTATION_SUMMARY.md` - Guard feature details
- `HTTP_SERVER_SECURITY.md` - Metrics server security
- `CONFIG_PRECEDENCE.md` - Configuration hierarchy

---

## 🚀 Quick Start

### Installation
```bash
pip install crashlens
```

### Basic Usage
```bash
# Demo scan
crashlens scan --demo

# Scan your logs
crashlens scan logs.jsonl

# With policy enforcement
crashlens scan logs.jsonl --policy-template all --fail-on-violations
```

### Setup
```bash
# Interactive setup
crashlens init

# Non-interactive (CI/CD)
export CRASHLENS_TEMPLATES="all"
export CRASHLENS_SEVERITY="medium"
crashlens init --non-interactive
```

### Integration
```bash
# Fetch from Langfuse and analyze
crashlens scan --from-langfuse --hours-back 24

# Enable Prometheus metrics
crashlens scan logs.jsonl --push-metrics --pushgateway-url http://localhost:9091
```

---

## 📞 Support & Community

### Resources
- **GitHub Repository**: [github.com/Crashlens/crashlens](https://github.com/Crashlens/crashlens)
- **Issue Tracker**: [github.com/Crashlens/crashlens/issues](https://github.com/Crashlens/crashlens/issues)
- **Documentation**: `docs/` directory in repository
- **Examples**: `examples/` directory for templates and samples

### Contributing
See `CONTRIBUTING.md` for contribution guidelines.

### License
MIT License - See `LICENSE` file for details.

---

## 🎯 Use Cases

### 1. Development Teams
- Catch token waste before production
- Optimize model selection in staging
- Enforce cost budgets per service
- Monitor retry patterns

### 2. DevOps & Platform Teams
- CI/CD pipeline integration
- Prometheus/Grafana monitoring
- Alerting on policy violations
- Cost attribution by team

### 3. Security & Compliance
- PII detection in logs
- Audit trail generation
- Policy enforcement
- Data governance

### 4. Cost Optimization
- Identify savings opportunities
- Track cost trends over time
- Model usage optimization
- Budget enforcement

### 5. Quality Assurance
- Detect error patterns
- Monitor fallback chains
- Validate retry strategies
- Performance testing

---

**Built with ❤️ for the AI Engineering community**

*Last updated: January 2025 | Version 2.9.22*
