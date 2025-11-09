# CrashLens Grafana Dashboards

This directory contains production-ready Grafana dashboards and Prometheus alert rules for monitoring CrashLens policy enforcement.

## 📊 Available Dashboards

### crashlens-policy-enforcement.json

**Production-Ready Dashboard v2.0**

Comprehensive monitoring dashboard with 12 panels organized in 3 functional rows.

#### Panel Overview

**Row 1: Overview - Key Performance Indicators (4 panels)**
1. **Total Violations** (Stat) - All violations with color-coded thresholds
2. **Critical Violations** (Stat) - High-priority violations requiring immediate attention
3. **Traces Processed** (Stat) - Total successfully processed traces
4. **Failure Rate** (Gauge) - Percentage of failed trace processing

**Row 2: Violations Analysis (4 panels)**
5. **Rule Hits Rate** (Time Series) - Per-minute rule trigger rate with severity breakdown
6. **Violations by Severity** (Time Series) - Stacked bar chart showing severity distribution over time
7. **Severity Distribution** (Pie Chart) - Current violation breakdown by severity
8. **Top 10 Rules by Hit Count** (Bar Gauge) - Most frequently triggered rules

**Row 3: Trace Processing & Performance (4 panels)**
9. **Trace Processing Rate** (Time Series) - Success vs failure rates per minute
10. **Rule Evaluation Latency** (Time Series) - Average rule evaluation time (alert at >100ms)
11. **Last Scan Status** (Stat) - Time since last successful scan (alert at >60 min)
12. **Trace Failures by Reason** (Table) - Detailed breakdown of failure reasons

#### Features

✅ **5 Template Variables** for advanced filtering:
- `$job` - Filter by CrashLens job name
- `$severity` - Filter by violation severity (critical, high, medium, low)
- `$rule` - Filter by specific policy rule
- `$mode` - Filter by execution mode (scan, guard)
- `$interval` - Auto-adjusting time range for rate calculations

✅ **Alert Thresholds** on critical metrics:
- Total violations: 50 (yellow), 100 (red)
- Critical violations: 1 (orange), 5 (red)
- Failure rate: 5% (yellow), 10% (red)
- Rule latency: 50ms (yellow), 100ms (red)

✅ **Color-Coded Severity Visualization**:
- Critical: Dark Red
- High: Dark Orange
- Medium: Dark Yellow
- Low: Dark Blue

✅ **Panel Descriptions**: Every panel includes a description explaining what it monitors and alert thresholds

✅ **Optimized PromQL Queries**: Uses `$interval` variable for automatic rate window adjustment

✅ **Annotations**: Shows Prometheus alerts directly on time series graphs

✅ **Shared Crosshair**: Synchronized tooltips across all time series panels

#### Statistics

- **File Size**: 26,240 bytes
- **Total Panels**: 15 (12 data panels + 3 row headers)
- **Panel Types**: 4 timeseries, 4 stat, 1 gauge, 1 piechart, 1 bargauge, 1 table
- **Template Variables**: 5
- **Annotations**: 1 (Prometheus alerts)
- **Schema Version**: 38 (latest)

---

## 🚨 Alert Rules

### crashlens-alert-rules.yml

Prometheus alert rules for automated monitoring and alerting.

#### Available Alerts

1. **CrashLensHighCriticalViolations**
   - **Trigger**: More than 5 critical violations
   - **Duration**: 5 minutes
   - **Severity**: Critical
   - **Action**: Page on-call engineer

2. **CrashLensHighFailureRate**
   - **Trigger**: Failure rate > 10%
   - **Duration**: 10 minutes
   - **Severity**: Warning
   - **Action**: Notify team channel

3. **CrashLensScanStale**
   - **Trigger**: No successful scan in > 1 hour
   - **Duration**: 10 minutes
   - **Severity**: Warning
   - **Action**: Check scheduler/cron

4. **CrashLensSlowRuleEvaluation**
   - **Trigger**: Rule evaluation > 100ms
   - **Duration**: 5 minutes
   - **Severity**: Warning
   - **Action**: Optimize rule logic

5. **CrashLensMetricsPushFailure**
   - **Trigger**: Metrics push status = 0
   - **Duration**: 5 minutes
   - **Severity**: Info
   - **Action**: Check pushgateway connectivity

---

## 🚀 Quick Start

### 1. Prerequisites

```bash
# Install Docker (if not installed)
# Windows: https://docs.docker.com/desktop/install/windows-install/
# Mac: https://docs.docker.com/desktop/install/mac-install/
# Linux: https://docs.docker.com/engine/install/

# Verify Docker is running
docker --version
```

