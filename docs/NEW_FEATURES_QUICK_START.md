# Quick Start: New CrashLens Features

This guide covers the newly implemented features in CrashLens.

---

## 📁 Report Organization

CrashLens now automatically organizes reports into structured subdirectories:

```
policy-violations/
├── reports/          # All formatted reports (MD, JSON, HTML)
├── traces/           # Raw trace data (JSONL)
├── archives/         # Old reports (organized by month)
└── README.md         # Auto-generated index
```

### Basic Usage

```bash
# Run scan (reports auto-organized)
crashlens scan logs.jsonl --format markdown

# View statistics
crashlens reports stats
📊 Report Statistics
========================================
Total Reports:  15
Total Traces:   5
Total Archives: 0

# Archive old reports (older than 30 days)
crashlens reports archive --days 30
✅ Archived 3 reports:
  - archives/2024-12/scan_2024-12-01_10-00-00.md
  - archives/2024-12/guard_2024-12-15_14-30-00.json
  - archives/2025-01/scan_2025-01-01_09-00-00.md

# Prune old archives (delete older than 90 days)
crashlens reports prune --days 90
⚠️  This will permanently delete 2 archived reports.
Continue? [y/N]: y
✅ Pruned 2 archived reports.

# Regenerate README
crashlens reports readme
✅ Generated README: policy-violations/README.md
```

### Programmatic API

```python
from pathlib import Path
from crashlens.reporters import FileOrganizer, ReportMetadata

# Initialize organizer
organizer = FileOrganizer(
    base_dir=Path("policy-violations"),
    auto_readme=True  # Auto-update README after changes
)

# Save report
report_path = organizer.save_report(
    content="# Scan Report\n...",
    format="markdown",
    report_type="scan",
    metadata=ReportMetadata(
        file_path="scan_2025-01-25.md",
        timestamp="2025-01-25T14:30:00",
        format="markdown",
        detections_count=10,
        severity_summary={"high": 3, "medium": 7},
        total_waste_cost=5.67,
        total_waste_tokens=5000,
        report_type="scan"
    )
)

# Archive old reports
archived = organizer.archive_old_reports(days=30)
print(f"Archived {len(archived)} reports")

# Prune old archives
pruned = organizer.prune_archives(days=90)
print(f"Pruned {len(pruned)} archived reports")
```

---

## 🔖 Schema Versioning

CrashLens now supports multiple log formats via a parser registry:

### Supported Formats

- **langfuse-v1** ✅ Stable - Original Langfuse JSONL format
- **langfuse-v2** ⚠️ Experimental - Enhanced Langfuse format
- **openai-v1** ⚠️ Experimental - OpenAI API response logs
- **anthropic-v1** ⚠️ Experimental - Anthropic Claude logs
- **helicone-v1** ⚠️ Experimental - Helicone proxy logs

### CLI Usage

```bash
# List supported formats
crashlens list-schemas

📋 Supported Log Formats
============================================================

✅ STABLE langfuse-v1 (v1.0.0)
  Original Langfuse JSONL format

⚠️  EXPERIMENTAL langfuse-v2 (v2.0.0)
  Enhanced Langfuse format with extended metadata

💡 Usage:
  crashlens scan logs.jsonl --log-format langfuse-v1

# Auto-detect schema
crashlens detect-schema unknown-logs.jsonl
✅ Detected schema: langfuse-v1

💡 Use this with: crashlens scan unknown-logs.jsonl --log-format langfuse-v1

# Use specific schema version
crashlens scan logs.jsonl --log-format langfuse-v1 --format json
```

### Programmatic API

```python
from pathlib import Path
from crashlens.parsers import get_parser, list_supported_formats, auto_detect_schema

# Get parser for specific format
parser = get_parser("langfuse-v1", verbose=True)
traces = parser.parse_file(Path("logs.jsonl"))

# Auto-detect format
schema_id = auto_detect_schema(Path("logs.jsonl"))
if schema_id:
    parser = get_parser(schema_id)
    traces = parser.parse_file(Path("logs.jsonl"))

# List all formats
formats = list_supported_formats(stable_only=True)
for fmt in formats:
    print(f"{fmt['schema_id']}: {fmt['description']}")
```

