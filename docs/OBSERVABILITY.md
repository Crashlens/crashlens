# CrashLens Observability Guide

**Version:** 1.0  
**Last Updated:** October 23, 2025  
**Status:** Production Ready

---

## 📊 Overview

CrashLens provides comprehensive Prometheus metrics for monitoring AI token waste detection in production environments. This guide covers installation, configuration, metrics reference, and best practices for production deployment.

### What Can You Monitor?

- **Policy Enforcement:** Track rule hits and violations in real-time
- **Trace Processing:** Monitor success rates and failure reasons
- **Performance:** Measure rule evaluation latency and identify bottlenecks
- **System Health:** Self-monitoring of metrics push status

### Key Features

- ✅ **Zero overhead when disabled** - Lazy loading with optional dependency
- ✅ **Fire-and-forget push** - Non-blocking CLI (< 2s wait)
- ✅ **Cardinality protection** - Prevents label explosion (max 500 unique rules)
- ✅ **Graceful degradation** - Failed pushes don't crash the CLI
- ✅ **Production-ready** - Validated in Phase 0 benchmarks

---

## 🚀 Installation

### 1. Install CrashLens with Metrics Support

```bash
# Using pip
pip install crashlens[metrics]

# Using poetry
poetry add crashlens --extras metrics

# Verify installation
python -c "from prometheus_client import Counter; print('✓ Metrics support installed')"
```

### 2. Set Up Prometheus Pushgateway

CrashLens pushes metrics to Prometheus Pushgateway for aggregation.

**Docker (Recommended):**
```bash
# Start pushgateway
docker run -d \
  --name pushgateway \
  -p 9091:9091 \
  prom/pushgateway

# Verify it's running
curl http://localhost:9091/metrics
```

**Docker Compose:**
```yaml
version: '3'
services:
  pushgateway:
    image: prom/pushgateway
    ports:
      - "9091:9091"
    restart: unless-stopped
```

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pushgateway
spec:
  replicas: 1
  selector:
    matchLabels:
      app: pushgateway
  template:
    metadata:
      labels:
        app: pushgateway
    spec:
      containers:
      - name: pushgateway
        image: prom/pushgateway
        ports:
        - containerPort: 9091
---
apiVersion: v1
kind: Service
metadata:
  name: pushgateway
spec:
  ports:
  - port: 9091
    targetPort: 9091
  selector:
    app: pushgateway
```

### 3. Configure Prometheus to Scrape Pushgateway

**prometheus.yml:**
```yaml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true
    static_configs:
      - targets: ['localhost:9091']
    # Scrape every 30 seconds
    scrape_interval: 30s
```

---

## ⚙️ Configuration

### CLI Flags

```bash
crashlens scan logs.jsonl \
  --push-metrics \                      # Enable metrics push
  --pushgateway-url http://localhost:9091 \  # Pushgateway URL
  --metrics-job crashlens_scan \        # Job name for grouping
  --metrics-max-rules 500               # Max unique rule names
```

### Environment Variables

```bash
# Enable metrics
export CRASHLENS_PUSH_METRICS=true

# Configure pushgateway
export CRASHLENS_PUSHGATEWAY_URL=http://prometheus:9091

# Set job name (for grouping metrics)
export CRASHLENS_METRICS_JOB=my-app-policy-check

# Set max rules (cardinality protection)
export CRASHLENS_METRICS_MAX_RULES=1000

# Kill switch (emergency disable)
export CRASHLENS_DISABLE_METRICS=true
```

### Configuration Precedence

1. **Kill switch** - `CRASHLENS_DISABLE_METRICS=true` (highest priority)
2. **CLI flags** - `--push-metrics`, `--pushgateway-url`, etc.
3. **Environment variables** - `CRASHLENS_PUSH_METRICS`, etc.
4. **Defaults** - Disabled by default

### Example Configurations

**Development (Local):**
```bash
crashlens scan logs.jsonl \
  --push-metrics \
  --pushgateway-url http://localhost:9091
