# CrashLens Prometheus Integration

Complete setup guide for integrating CrashLens Guard with Prometheus metrics collection.

## 📋 Overview

CrashLens Guard can push metrics to Prometheus Pushgateway for observability:

- **Guard runs**: Total executions, success/failure rates
- **Violations**: Policy violations by rule and severity
- **Performance**: Execution duration, logs processed
- **Rules**: Active rules, evaluation counts

## 🚀 Quick Start

### 1. Install Dependencies

```bash
poetry add prometheus-client
```

### 2. Start Prometheus Stack

```bash
# Start all services (Pushgateway, Prometheus, Grafana)
docker compose up -d

# Verify services are running
docker compose ps

# Check logs
docker compose logs -f
```

### 3. Run Guard with Metrics

```bash
# Basic usage
poetry run crashlens guard fixtures/combined-logs.jsonl \
  --rules policies/retry-loop-detector.yaml \
  --push-metrics

# Custom Pushgateway URL
poetry run crashlens guard logs.jsonl \
  --rules rules.yaml \
  --push-metrics \
  --pushgateway-url http://localhost:9091 \
  --metrics-job my-guard-job
```

### 4. Verify Metrics

**Pushgateway UI**: http://localhost:9091
- See raw metrics pushed by CrashLens

**Prometheus UI**: http://localhost:9090
- Query metrics: `crashlens_guard_runs_total`
- Explore all `crashlens_*` metrics

**Grafana**: http://localhost:3000 (admin/admin)
- Import CrashLens dashboard from `dashboards/`
- Visualize metrics over time

## � Guard Integration

CrashLens Guard **automatically pushes runtime metrics** to the configured Pushgateway endpoint when `--push-metrics` is enabled. No additional code or configuration required!

### Metrics Pushed Automatically

Every Guard run records:
- **_runs_total**: Total executions (by status: success/failure, severity threshold)
- **_violations_total**: Policy violations (by rule_id, severity)
- **_logs_processed_total**: Log entries analyzed
- **_duration_seconds**: Execution time (histogram for P95/P99 calculations)
- **_latency_ms**: Evaluation latency in milliseconds
- **_last_run_timestamp**: When the last run completed
- **_active_rules**: Number of rules evaluated

### Configuration via Environment Variables

Configure Pushgateway connection using environment variables (recommended for production):

```bash
# Set Pushgateway URL
export CRASHLENS_PUSHGATEWAY=http://localhost:9091

# Set job name for metrics grouping
export CRASHLENS_METRICS_JOB=guard_production

# Run guard - will use environment variables
crashlens guard logs.jsonl --rules rules.yaml --push-metrics
```

**Priority Order**:
1. CLI flags (`--pushgateway-url`, `--metrics-job`) - highest priority
2. Environment variables (`CRASHLENS_PUSHGATEWAY`, `CRASHLENS_METRICS_JOB`)
3. Defaults (`http://localhost:9091`, `crashlens-guard`)

### CI/CD Integration

Example GitHub Actions workflow:

```yaml
env:
  CRASHLENS_PUSHGATEWAY: localhost:9091
  CRASHLENS_METRICS_JOB: guard_ci

steps:
  - name: Run Guard check
    run: |
      poetry run crashlens guard fixtures/combined-logs.jsonl \
        --rules .crashlens/rules.yaml \
        --push-metrics \
        --fail-on-violations
  
  - name: Verify metrics pushed
    run: |
      curl http://localhost:9091/metrics | grep crashlens_guard
```

See `.github/workflows/guard-metrics-test.yml` for a complete working example.

## �📊 Available Metrics

### Counters

- `crashlens_guard_runs_total{status, severity}` - Total guard executions
- `crashlens_guard_violations_total{rule_id, severity}` - Policy violations
- `crashlens_guard_logs_processed_total` - Log entries processed
- `crashlens_guard_rules_evaluated_total{rule_id}` - Rule evaluations

### Histograms

- `crashlens_guard_duration_seconds` - Execution time distribution (for P95/P99 calculations)

### Gauges

- `crashlens_guard_latency_ms` - Evaluation latency in milliseconds (latest run)
- `crashlens_guard_last_run_timestamp` - Last run timestamp
- `crashlens_guard_active_rules` - Number of active rules

## 🔧 Configuration

### Environment Variables

```bash
# Configure Pushgateway connection
export CRASHLENS_PUSHGATEWAY=http://localhost:9091
export CRASHLENS_METRICS_JOB=guard_production

# Disable metrics push temporarily
export CRASHLENS_DISABLE_METRICS=true

# Custom Pushgateway URL (legacy, prefer CRASHLENS_PUSHGATEWAY)
export CRASHLENS_PUSHGATEWAY_URL=http://custom:9091
```

### CLI Flags

```bash
--push-metrics              # Enable metrics push
--pushgateway-url URL       # Pushgateway URL (default: http://localhost:9091)
--metrics-job NAME          # Job name for grouping (default: crashlens-guard)
```

## 🐳 Docker Services

### Pushgateway (Port 9091)

Receives metrics from CrashLens Guard via HTTP push.

**Access**: http://localhost:9091

**Test**:
```bash
curl http://localhost:9091/metrics | grep crashlens
```

### Prometheus (Port 9090)

Scrapes metrics from Pushgateway every 15 seconds.

**Access**: http://localhost:9090

**Query Examples**:
```promql
# Total guard runs by status
crashlens_guard_runs_total

# Violation rate
rate(crashlens_guard_violations_total[5m])

# Average execution time
rate(crashlens_guard_duration_seconds_sum[5m]) / rate(crashlens_guard_duration_seconds_count[5m])

# Logs processed per minute
rate(crashlens_guard_logs_processed_total[1m]) * 60
```