### Custom Parser Registration

```python
from crashlens.parsers import register_custom_parser

class MyCustomParser:
    def __init__(self, verbose=False, **kwargs):
        self.verbose = verbose
    
    def parse_file(self, file_path):
        # Your parsing logic
        return traces

# Register your parser
register_custom_parser(
    schema_id="custom-v1",
    parser_class=MyCustomParser,
    description="My custom log format",
    version="1.0.0",
    stable=True,
    verbose=True  # Default kwargs
)

# Use your parser
parser = get_parser("custom-v1")
traces = parser.parse_file(Path("my-logs.jsonl"))
```

---

## ✅ JSON Schema Validation

Validate JSON reports against JSON Schema to ensure correctness:

### CLI Usage

```bash
# Validate report
crashlens validate report.json
🔍 Validating report.json...
✅ Report is valid (v1)

# Strict validation (warnings as errors)
crashlens validate report.json --strict

# Validate with specific schema version
crashlens validate report.json --schema-version v1

# List available schemas
crashlens list-schemas
📋 Available Report Schemas
========================================
  • v1 (report-v1.json)

💡 Usage:
  crashlens validate report.json --schema-version v1
```

### Programmatic API

```python
from pathlib import Path
from crashlens.formatters.schema_validator import validate_report, validate_report_file

# Validate data
report_data = {
    "metadata": {
        "timestamp": "2025-01-25T14:30:00Z",
        "version": "1.2.3",
        "report_type": "scan"
    },
    "summary": {
        "total_detections": 10,
        "total_waste_cost": 5.67,
        "total_waste_tokens": 5000,
        "traces_processed": 100
    },
    "detections": []
}

is_valid, errors = validate_report(report_data, schema_version="v1")

if not is_valid:
    print("Validation errors:")
    for error in errors:
        print(f"  • {error}")
else:
    print("✅ Report is valid")

# Validate file
is_valid, errors = validate_report_file(Path("report.json"))
```

### Error Examples

```bash
crashlens validate bad-report.json
❌ Validation failed:
  • Missing required field 'timestamp' at metadata
  • Invalid value at summary.total_waste_cost: -5.0 is less than the minimum of 0
  • Invalid value at detections[0].severity: 'super-critical' is not one of ['critical', 'high', 'medium', 'low', 'info']
  • Value constraint violation at summary.total_detections: 'ten' is not of type 'integer'
```

---

## 📊 Probabilistic Sampling

**Note:** This feature was already fully implemented! Documentation clarified.

Reduce metrics overhead by sampling (recommended for production):

### CLI Usage

```bash
# Use 10% sampling (recommended for production)
crashlens scan logs.jsonl --metrics-sample-rate 0.1 --push-metrics

# Or via environment variable
export CRASHLENS_METRICS_SAMPLE_RATE=0.1
crashlens scan logs.jsonl --push-metrics

# With pushgateway
crashlens scan logs.jsonl \
  --metrics-sample-rate 0.1 \
  --push-metrics \
  --pushgateway-url http://localhost:9091
```

### Programmatic API

```python
from crashlens.observability import initialize_metrics

# Global sampling (10% of all metrics)
metrics = initialize_metrics(
    enabled=True,
    sample_rate=0.1  # Record 10% of metrics
)

# Per-rule sampling rates
metrics = initialize_metrics(
    enabled=True,
    sample_rate=0.1,  # Default 10%
    per_rule_rates={
        "critical_rule": 1.0,    # Always record (100%)
        "common_rule": 0.01,     # Rarely record (1%)
        "debug_rule": 0.001      # Very rarely (0.1%)
    }
)

# Record metrics (automatically sampled)
metrics.record_rule_hit(
    rule_name="critical_rule",
    severity="high",
    mode="scan"
)
# ^ This gets recorded 100% of the time (per_rule_rates override)

metrics.record_rule_hit(
    rule_name="common_rule",
    severity="medium",
    mode="scan"
)
# ^ This gets recorded 1% of the time (per_rule_rates override)

metrics.record_rule_hit(
    rule_name="unknown_rule",
    severity="low",
    mode="scan"
)
# ^ This gets recorded 10% of the time (global sample_rate)
```