```

**Production (Kubernetes):**
```bash
export CRASHLENS_PUSH_METRICS=true
export CRASHLENS_PUSHGATEWAY_URL=http://pushgateway.monitoring.svc.cluster.local:9091
export CRASHLENS_METRICS_JOB=production-policy-scan
crashlens scan /data/logs.jsonl
```

**CI/CD (GitHub Actions):**
```yaml
- name: Run CrashLens with Metrics
  env:
    CRASHLENS_PUSH_METRICS: true
    CRASHLENS_PUSHGATEWAY_URL: ${{ secrets.PUSHGATEWAY_URL }}
    CRASHLENS_METRICS_JOB: ci-${{ github.run_id }}
  run: |
    crashlens scan logs.jsonl
```

### Advanced Sampling

**📊 Per-Rule Sampling for High-Cardinality Environments**

In high-volume environments with hundreds of policy rules, full metrics collection can create cardinality issues in Prometheus. Per-rule sampling allows you to apply different sampling rates to different rules, reducing overhead while maintaining visibility into critical issues.

#### How It Works

- **Global Rate:** Apply a default sampling rate to all rules (e.g., 10% = 0.1)
- **Per-Rule Overrides:** Override the global rate for specific rules
- **Precedence:** Per-rule rates take precedence over the global rate

#### Configuration

**CLI with Config File:**
```bash
crashlens scan logs.jsonl \
  --push-metrics \
  --metrics-config metrics.yaml
```

**Configuration File (metrics.yaml):**
```yaml
metrics:
  enabled: true
  sampling:
    rate: 0.1  # 10% sampling for most rules
    per_rule:
      # High-frequency rules - 1% sampling
      rate_limit_violation: 0.01
      prompt_too_long: 0.01
      token_count_exceeded: 0.01
      
      # Medium-frequency rules - 5% sampling
      model_overkill: 0.05
      inefficient_prompt: 0.05
      
      # Critical rules - 100% sampling (always record)
      security_breach: 1.0
      cost_overrun: 1.0
      pii_exposure: 1.0
      gdpr_violation: 1.0
      
      # Test/development rules - 50% sampling
      experimental_detector: 0.5
      
      # Disabled rules - 0% sampling (never record)
      deprecated_rule: 0.0
      noisy_rule_to_ignore: 0.0
  pushgateway:
    url: "http://localhost:9091"
    job: "crashlens-production"
```

#### Rule Frequency Guidelines

| Frequency | Hits Per Scan | Recommended Rate | Example Rules |
|-----------|---------------|------------------|---------------|
| High | >10,000 | 0.01 (1%) | `rate_limit_violation`, `prompt_too_long` |
| Frequent | 1,000-10,000 | 0.05 (5%) | `model_overkill`, `inefficient_prompt` |
| Medium | 100-1,000 | 0.2 (20%) | `retry_loop_detected`, `fallback_storm` |
| Low | <100 | 1.0 (100%) | Most rules |
| Critical | Any | 1.0 (100%) | `security_breach`, `cost_overrun`, `pii_exposure` |

#### Memory & Performance Impact

- **Per-Rule Overhead:** ~80 bytes per rule (rule name + sampling rate)
- **Lookup Overhead:** O(1) hash lookup (~10ns) + random() call (~50ns) = <100ns total
- **Memory Example:**
  - 500 rules × 80 bytes = ~40 KB
  - 1000 rules × 80 bytes = ~80 KB
- **Recommended Maximum:** 1000 unique rules

#### Migration from CLI Flags

**Before (CLI only):**
```bash
crashlens scan logs.jsonl \
  --push-metrics \
  --metrics-sample-rate 0.1  # Global 10% only
```

**After (Config file with per-rule sampling):**
```bash
crashlens scan logs.jsonl \
  --push-metrics \
  --metrics-config metrics.yaml  # Supports per-rule rates
```

#### Validation

Validate your config file before deployment:
```bash
# Check syntax and values
crashlens config validate-metrics --config metrics.yaml