### 2. Start Infrastructure

```bash
# Start Pushgateway
docker run -d --name pushgateway \
  -p 9091:9091 \
  --restart unless-stopped \
  prom/pushgateway

# Start Prometheus with alert rules
docker run -d --name prometheus \
  -p 9090:9090 \
  -v $(pwd)/dashboards/crashlens-alert-rules.yml:/etc/prometheus/crashlens-alert-rules.yml \
  -v $(pwd)/dashboards/prometheus.yml:/etc/prometheus/prometheus.yml \
  --link pushgateway:pushgateway \
  --restart unless-stopped \
  prom/prometheus

# Start Grafana
docker run -d --name grafana \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  --link prometheus:prometheus \
  --restart unless-stopped \
  grafana/grafana:latest
```

### 3. Configure Grafana

1. **Access Grafana**: http://localhost:3000
2. **Login**: admin / admin (change password when prompted)
3. **Add Prometheus Data Source**:
   - Configuration → Data Sources → Add data source → Prometheus
   - URL: `http://prometheus:9090` (if linked) or `http://host.docker.internal:9090`
   - Click "Save & test" → Should show green checkmark

### 4. Import Dashboard

1. **Go to Dashboards**: Dashboards → Import
2. **Upload JSON**: Click "Upload JSON file"
3. **Select File**: `crashlens-policy-enforcement.json`
4. **Configure**:
   - Name: CrashLens Policy Enforcement (Production)
   - Folder: General (or create new folder)
   - Data Source: Select your Prometheus data source
5. **Click Import**

### 5. Test with CrashLens

```bash
# Push metrics from CrashLens
poetry run crashlens scan sample-logs/demo-logs.jsonl \
  --push-metrics \
  --pushgateway-url http://localhost:9091

# Verify metrics in Pushgateway
curl http://localhost:9091/metrics | grep crashlens

# Check Prometheus has scraped metrics
curl http://localhost:9090/api/v1/query?query=crashlens_traces_processed_total
```

### 6. Explore Dashboard

- **View Dashboard**: http://localhost:3000/dashboards
- **Use Filters**: Select job, severity, rule, or mode from top dropdowns
- **Adjust Time Range**: Use time picker in top-right (default: last 1 hour)
- **Hover for Details**: Mouse over graphs for detailed tooltips
- **Pan & Zoom**: Click and drag on time series to zoom into specific time range

---

## 🔧 Customization

### Modifying the Dashboard

1. **Edit in Grafana**:
   - Open dashboard → Click "Dashboard settings" (gear icon) → JSON Model
   - Make changes in Grafana UI
   - Export JSON via "Dashboard settings" → JSON Model → Copy to clipboard

2. **Regenerate from Script**:
   ```bash
   # Edit scripts/generate_dashboard.py
   # Then regenerate
   poetry run python scripts/generate_dashboard.py
   ```

### Adding Custom Panels

```python
# In scripts/generate_dashboard.py, add to panels list:
panels.append({
    "id": 13,
    "title": "My Custom Panel",
    "description": "Description of what this monitors",
    "type": "timeseries",
    "datasource": "Prometheus",
    "gridPos": {"h": 8, "w": 12, "x": 0, "y": row_y},
    "targets": [{
        "expr": 'my_custom_promql_query',
        "legendFormat": "{{label}}",
        "refId": "A"
    }],
    # ... panel configuration
})
```

### Customizing Alert Rules

Edit `crashlens-alert-rules.yml`:

```yaml
# Add new alert
- alert: MyCustomAlert
  expr: my_metric > threshold
  for: 5m
  labels:
    severity: warning
    component: crashlens
  annotations:
    summary: "Alert summary"
    description: "Detailed description with {{ $value }}"
```

Then reload Prometheus:
```bash
curl -X POST http://localhost:9090/-/reload
```

---

## 📊 Panel Details

### Panel 1: Total Violations (Stat)

**Purpose**: Shows total number of policy violations across all severities

**Query**:
```promql
sum(crashlens_violations_total{severity=~"$severity"})
```

**Thresholds**:
- Green: < 50 violations
- Yellow: 50-99 violations
- Red: ≥ 100 violations

**Use Case**: Quick health check - high violation count indicates policy issues or system problems

---

### Panel 5: Rule Hits Rate (Time Series)

**Purpose**: Track which rules are triggering most frequently over time