### Sampling Impact

| Sample Rate | Overhead Reduction | Use Case |
|-------------|-------------------|----------|
| 1.0 (100%) | 0% | Development, debugging |
| 0.5 (50%) | ~50% | Staging environments |
| 0.1 (10%) | ~90% | Production (recommended) |
| 0.01 (1%) | ~99% | High-traffic production |

---

## 🔒 HTTP Server Security (Already Implemented)

**Note:** This feature was already fully implemented! Documentation clarified.

Expose Prometheus metrics via HTTP server with security controls:

### CLI Usage

```bash
# Enable HTTP server (requires opt-in env var)
export CRASHLENS_ALLOW_HTTP_METRICS=true
crashlens scan logs.jsonl --metrics-http --metrics-port 9090

# Localhost-only (default, secure)
crashlens scan logs.jsonl --metrics-http --metrics-addr 127.0.0.1

# Network-exposed with basic auth
crashlens scan logs.jsonl \
  --metrics-http \
  --metrics-addr 0.0.0.0 \
  --metrics-auth-user admin \
  --metrics-auth-pass secret123

# In CI/CD (skip TTY check)
export CRASHLENS_ALLOW_HTTP_METRICS=true
crashlens scan logs.jsonl \
  --metrics-http \
  --skip-tty-check
```

### Security Features

- ✅ **Opt-in required:** `CRASHLENS_ALLOW_HTTP_METRICS=true` environment variable
- ✅ **Localhost-only default:** Binds to `127.0.0.1` (not `0.0.0.0`)
- ✅ **Basic auth:** Required for non-localhost binding
- ✅ **Port range validation:** 1024-65535
- ✅ **TTY warning:** Warns in interactive terminals about risks

---

## 💬 Slack Integration (Already Implemented)

**Note:** This feature was already fully implemented! Documentation clarified.

Send reports directly to Slack webhooks:

### CLI Usage

```bash
# Send report to Slack
crashlens slack notify \
  --webhook-url https://hooks.slack.com/services/XXX \
  --report report.md

# Or via environment variable
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX
crashlens slack notify --report report.md

# Scan and send directly
crashlens scan logs.jsonl --format slack | \
  crashlens slack notify --stdin
```

### Block Kit Support

Slack messages use rich Block Kit formatting:
- **Sections** for report summary
- **Fields** for detection counts by severity
- **Dividers** for visual separation
- **Context** for metadata (timestamp, version)

---

## 🎯 Complete Workflow Example

```bash
# 1. Scan logs with specific schema
crashlens scan logs.jsonl --log-format langfuse-v1 --format json

# 2. View organized reports
crashlens reports stats
📊 Report Statistics
========================================
Total Reports:  1
Total Traces:   0
Total Archives: 0

# 3. Validate generated report
crashlens validate policy-violations/reports/scan_*.json
✅ Report is valid (v1)

# 4. Archive old reports monthly
crashlens reports archive --days 30

# 5. Send to Slack
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX
crashlens slack notify --report policy-violations/reports/scan_*.md

# 6. Use sampling for production metrics
crashlens scan logs.jsonl \
  --metrics-sample-rate 0.1 \
  --push-metrics \
  --pushgateway-url http://prometheus:9091

# 7. Prune old archives quarterly
crashlens reports prune --days 90 --confirm
```

---

## 📚 Additional Resources

- **Full Command Reference:** `docs/COMMAND-REFERENCE.md`
- **Implementation Details:** `docs/IMPLEMENTATION_COMPLETE.md`
- **API Documentation:** `docs/API_REFERENCE.md` (coming soon)
- **GitHub Issues:** Report bugs or request features

---

**Last Updated:** January 25, 2025  
**CrashLens Version:** 1.2.0+ (unreleased)