# Show effective configuration
crashlens config show-metrics --config metrics.yaml
```

#### Best Practices

1. **Start Broad:** Begin with 10% global sampling, identify high-frequency rules
2. **Profile First:** Run a test scan without sampling to measure rule frequencies
3. **Critical Rules at 100%:** Always record security, compliance, and cost-critical rules
4. **Disable Noise:** Set noisy/deprecated rules to 0% to reduce cardinality
5. **Monitor Cardinality:** Track `prometheus_target_scrape_samples_scraped` metric
6. **Test Changes:** Validate config changes in dev before production

#### Example: Kubernetes Production Deployment

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: crashlens-metrics-config
  namespace: ai-monitoring
data:
  metrics.yaml: |
    metrics:
      enabled: true
      sampling:
        rate: 0.05  # 5% global rate for production
        per_rule:
          rate_limit_violation: 0.005     # 0.5% for very high-frequency
          security_breach: 1.0            # 100% for security
          cost_overrun: 1.0               # 100% for cost
          pii_exposure: 1.0               # 100% for compliance
      pushgateway:
        url: "http://prometheus-pushgateway.monitoring.svc.cluster.local:9091"
        job: "crashlens-production-team-ai"
        timeout: 10

---
# deployment.yaml (excerpt)
spec:
  containers:
  - name: crashlens
    image: crashlens:latest
    command:
    - crashlens
    - scan
    - /data/logs.jsonl
    - --push-metrics
    - --metrics-config
    - /config/metrics.yaml
    volumeMounts:
    - name: metrics-config
      mountPath: /config
  volumes:
  - name: metrics-config
    configMap:
      name: crashlens-metrics-config
```

#### Troubleshooting

**Q: How do I know which rules need lower sampling rates?**
A: Run a test scan with 100% sampling and check Grafana for rules with >1000 hits.

**Q: Does sampling affect metric accuracy?**
A: Counters remain statistically accurate with random sampling. Rate calculations are unaffected.

**Q: Can I mix CLI flags and config files?**
A: Yes! CLI flags take precedence: `--metrics-sample-rate` overrides `metrics.yaml` global rate.

**Q: How do I add a new rule without redeploying?**
A: Update the ConfigMap and the next scan will pick up changes (no restart needed for Kubernetes Jobs).

---

## 📈 Metrics Reference

### 1. crashlens_rule_hits_total

**Type:** Counter  
**Labels:** `rule`, `severity`, `mode`  
**Description:** Total number of policy rule hits

**Example:**
```promql
# Total rule hits
sum(crashlens_rule_hits_total)

# Rule hits by severity
sum by (severity) (crashlens_rule_hits_total)

# Top 10 most triggered rules
topk(10, sum by (rule) (rate(crashlens_rule_hits_total[5m])))

# High severity rule hits in last hour
sum(crashlens_rule_hits_total{severity="high"}[1h])
```

**Sample Output:**
```
crashlens_rule_hits_total{mode="scan",rule="excessive_retries",severity="high"} 42
crashlens_rule_hits_total{mode="scan",rule="model_overkill",severity="medium"} 17
crashlens_rule_hits_total{mode="policy-check",rule="max_cost",severity="critical"} 3
```

**Use Cases:**
- Track which policies are most frequently violated
- Monitor policy effectiveness over time
- Alert on sudden spikes in specific rule violations

---

### 2. crashlens_violations_total

**Type:** Counter  
**Labels:** `severity`  
**Description:** Total number of policy violations by severity level

**Example:**
```promql
# Total violations
sum(crashlens_violations_total)

# Violations by severity
sum by (severity) (crashlens_violations_total)

# Critical violations rate (per minute)
rate(crashlens_violations_total{severity="critical"}[5m]) * 60

# Percentage of high/critical violations
sum(crashlens_violations_total{severity=~"high|critical"}) 
/ sum(crashlens_violations_total) * 100
```

**Sample Output:**
```
crashlens_violations_total{severity="critical"} 5
crashlens_violations_total{severity="high"} 23
crashlens_violations_total{severity="medium"} 48
crashlens_violations_total{severity="low"} 102
```

**Use Cases:**
- Monitor overall policy compliance
- Track severity distribution
- Set up severity-based alerting thresholds

---

### 3. crashlens_traces_processed_total

**Type:** Counter  
**Description:** Total number of traces successfully processed

**Example:**
```promql
# Total traces processed
crashlens_traces_processed_total

# Traces processed per minute
rate(crashlens_traces_processed_total[5m]) * 60

# Traces processed today
increase(crashlens_traces_processed_total[24h])

# Processing rate trend (7-day moving average)
avg_over_time(rate(crashlens_traces_processed_total[5m])[7d:1h]) * 60
```

**Sample Output:**
```
crashlens_traces_processed_total 15673
```

**Use Cases:**
- Monitor processing throughput
- Capacity planning
- SLA tracking (traces per day)

---

### 4. crashlens_traces_failed_total

**Type:** Counter  
**Labels:** `reason`  
**Description:** Total number of traces that failed processing

