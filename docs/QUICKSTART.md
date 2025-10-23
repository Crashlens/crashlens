# CrashLens Quick Start Guide

**Version:** 2.9.12  
**Last Updated:** October 23, 2025

## 📦 Installation

```bash
# Basic installation
pip install crashlens

# With Prometheus metrics support
pip install crashlens[prometheus]

# Interactive setup wizard
crashlens init
```

## 🚀 Common Commands

### Scan for Token Waste

```bash
# Quick demo with sample data
crashlens scan --demo

# Scan local JSONL file
crashlens scan logs.jsonl

# Output formats
crashlens scan logs.jsonl --format markdown
crashlens scan logs.jsonl --format json
crashlens scan logs.jsonl --format slack

# Save report to file
crashlens scan logs.jsonl --output report.md

# Fetch from Langfuse API
crashlens scan --from-langfuse --hours-back 24 --limit 1000
```

### Policy Enforcement

```bash
# Check against custom policy
crashlens policy-check logs.jsonl --policy-file policies/my-rules.yaml

# Use built-in policy templates
crashlens scan logs.jsonl --policy-template retry-loop-prevention

# Available templates:
#   - retry-loop-prevention
#   - model-overkill-detection
#   - fallback-chain-monitoring
#   - all (combined)
```

### PII Removal

```bash
# Remove all PII types
crashlens pii-remove logs.jsonl

# Dry run (analyze without modifying)
crashlens pii-remove logs.jsonl --dry-run

# Remove specific PII types
crashlens pii-remove logs.jsonl --types email --types phone_us

# List available PII types
crashlens pii-remove --list-types
```

### Slack Integration

```bash
# Send report to Slack
crashlens slack notify --webhook-url $SLACK_WEBHOOK --report report.md

# Scan and send directly
crashlens scan logs.jsonl --format slack | \
  crashlens slack notify --webhook-url $SLACK_WEBHOOK --stdin
```

### Prometheus Metrics

```bash
# Push metrics to Pushgateway (recommended for CI/CD)
crashlens scan logs.jsonl \
  --push-metrics \
  --pushgateway-url http://localhost:9091

# HTTP metrics server (for long-running services)
crashlens scan logs.jsonl \
  --http-metrics \
  --http-metrics-port 9090

# With per-rule sampling
crashlens scan logs.jsonl \
  --push-metrics \
  --metrics-config .crashlens/metrics.yaml
```

## 🎯 Detection Types

CrashLens automatically detects 4 types of token waste:

1. **Retry Loops**: Repeated identical failures
2. **Fallback Storms**: Cascade failures across fallback chains
3. **Model Overkill**: Expensive models on simple tasks
4. **Fallback Failures**: Failed fallback attempts

## 📊 Output Formats

### Markdown (Default)
Human-readable reports with tables, summaries, and recommendations.

### JSON
Structured output for CI/CD pipelines:
```json
{
  "summary": {
    "total_waste_cost": 12.45,
    "total_waste_tokens": 125000
  },
  "by_category": {
    "retry_loops": [...],
    "fallback_storms": [...],
    "model_overkill": [...],
    "fallback_failures": [...]
  }
}
```

### Slack
Block Kit formatted messages for Slack webhooks.

## 🔧 Configuration

### Config File Locations
CrashLens searches for configuration in this order:
1. `--config` flag (highest priority)
2. `.crashlens.yaml` (current directory)
3. `.crashlens/config.yaml`
4. `~/.crashlens/config.yaml`
5. `/etc/crashlens/config.yaml` (Linux only)

### Sample Config (`custom-pricing.yaml`)

```yaml
models:
  gpt-4:
    prompt_token_cost: 0.00003
    completion_token_cost: 0.00006
  gpt-3.5-turbo:
    prompt_token_cost: 0.0000015
    completion_token_cost: 0.000002
```

### Metrics Config (`.crashlens/metrics.yaml`)

```yaml
sampling:
  rate: 0.1  # 10% global sampling
  per_rule:
    security_violation: 1.0      # Always sample
    cost_exceeded: 1.0
    high_frequency_rule: 0.01    # 1% sampling

pushgateway:
  url: "http://localhost:9091"
  job: "crashlens-prod"
  grouping_labels:
    environment: "production"
    team: "ai-platform"

http_server:
  enabled: false
  port: 9090
  host: "127.0.0.1"
```

## 🔐 Environment Variables

```bash
# Langfuse API
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"

# Helicone API
export HELICONE_API_KEY="sk-helicone-..."

# Slack
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Prometheus
export CRASHLENS_PUSH_METRICS=true
export CRASHLENS_PUSHGATEWAY_URL="http://prometheus:9091"
```

## 📖 Additional Documentation

- **[COMMAND-REFERENCE.md](COMMAND-REFERENCE.md)** - Complete CLI reference
- **[OBSERVABILITY.md](OBSERVABILITY.md)** - Prometheus & Grafana setup
- **[PII_REMOVAL_GUIDE.md](PII_REMOVAL_GUIDE.md)** - Privacy features
- **[SLACK_INTEGRATION.md](SLACK_INTEGRATION.md)** - Slack webhook setup
- **[FILE_HANDLING_MANUAL.md](FILE_HANDLING_MANUAL.md)** - Input sources & formats
- **[NON-INTERACTIVE-GUIDE.md](NON-INTERACTIVE-GUIDE.md)** - CI/CD integration

## 🐛 Troubleshooting

### Common Issues

**Q: "No token waste detected" but I see issues in logs**
- Check log format matches Langfuse JSONL schema
- Verify `traceId` field is present
- Use `--verbose` flag for detailed parsing info

**Q: Metrics not appearing in Prometheus**
- Verify Pushgateway is running: `curl http://localhost:9091/metrics`
- Check network connectivity
- Enable verbose mode: `--verbose`

**Q: PII removal not working**
- Use `--dry-run --verbose` to see detection details
- Check PII patterns in logs match supported types
- Try specific types: `--types email --types phone_us`

### Getting Help

```bash
# Command-specific help
crashlens scan --help
crashlens policy-check --help
crashlens pii-remove --help

# Show version
crashlens --version

# Validate metrics config
crashlens validate-metrics-config .crashlens/metrics.yaml

# Show current metrics config
crashlens show-metrics-config
```

## 🎓 Examples Directory

Explore `examples/` for:
- Sample logs (`sample-logs/demo-logs.jsonl`)
- Policy templates (`policies/*.yaml`)
- Config files (`examples/custom-pricing.yaml`)
- Grafana dashboards (`dashboards/`)

## 🤝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for development setup, testing, and contribution guidelines.

## 📄 License

MIT License - See [LICENSE](../LICENSE) for details.