### Grafana (Port 3000)

Visualizes Prometheus metrics in dashboards.

**Access**: http://localhost:3000
**Login**: admin / admin

**Setup Prometheus Data Source**:
1. Navigate to Configuration → Data Sources
2. Click "Add data source"
3. Select "Prometheus"
4. Set URL: `http://prometheus:9090` (Docker network)
5. Click "Save & Test"

**Import CrashLens Dashboards**:

CrashLens provides two pre-built Grafana dashboards:

1. **Guard Runtime Dashboard** (`dashboards/crashlens-guard.json`)
   - Total Guard Runs
   - Violations by Severity
   - P95 Evaluation Latency
   - Logs Processed Rate
   - Active Rules Count
   - Top Violated Rules table

2. **Policy Enforcement Dashboard** (`dashboards/crashlens-policy-enforcement.json`)
   - Comprehensive policy monitoring
   - FinOps cost tracking
   - Multi-job aggregation

**Import Steps**:
1. In Grafana, click "+" → Import
2. Click "Upload JSON file"
3. Select `dashboards/crashlens-guard.json`
4. Select Prometheus data source
5. Click "Import"
6. Repeat for `crashlens-policy-enforcement.json`

**Quick PromQL Examples**:
```promql
# Total guard runs in last hour
sum(crashlens_guard_runs_total)

# Violations by severity
sum by (severity) (crashlens_guard_violations_total)

# P95 latency
histogram_quantile(0.95, rate(crashlens_guard_duration_seconds_bucket[5m]))

# Current latency in milliseconds
crashlens_guard_latency_ms
```

## 🧪 Testing

### Test Script

Run the automated setup and verification:

```bash
# Windows PowerShell
.\setup-prometheus-integration.ps1

# Verify metrics integration
.\test-prometheus-metrics.ps1
```

### Manual Testing

```bash
# 1. Test metrics module directly
poetry run python -c "from crashlens.metrics import test_metrics; test_metrics()"

# 2. Run guard with metrics
poetry run crashlens guard fixtures/combined-logs.jsonl \
  --rules policies/retry-loop-detector.yaml \
  --push-metrics

# 3. Check Pushgateway
curl http://localhost:9091/metrics | grep crashlens_guard_runs_total

# 4. Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=crashlens_guard_runs_total'
```

## 📈 Example Queries

### Guard Performance

```promql
# Execution duration (95th percentile)
histogram_quantile(0.95, crashlens_guard_duration_seconds_bucket)

# Success rate (last hour)
sum(rate(crashlens_guard_runs_total{status="success"}[1h])) / 
sum(rate(crashlens_guard_runs_total[1h])) * 100
```

### Violation Trends

```promql
# Violations per minute by severity
sum by (severity) (rate(crashlens_guard_violations_total[1m])) * 60

# Top 5 rules with violations
topk(5, sum by (rule_id) (crashlens_guard_violations_total))
```

### Resource Usage

```promql
# Logs processed per second
rate(crashlens_guard_logs_processed_total[1m])

# Average rules per run
avg_over_time(crashlens_guard_active_rules[5m])
```

## 🔥 Troubleshooting

### Metrics Not Appearing

1. **Check Pushgateway connection**:
   ```bash
   curl http://localhost:9091/metrics
   ```

2. **Verify guard CLI flags**:
   ```bash
   poetry run crashlens guard --help | grep metrics
   ```

3. **Check Docker services**:
   ```bash
   docker compose ps
   docker compose logs pushgateway
   ```

### Permission Errors

```bash
# Windows: Run PowerShell as Administrator
# Fix volume permissions
docker compose down -v
docker compose up -d
```

### Prometheus Not Scraping

1. **Check dashboards/prometheus.yml**:
   ```yaml
   scrape_configs:
     - job_name: 'pushgateway'
       static_configs:
         - targets: ['pushgateway:9091']  # Must use Docker network name
   ```

2. **Reload Prometheus config**:
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```

3. **Check targets in Prometheus UI**:
   http://localhost:9090/targets

### Grafana Data Source Issues

1. **Prometheus URL must be**: `http://prometheus:9090` (Docker network name)
2. **Not**: `http://localhost:9090` (won't work inside container)

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Pushgateway Guide](https://prometheus.io/docs/practices/pushing/)
- [Grafana Dashboards](https://grafana.com/docs/)
- [CrashLens Metrics API](../docs/OBSERVABILITY.md)

## 🔒 Production Deployment

### Security Checklist

- [ ] Change Grafana admin password
- [ ] Enable Prometheus authentication
- [ ] Use HTTPS for all endpoints
- [ ] Restrict Pushgateway access (firewall rules)
- [ ] Set up alert rules for violations
- [ ] Configure backup for Grafana dashboards

### Scaling Considerations

- [ ] Use persistent volumes for data retention
- [ ] Configure Prometheus retention (default: 15 days)
- [ ] Set up federation for multi-cluster deployments
- [ ] Monitor Pushgateway memory usage
- [ ] Implement metrics aggregation for high-volume logs

## 🎯 Next Steps

1. **Set up alerts**: Create rules in `dashboards/crashlens-alert-rules.yml`
2. **Customize dashboard**: Import and modify Grafana dashboard
3. **CI/CD integration**: Add metrics push to CI pipeline
4. **Production deployment**: Follow security checklist above

---

**Status**: ✅ Ready for Production
**Version**: v1.0.0
**Last Updated**: 2025-11-09