**Example:**
```promql
# Total failed traces
sum(crashlens_traces_failed_total)

# Failures by reason
sum by (reason) (crashlens_traces_failed_total)

# Failure rate
rate(crashlens_traces_failed_total[5m]) 
/ rate(crashlens_traces_processed_total[5m])

# Top failure reasons
topk(5, sum by (reason) (crashlens_traces_failed_total))
```

**Sample Output:**
```
crashlens_traces_failed_total{reason="parse_error"} 23
crashlens_traces_failed_total{reason="missing_fields"} 8
crashlens_traces_failed_total{reason="validation_error"} 5
```

**Common Reasons:**
- `parse_error` - Invalid JSONL format
- `missing_fields` - Required fields not present
- `validation_error` - Schema validation failed
- `timeout` - Processing timeout exceeded

**Use Cases:**
- Monitor data quality issues
- Identify problematic log sources
- Alert on high failure rates

---

### 5. crashlens_decision_latency_avg_seconds

**Type:** Gauge  
**Labels:** `rule`  
**Description:** Average rule evaluation time in seconds

**Example:**
```promql
# Average latency across all rules
avg(crashlens_decision_latency_avg_seconds)

# Slowest rules
topk(10, crashlens_decision_latency_avg_seconds)

# Rules exceeding 100ms average
crashlens_decision_latency_avg_seconds > 0.1

# Latency percentiles (approximation)
histogram_quantile(0.95, 
  sum by (rule) (crashlens_decision_latency_avg_seconds))
```

**Sample Output:**
```
crashlens_decision_latency_avg_seconds{rule="excessive_retries"} 0.0023
crashlens_decision_latency_avg_seconds{rule="model_overkill"} 0.0156
crashlens_decision_latency_avg_seconds{rule="complex_regex"} 0.0891
```

**Use Cases:**
- Identify slow rules needing optimization
- Monitor performance degradation
- Capacity planning for rule processing

---

### 6. crashlens_decision_latency_max_seconds

**Type:** Gauge  
**Labels:** `rule`  
**Description:** Maximum rule evaluation time in seconds (outlier detection)

**Example:**
```promql
# Maximum latency across all rules
max(crashlens_decision_latency_max_seconds)

# Rules with high max latency (> 500ms)
crashlens_decision_latency_max_seconds > 0.5

# Ratio of max to avg (outlier detection)
crashlens_decision_latency_max_seconds 
/ crashlens_decision_latency_avg_seconds

# Rules with highest variance
topk(10, 
  crashlens_decision_latency_max_seconds 
  - crashlens_decision_latency_avg_seconds)
```

**Sample Output:**
```
crashlens_decision_latency_max_seconds{rule="excessive_retries"} 0.0089
crashlens_decision_latency_max_seconds{rule="model_overkill"} 0.0234
crashlens_decision_latency_max_seconds{rule="complex_regex"} 0.2145
```

**Use Cases:**
- Detect performance outliers
- Identify rules with inconsistent performance
- Plan for worst-case scenarios

---

### 7. crashlens_last_run_timestamp_seconds

**Type:** Gauge  
**Labels:** `status`  
**Description:** Unix timestamp of last CrashLens scan completion

**Example:**
```promql
# Time since last successful run
time() - crashlens_last_run_timestamp_seconds{status="success"}

# Alert if no run in last hour
time() - crashlens_last_run_timestamp_seconds{status="success"} > 3600

# Last run time (human-readable in Grafana)
timestamp(crashlens_last_run_timestamp_seconds{status="success"})

# Run frequency (scans per day)
changes(crashlens_last_run_timestamp_seconds{status="success"}[24h])
```

**Sample Output:**
```
crashlens_last_run_timestamp_seconds{status="success"} 1729700123.456
crashlens_last_run_timestamp_seconds{status="failure"} 1729695234.789
```

**Status Values:**
- `success` - Scan completed successfully
- `failure` - Scan failed with errors
- `partial` - Scan completed with warnings

**Use Cases:**
- Monitor job scheduling health
- Alert on missed scans
- Track scan frequency

---

### 8. crashlens_metrics_push_status

**Type:** Gauge  
**Description:** Metrics push status indicator (1=success, 0=failure)