**Query**:
```promql
sum by (rule, severity) (rate(crashlens_rule_hits_total{job=~"$job", rule=~"$rule", severity=~"$severity", mode=~"$mode"}[$interval])) * 60
```

**Features**:
- Per-minute rate calculation
- Grouped by rule and severity
- Automatic interval adjustment with `$interval`
- Legend shows last, max, and mean values

**Threshold Line**:
- Yellow: 10 hits/min
- Red: 50 hits/min

**Use Case**: Identify problematic rules, detect spikes in violations, optimize policy configuration

---

### Panel 10: Rule Evaluation Latency (Time Series)

**Purpose**: Monitor performance of policy rule evaluation

**Query**:
```promql
topk(10, crashlens_decision_latency_avg_seconds{rule=~"$rule"}) * 1000
```

**Features**:
- Shows top 10 slowest rules
- Converted to milliseconds for readability
- Alert threshold at 100ms

**Thresholds**:
- Green: < 50ms (fast)
- Yellow: 50-99ms (acceptable)
- Red: ≥ 100ms (needs optimization)

**Use Case**: Identify slow rules for optimization, capacity planning, SLA monitoring

---

## 🎯 Best Practices

### Dashboard Usage

1. **Regular Monitoring**: Check dashboard at least daily in production
2. **Use Filters**: Leverage template variables to focus on specific issues
3. **Set Time Range**: Adjust based on investigation needs (last 5m, 1h, 24h, 7d)
4. **Watch Trends**: Look for patterns over time, not just point values
5. **Correlate Events**: Use shared crosshair to correlate changes across panels

### Alert Configuration

1. **Tune Thresholds**: Adjust alert thresholds based on your baseline
2. **Avoid Alert Fatigue**: Set `for` duration to prevent flapping
3. **Severity Mapping**: Critical → page, Warning → Slack, Info → log only
4. **Test Alerts**: Manually trigger alerts to verify notification routing

### Performance Optimization

1. **Use Recording Rules**: Pre-compute expensive queries
2. **Limit Time Range**: Shorter ranges = faster queries
3. **Reduce Cardinality**: Be selective with label filtering
4. **Use $interval**: Let Grafana optimize rate windows

---

## 🔍 Troubleshooting

### Dashboard Shows "No data"

**Cause**: Prometheus not scraping pushgateway or CrashLens not pushing metrics

**Fix**:
```bash
# Check pushgateway has metrics
curl http://localhost:9091/metrics | grep crashlens

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Push test metrics
poetry run crashlens scan sample-logs/demo-logs.jsonl --push-metrics
```

---

### Panels Show "N/A"

**Cause**: Query returned no data or metric doesn't exist

**Fix**:
1. Check metric name spelling in panel query
2. Verify CrashLens is recording that metric
3. Check template variable filters aren't too restrictive
4. Expand time range (top-right time picker)

---

### "Error executing query" Message

**Cause**: Invalid PromQL syntax or data source unreachable

**Fix**:
1. Test query in Prometheus UI: http://localhost:9090/graph
2. Check data source configuration in Grafana
3. Verify Prometheus is running: `docker ps | grep prometheus`
4. Check logs: `docker logs prometheus`

---

### Alerts Not Firing

**Cause**: Alert rules not loaded or threshold not met

**Fix**:
```bash
# Check alert rules in Prometheus
curl http://localhost:9090/api/v1/rules

# Verify rule file is mounted
docker exec prometheus cat /etc/prometheus/crashlens-alert-rules.yml

# Check alert status
curl http://localhost:9090/api/v1/alerts
```

---

## 📚 Additional Resources

- **CrashLens Observability Guide**: [docs/OBSERVABILITY.md](../docs/OBSERVABILITY.md)
- **Grafana Documentation**: https://grafana.com/docs/
- **Prometheus Query Examples**: https://prometheus.io/docs/prometheus/latest/querying/examples/
- **Dashboard Best Practices**: https://grafana.com/docs/grafana/latest/best-practices/

---

## 🤝 Contributing

### Reporting Dashboard Issues

Open a GitHub issue with:
- Dashboard version (check JSON file `"version"` field)
- Panel name/ID causing issues
- Expected vs actual behavior
- Screenshot if visual issue

### Suggesting Improvements

We welcome suggestions for:
- New panels
- Better PromQL queries
- Additional alert rules
- UI/UX improvements

Submit via GitHub Issues or Pull Requests.

---

**Dashboard Version**: 2.0  
**Last Updated**: October 23, 2025  
**Maintainer**: CrashLens Team
