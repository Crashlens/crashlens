# Changelog

All notable changes to CrashLens will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Phase 2: Observability & Metrics (October 2025)

#### Prometheus & Grafana Integration
- **8 Prometheus metrics** for policy enforcement monitoring:
  - `crashlens_rule_hits_total`: Policy rule violations counter
  - `crashlens_violations_total`: Total violations by severity
  - `crashlens_traces_processed_total`: Trace processing counter
  - `crashlens_traces_failed_total`: Failed traces with failure reasons
  - `crashlens_decision_latency_avg_seconds`: Rule evaluation latency
  - `crashlens_last_run_timestamp_seconds`: Last successful scan timestamp
  - `crashlens_metrics_push_status`: Self-monitoring metric for push health
  - `crashlens_rule_label_overflow_total`: Cardinality protection counter

- **12-panel Grafana dashboard** (v2.0):
  - Row 1: Overview KPIs (violations, critical count, traces, failure rate)
  - Row 2: Violations Analysis (rule hits, severity breakdown, distribution, top rules)
  - Row 3: Performance & Health (processing rate, latency, scan status, failure reasons)
  - 5 template variables for dynamic filtering
  - Auto-refresh and color-coded thresholds

- **5 Prometheus alert rules**:
  - High critical violations (>5 in 5 minutes)
  - High failure rate (>10%)
  - Stale scan detection (>60 minutes)
  - Slow rule evaluation (>100ms)
  - Metrics push failures

- **Per-rule sampling system**:
  - Global sampling rate configuration (default: 10%)
  - Per-rule sampling overrides for high-value rules
  - O(1) lookup performance (<100ns)
  - YAML configuration with validation
  - CLI tools: `validate-metrics-config`, `show-metrics-config`

- **HTTP server mode** for Prometheus scraping:
  - Alternative to Pushgateway (for long-running services)
  - Localhost-only by default (security first)
  - Port range validation (1024-65535)
  - Health check endpoint
  - Graceful shutdown

- **Deployment modes**:
  - Push mode (Pushgateway) - recommended for CI/CD
  - HTTP mode (scraping) - for persistent services
  - Config file support with 5-location search

#### Performance
- 4.04% overhead with 10% sampling (validated on Linux)
- <0.1 MB memory overhead
- Zero overhead when disabled (lazy loading)
- Fire-and-forget push (non-blocking)

#### Testing
- 85 tests total (100% passing)
- 36 unit tests for metrics core
- 22 tests for per-rule sampling + CLI validation
- 16 integration tests (skip without Prometheus)
- 11 HTTP server tests

#### Documentation
- Complete observability guide (1,390 lines)
- Dashboard setup and configuration
- Alert rule examples
- Kubernetes deployment examples
- Per-rule sampling guide (180 lines)

### Added - Phase 1: Core Features (September 2025)

#### Detection System
- **Retry Loop Detector**: Identify exponential backoff failures and infinite retries
- **Fallback Storm Detector**: Detect cascade failures across fallback chains
- **Model Overkill Detector**: Flag expensive models on simple tasks
- **Fallback Failure Detector**: Track failed fallback attempts

#### Policy Engine
- YAML-based policy rules with dot notation
- Hot loop optimization (<10% overhead target)
- Policy templates: retry-loop-prevention, model-overkill-detection, fallback-chain-monitoring
- Fail-fast mode and circuit breakers
- Constant-memory stats collection

#### Output Formats
- **Markdown formatter**: Human-readable reports
- **JSON formatter**: Machine-parseable output with category breakdown
- **Slack formatter**: Block Kit messages for webhook integration

#### Privacy Features
- PII removal (emails, phones, SSNs)
- Summary-only mode (suppress trace IDs)
- Local-only processing (no external API calls except user-configured)

#### CLI Commands
- `crashlens scan`: Analyze logs for waste patterns
- `crashlens policy-check`: Validate against custom policies
- `crashlens pii-remove`: Scrub sensitive data
- `crashlens slack notify`: Send reports to Slack

#### Data Sources
- File input (JSONL)
- Stdin/pipeline support
- Clipboard integration
- Langfuse API integration
- Helicone API integration

## [2.9.12] - 2025-10-15

### Initial Release
- Core log parsing (Langfuse JSONL schema v1)
- Basic waste detection
- CLI framework with Click
- Poetry-based dependency management
- Python 3.12+ support

---

## Migration Notes

### Upgrading to Phase 2 (Observability)

**New optional dependencies:**
`bash
pip install crashlens[prometheus]
`

**New CLI flags:**
- `--push-metrics`: Enable Prometheus metrics push
- `--pushgateway-url`: Pushgateway URL (default: http://localhost:9091)
- `--http-metrics`: Enable HTTP metrics server
- `--http-metrics-port`: HTTP server port (default: 9090)

**Environment variables:**
- `CRASHLENS_PUSH_METRICS`: Enable push mode
- `CRASHLENS_PUSHGATEWAY_URL`: Pushgateway URL
- `CRASHLENS_HTTP_METRICS`: Enable HTTP mode
- `CRASHLENS_HTTP_METRICS_PORT`: HTTP port

**Backwards compatibility:**
All metrics features are opt-in. Existing workflows continue working without changes.

---

For detailed implementation notes, see [OBSERVABILITY_REPORT.md](OBSERVABILITY_REPORT.md)