**Example:**
```promql
# Current push status
crashlens_metrics_push_status

# Alert if metrics push failing
crashlens_metrics_push_status == 0

# Push success rate over time
avg_over_time(crashlens_metrics_push_status[1h])

# Time since last successful push
(time() - max_over_time(
  crashlens_metrics_push_status[5m] * timestamp(crashlens_metrics_push_status)
))
```

**Sample Output:**
```
crashlens_metrics_push_status 1.0  # Success
crashlens_metrics_push_status 0.0  # Failure
```

**Use Cases:**
- Self-monitor metrics system health
- Alert on metrics push failures
- Validate observability stack

---

## 📊 Grafana Setup

### Dashboard Import

**Option 1: Pre-built Dashboard (Coming Soon)**
```
Dashboard ID: TBD
Dashboard JSON: dashboards/crashlens-policy-enforcement.json
```

**Option 2: Manual Creation**

Create a new dashboard with these panels:

#### Panel 1: Policy Violations by Severity
```json
{
  "title": "Violations by Severity",
  "targets": [{
    "expr": "sum by (severity) (crashlens_violations_total)"
  }],
  "type": "piechart"
}
```

#### Panel 2: Rule Hit Rate
```json
{
  "title": "Rule Hits (per minute)",
  "targets": [{
    "expr": "sum by (rule) (rate(crashlens_rule_hits_total[5m])) * 60"
  }],
  "type": "graph"
}
```

#### Panel 3: Processing Throughput
```json
{
  "title": "Traces Processed",
  "targets": [{
    "expr": "rate(crashlens_traces_processed_total[5m]) * 60",
    "legendFormat": "Traces/min"
  }],
  "type": "graph"
}
```

#### Panel 4: Failure Rate
```json
{
  "title": "Failure Rate (%)",
  "targets": [{
    "expr": "(rate(crashlens_traces_failed_total[5m]) / rate(crashlens_traces_processed_total[5m])) * 100"
  }],
  "type": "gauge"
}
```

#### Panel 5: Rule Latency (Top 10)
```json
{
  "title": "Slowest Rules (ms)",
  "targets": [{
    "expr": "topk(10, crashlens_decision_latency_avg_seconds * 1000)"
  }],
  "type": "barchart"
}
```

### Dashboard Variables

```
# Job selector
$job = label_values(crashlens_rule_hits_total, job)

# Severity filter
$severity = label_values(crashlens_violations_total, severity)

# Time range
$__interval = auto
```

---

## 🚨 Alerting

### Example Alert Rules

**prometheus-alerts.yml:**

```yaml
groups:
  - name: crashlens_alerts
    interval: 30s
    rules:
      
      # Critical: High violation rate
      - alert: CrashLensHighViolationRate
        expr: |
          rate(crashlens_violations_total{severity="critical"}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
          component: crashlens
        annotations:
          summary: "High critical violation rate detected"
          description: "Critical violations: {{ $value | humanize }}/min"
          
      # Warning: Scan not running
      - alert: CrashLensScanStale
        expr: |
          time() - crashlens_last_run_timestamp_seconds{status="success"} > 3600
        for: 10m
        labels:
          severity: warning
          component: crashlens
        annotations:
          summary: "CrashLens scan hasn't run in over 1 hour"
          description: "Last successful scan: {{ $value | humanizeDuration }} ago"
          
      # Warning: High failure rate
      - alert: CrashLensHighFailureRate
        expr: |
          (
            rate(crashlens_traces_failed_total[5m]) 
            / rate(crashlens_traces_processed_total[5m])
          ) > 0.1
        for: 10m
        labels:
          severity: warning
          component: crashlens
        annotations:
          summary: "High trace failure rate: {{ $value | humanizePercentage }}"
          description: "Check log quality and parsing issues"
          
      # Critical: Slow rule processing
      - alert: CrashLensSlowRuleProcessing
        expr: |
          crashlens_decision_latency_avg_seconds > 0.5
        for: 5m
        labels:
          severity: warning
          component: crashlens
        annotations:
          summary: "Slow rule detected: {{ $labels.rule }}"
          description: "Average latency: {{ $value }}s (threshold: 0.5s)"
          
      # Info: Metrics push failure
      - alert: CrashLensMetricsPushFailure
        expr: |
          crashlens_metrics_push_status == 0
        for: 5m
        labels:
          severity: info
          component: crashlens
        annotations:
          summary: "Metrics push to pushgateway failing"
          description: "Check pushgateway connectivity"
```

### Alertmanager Configuration

**alertmanager.yml:**

```yaml
route:
  group_by: ['alertname', 'component']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'crashlens-team'
  
  routes:
    - match:
        component: crashlens
        severity: critical
      receiver: 'pagerduty'
      continue: true
      
    - match:
        component: crashlens
        severity: warning
      receiver: 'slack'

receivers:
  - name: 'crashlens-team'
    email_configs:
      - to: 'crashlens-alerts@example.com'
        
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/XXX'
        channel: '#crashlens-alerts'
        title: '{{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
        
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: 'YOUR_PAGERDUTY_KEY'
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Metrics Not Appearing in Prometheus

**Symptoms:**
- No `crashlens_*` metrics in Prometheus
- Queries return empty results

**Diagnostics:**
```bash
# Check if metrics are in pushgateway
curl http://localhost:9091/metrics | grep crashlens

# Check CrashLens is pushing
crashlens scan logs.jsonl --push-metrics 2>&1 | grep "Metrics pushed"

# Check prometheus scrape config
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.scrapePool=="pushgateway")'
```

**Solutions:**
1. Verify pushgateway is running: `docker ps | grep pushgateway`
2. Check `--push-metrics` flag is set
3. Verify Prometheus scrape config includes pushgateway
4. Check network connectivity: `telnet localhost 9091`

---

#### 2. "prometheus_client not available" Error

**Symptoms:**
```
RuntimeError: prometheus_client is not available. Install with: pip install crashlens[metrics]
```

**Solution:**
```bash
# Reinstall with metrics extra
pip uninstall crashlens
pip install crashlens[metrics]

# Verify
python -c "import prometheus_client; print('✓ OK')"
```

---

#### 3. Metrics Push Timeout

**Symptoms:**
- CLI hangs for 2 seconds
- Warning: "Push thread still running"

**Diagnostics:**
```bash
# Check pushgateway connectivity
curl -v http://localhost:9091/metrics

# Check logs
tail -f /tmp/crashlens-metrics.log  # Linux
tail -f %TEMP%\crashlens-metrics.log  # Windows
```

**Solutions:**
1. Increase `--metrics-max-wait` if needed (not recommended)
2. Check firewall rules
3. Verify pushgateway URL is correct
4. Use kill switch if needed: `export CRASHLENS_DISABLE_METRICS=true`

---

#### 4. Cardinality Explosion

**Symptoms:**
- High memory usage in Prometheus
- Slow query performance
- Many rules with `rule_overflow` label

**Diagnostics:**
```promql
# Check unique rule names
count(count by (rule) (crashlens_rule_hits_total))

# Check overflow events
crashlens_rule_label_overflow_total
```

**Solutions:**
1. Increase `--metrics-max-rules` if legitimate
2. Review policy rules for overly generic names
3. Consolidate similar rules
4. Use Prometheus recording rules for aggregation

---

#### 5. Metrics Not Updating

**Symptoms:**
- Same values in all metrics
- Timestamp not changing

**Diagnostics:**
```bash
# Check last run timestamp
curl http://localhost:9091/metrics | grep last_run_timestamp

# Check if CrashLens is running
ps aux | grep crashlens
```

**Solutions:**
1. Verify scans are running regularly
2. Check cron/scheduler configuration
3. Review CrashLens logs for errors

---

## 💡 Best Practices

### 1. Production Deployment

**DO:**
- ✅ Use separate pushgateway instances per environment (dev/staging/prod)
- ✅ Set appropriate `--metrics-max-rules` based on your policy count
- ✅ Monitor `crashlens_metrics_push_status` for observability health
- ✅ Use `--metrics-job` to distinguish between different scan jobs
- ✅ Set up alerting for critical violations
- ✅ Use Grafana dashboards for visualization
- ✅ Enable metrics in production only (not development)

**DON'T:**
- ❌ Use default `--metrics-max-rules` if you have >500 unique rules
- ❌ Push metrics synchronously (fire-and-forget is intentional)
- ❌ Ignore `rule_overflow` events
- ❌ Skip alerting configuration
- ❌ Share pushgateway between unrelated applications

---

### 2. Performance Optimization

**Minimize Overhead:**
```bash
# Disable metrics in dev
export CRASHLENS_DISABLE_METRICS=true

# Use appropriate job names
export CRASHLENS_METRICS_JOB="scan-$(date +%Y%m%d)"

# Increase max rules if needed
export CRASHLENS_METRICS_MAX_RULES=1000
```

**Optimize Prometheus:**
```yaml
# Reduce retention for high-cardinality metrics
- job_name: 'pushgateway'
  metric_relabel_configs:
    - source_labels: [__name__]
      regex: 'crashlens_decision_latency_.*'
      action: drop
      # OR keep with shorter retention
```

---

### 3. Security

**Pushgateway:**
```bash
# Use authentication (if supported)
export CRASHLENS_PUSHGATEWAY_URL="http://user:pass@pushgateway:9091"

# Use HTTPS in production
export CRASHLENS_PUSHGATEWAY_URL="https://pushgateway.example.com:9091"

# Restrict network access
# Only allow CrashLens instances to push metrics
```

**Prometheus:**
```yaml
# Limit scrape scope
scrape_configs:
  - job_name: 'pushgateway'
    metric_relabel_configs:
      # Only scrape crashlens_* metrics
      - source_labels: [__name__]
        regex: 'crashlens_.*'
        action: keep
```

---

### 4. CI/CD Integration

**GitHub Actions:**
```yaml
name: CrashLens Policy Scan

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install CrashLens
        run: pip install crashlens[metrics]
      
      - name: Run Scan with Metrics
        env:
          CRASHLENS_PUSH_METRICS: true
          CRASHLENS_PUSHGATEWAY_URL: ${{ secrets.PUSHGATEWAY_URL }}
          CRASHLENS_METRICS_JOB: ci-${{ github.run_id }}
        run: |
          crashlens scan logs/*.jsonl
      
      - name: Upload Report
        uses: actions/upload-artifact@v3
        with:
          name: crashlens-report
          path: reports/
```

**GitLab CI:**
```yaml
crashlens_scan:
  stage: test
  image: python:3.12
  script:
    - pip install crashlens[metrics]
    - export CRASHLENS_PUSH_METRICS=true
    - export CRASHLENS_METRICS_JOB=ci-$CI_PIPELINE_ID
    - crashlens scan logs.jsonl
  artifacts:
    paths:
      - reports/
  only:
    - main
    - schedules
```

---

## 🏗️ Architecture

### How Metrics Work Internally

#### 1. Lazy Loading
```python
# prometheus_client is NOT imported at module level
# Only imported when metrics are enabled

if push_metrics:
    # First import happens here
    from crashlens.observability import initialize_metrics
    metrics = initialize_metrics(enabled=True)
```

**Benefits:**
- Zero overhead when disabled
- No dependency issues if prometheus-client not installed
- Faster startup time

---

#### 2. Fire-and-Forget Push

```python
def push_metrics_async(gateway_url, max_wait=2.0):
    """Non-blocking push with daemon thread."""
    
    def _push_worker():
        # Actual push happens here
        push_to_gateway(gateway_url, job_name, registry)
    
    # Spawn daemon thread (won't block process exit)
    thread = threading.Thread(target=_push_worker, daemon=True)
    thread.start()
    
    # Wait maximum 2 seconds, then return
    thread.join(timeout=max_wait)
    # CLI continues even if push not complete
```

**Benefits:**
- CLI never blocks > 2 seconds
- Graceful degradation on network issues
- User experience not impacted

---

#### 3. Cardinality Protection

```python
class CrashLensMetrics:
    def __init__(self, max_rules=500):
        self.max_rules = max_rules
        self._tracked_rules = set()
    
    def _get_rule_label(self, rule_name):
        if rule_name in self._tracked_rules:
            return rule_name
        
        if len(self._tracked_rules) >= self.max_rules:
            # Hit limit, use overflow sentinel
            self.label_overflow.inc()
            return 'rule_overflow'
        
        # Track new rule
        self._tracked_rules.add(rule_name)
        return rule_name
```

**Benefits:**
- Prevents unbounded memory growth
- Protects Prometheus from cardinality explosion
- Self-monitoring via `crashlens_rule_label_overflow_total`

---

#### 4. Singleton Pattern

```python
_metrics_instance = None

def initialize_metrics(enabled=False):
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = CrashLensMetrics()
    return _metrics_instance

def get_metrics():
    return _metrics_instance
```

**Benefits:**
- Single metrics instance across CLI
- Consistent metric values
- No duplicate registrations

---

### Metrics Collection Flow

```
User Command
    ↓
CLI: scan --push-metrics
    ↓
initialize_metrics(enabled=True)
    ↓
[Lazy Import] prometheus_client
    ↓
CrashLensMetrics instance created
    ↓
PolicyEngine.enable_metrics_recording()
    ↓
[Processing Loop]
    ├─ record_rule_hit()
    ├─ record_violation()
    ├─ record_trace_processed()
    └─ update_decision_latency()
    ↓
flush_metrics()
    ↓
push_metrics_async()
    ↓
[Daemon Thread] push_to_gateway()
    ↓
Pushgateway
    ↓
Prometheus (scrapes pushgateway)
    ↓
Grafana (visualizes metrics)
```

---

## ⚡ Performance

### Overhead Benchmarks

**Phase 0 Benchmark Results:**

| Configuration | Overhead | Notes |
|--------------|----------|-------|
| **Disabled** | -7.91% | Zero impact (lazy loading) |
| **Enabled (local)** | < 2% | Fire-and-forget push |
| **Enabled (remote)** | < 5% | Network latency |
| **Max wait** | 2 seconds | Guaranteed non-blocking |

**Test Conditions:**
- 10,000 trace scan
- 50 policy rules
- Intel i7, 16GB RAM
- Local pushgateway

---

### Optimization Tips

#### 1. Reduce Metric Cardinality

**Problem:**
Too many unique rule labels → high memory usage

**Solution:**
```bash
# Increase limit if legitimate
--metrics-max-rules 1000

# OR aggregate rules in Prometheus
record: crashlens:rule_hits:by_severity
expr: sum by (severity) (rate(crashlens_rule_hits_total[5m]))
```

---

#### 2. Batch Scans

**Problem:**
Multiple small scans → frequent metric pushes

**Solution:**
```bash
# Combine multiple files
crashlens scan logs/*.jsonl --push-metrics

# Use scheduled batch jobs instead of real-time
0 */6 * * * crashlens scan /data/logs/*.jsonl --push-metrics
```

---

#### 3. Optimize Prometheus Queries

**Slow:**
```promql
# Calculates on all data points
avg(crashlens_decision_latency_avg_seconds)
```

**Fast:**
```promql
# Uses recording rule
crashlens:decision_latency:avg
```

**Recording Rule:**
```yaml
groups:
  - name: crashlens_recordings
    interval: 60s
    rules:
      - record: crashlens:decision_latency:avg
        expr: avg(crashlens_decision_latency_avg_seconds)
```

---

### Memory Usage

**Typical Memory Footprint:**

| Component | Memory | Notes |
|-----------|--------|-------|
| **CrashLens (no metrics)** | 50-100 MB | Base usage |
| **CrashLens (with metrics)** | 55-110 MB | +5-10 MB overhead |
| **prometheus-client** | 5-10 MB | Dependency |
| **Per rule tracked** | ~1 KB | 500 rules = 500 KB |

**Pushgateway Memory:**
- Base: 20-50 MB
- Per job: +1-5 MB
- Per unique label combination: +1 KB

---

## 📚 Additional Resources

### Official Documentation
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Pushgateway GitHub](https://github.com/prometheus/pushgateway)
- [Grafana Documentation](https://grafana.com/docs/)

### CrashLens Resources
- [Main README](../README.md)
- [Command Reference](COMMAND-REFERENCE.md)
- [Policy Guide](../policies/README.md)

### Community
- [GitHub Issues](https://github.com/Crashlens/crashlens/issues)
- [Discussions](https://github.com/Crashlens/crashlens/discussions)

---

## 🤝 Support

### Getting Help

1. **Check Troubleshooting section** above
2. **Review Prometheus logs:** `docker logs pushgateway`
3. **Check CrashLens logs:** `/tmp/crashlens-metrics.log`
4. **Open GitHub Issue** with:
   - CrashLens version: `crashlens --version`
   - Prometheus version
   - Error messages
   - Configuration (sanitized)

### Reporting Bugs

Include:
- Steps to reproduce
- Expected vs actual behavior
- Relevant metrics queries
- Logs (sanitized)

---

**Document Version:** 1.0  
**Last Updated:** October 23, 2025  
**Feedback:** [Open an issue](https://github.com/Crashlens/crashlens/issues)
