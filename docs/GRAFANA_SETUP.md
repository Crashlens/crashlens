# Grafana Setup Guide for CrashLens

This guide walks you through setting up Grafana to visualize CrashLens policy enforcement metrics collected via Prometheus.

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Grafana Installation](#grafana-installation)
- [Prometheus Data Source Configuration](#prometheus-data-source-configuration)
- [Dashboard Import](#dashboard-import)
- [Dashboard Overview](#dashboard-overview)
- [Alert Configuration](#alert-configuration)
- [Customization](#customization)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before setting up Grafana, ensure you have:

- ✅ **CrashLens** installed with metrics support: `pip install crashlens[metrics]`
- ✅ **Prometheus** running and scraping CrashLens metrics (see [OBSERVABILITY.md](./OBSERVABILITY.md))
- ✅ CrashLens metrics being pushed to Pushgateway OR HTTP server exposed
- ✅ Network access to Prometheus and Grafana

**Recommended Versions**:
- Grafana: 10.0+ (schema version 38 compatible)
- Prometheus: 2.40+
- CrashLens: 2.10.0+

---

## Quick Start

**For the impatient** (5 minutes):

```bash
# 1. Start Grafana (Docker)
docker run -d -p 3000:3000 --name=grafana grafana/grafana

# 2. Open Grafana
open http://localhost:3000
# Default credentials: admin / admin

# 3. Add Prometheus data source
# Go to: Configuration → Data Sources → Add data source → Prometheus
# URL: http://prometheus:9090 (or your Prometheus URL)

# 4. Import CrashLens dashboard
# Go to: Dashboards → Import → Upload JSON file
# File: dashboards/crashlens-policy-enforcement.json

# Done! 🎉
```

---

## Grafana Installation

### Option 1: Docker (Recommended)

**Standalone Grafana**:
```bash
docker run -d \
  -p 3000:3000 \
  --name=grafana \
  -e "GF_SECURITY_ADMIN_PASSWORD=secret" \
  -e "GF_USERS_ALLOW_SIGN_UP=false" \
  grafana/grafana:latest
```

**With Docker Compose** (Grafana + Prometheus):
```yaml
# docker-compose.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  pushgateway:
    image: prom/pushgateway:latest
    ports:
      - "9091:9091"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./dashboards:/etc/grafana/provisioning/dashboards
      - ./datasources:/etc/grafana/provisioning/datasources
    depends_on:
      - prometheus

volumes:
  prometheus-data:
  grafana-data:
```

**Start the stack**:
```bash
docker-compose up -d
```

### Option 2: Native Installation

**Ubuntu/Debian**:
```bash
# Add Grafana repository
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -

# Install
sudo apt-get update
sudo apt-get install grafana

# Start service
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

**macOS** (Homebrew):
```bash
brew install grafana
brew services start grafana
```

**Windows** (Chocolatey):
```powershell
choco install grafana
```

**Verify Installation**:
```bash
# Check Grafana is running
curl http://localhost:3000/api/health
# Expected: {"commit":"...","database":"ok","version":"..."}
```

---

## Prometheus Data Source Configuration

### Step 1: Access Grafana

1. Open browser: `http://localhost:3000`
2. Login with default credentials:
   - **Username**: `admin`
   - **Password**: `admin` (you'll be prompted to change this)

### Step 2: Add Prometheus Data Source

**Via UI**:

1. Click **⚙️ Configuration** (gear icon) in left sidebar
2. Select **Data sources**
3. Click **Add data source**
4. Select **Prometheus**
5. Configure:
   ```
   Name: Prometheus
   URL: http://localhost:9090
   (or http://prometheus:9090 if using Docker Compose)
   
   Access: Server (default)
   Scrape interval: 15s
   HTTP Method: POST
   ```
6. Click **Save & Test**
7. You should see: ✅ "Data source is working"

**Via Provisioning** (Recommended for automation):

Create `datasources/prometheus.yml`:
```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      httpMethod: POST
      timeInterval: 15s
```

Mount this file in Docker Compose:
```yaml
grafana:
  volumes:
    - ./datasources:/etc/grafana/provisioning/datasources
```

### Step 3: Verify Data Source

Test the connection with a simple query:

1. Go to **Explore** (compass icon in left sidebar)
2. Select **Prometheus** data source
3. Run query: `up{job="pushgateway"}`
4. You should see metrics if Prometheus is scraping correctly

---

## Dashboard Import

CrashLens provides a pre-built Grafana dashboard with 15 panels for comprehensive policy monitoring.

### Method 1: Import via UI (Easiest)

1. **Download Dashboard JSON**:
   - From CrashLens repo: `dashboards/crashlens-policy-enforcement.json`
   - Or generate fresh: `python scripts/generate_dashboard.py`

2. **Import in Grafana**:
   - Click **+** icon in left sidebar → **Import**
   - Click **Upload JSON file**
   - Select `crashlens-policy-enforcement.json`
   - Select **Prometheus** data source
   - Click **Import**

3. **Dashboard is now available** at:
   - `http://localhost:3000/d/crashlens-policy/crashlens-policy-enforcement-production`

### Method 2: Import via API

```bash
# Using curl
curl -X POST http://admin:admin@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboards/crashlens-policy-enforcement.json

# Using Python
import requests
import json

dashboard = json.load(open('dashboards/crashlens-policy-enforcement.json'))
response = requests.post(
    'http://localhost:3000/api/dashboards/db',
    auth=('admin', 'admin'),
    json={'dashboard': dashboard, 'overwrite': True}
)
print(response.json())
```

### Method 3: Provisioning (Recommended for Production)

Create `dashboards/dashboard-provider.yml`:
```yaml
apiVersion: 1

providers:
  - name: 'CrashLens'
    orgId: 1
    folder: 'CrashLens'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
```

Mount dashboards in Docker Compose:
```yaml
grafana:
  volumes:
    - ./dashboards:/etc/grafana/provisioning/dashboards
```

Dashboard will auto-import on Grafana startup.

---

## Dashboard Overview

The CrashLens Policy Enforcement dashboard consists of **15 panels** organized in 3 rows:

### Row 1: Overview - Key Performance Indicators (KPIs)

| Panel | Type | Purpose | Alert Threshold |
|-------|------|---------|-----------------|
| **Total Violations** | Stat | Total policy violations across all severities | >100 (red) |
| **Critical Violations** | Stat | Critical severity violations requiring immediate action | >5 (red) |
| **Traces Processed** | Stat | Total traces successfully processed | - |
| **Failure Rate** | Gauge | Percentage of traces that failed processing | >10% (red) |

### Row 2: Violations Analysis

| Panel | Type | Purpose |
|-------|------|---------|
| **Rule Hits Rate** | Time Series | Rate of policy rule hits over time (per minute) |
| **Violations by Severity** | Time Series | Breakdown of violations by severity level (stacked bars) |
| **Severity Distribution** | Pie Chart | Current distribution across severity levels (donut chart) |
| **Top 10 Rules** | Bar Gauge | Most frequently triggered rules (horizontal bars) |

### Row 3: Trace Processing & Performance

| Panel | Type | Purpose |
|-------|------|---------|
| **Trace Processing Rate** | Time Series | Successful vs failed trace processing rate |
| **Rule Evaluation Latency** | Time Series | Average time to evaluate each policy rule |
| **Last Scan Status** | Stat | Time since last successful scan |
| **Failure Reasons Table** | Table | Breakdown of trace failures by reason |

### Template Variables (Filters)

The dashboard includes 5 template variables for filtering:

- **$job**: Prometheus job name (e.g., `crashlens_scan`)
- **$severity**: Violation severity (`critical`, `high`, `medium`, `low`)
- **$rule**: Specific policy rule name
- **$mode**: CrashLens mode (`push`, `http`)
- **$interval**: Time interval for rate calculations (auto, 1m, 5m, 10m, 30m, 1h)

**Usage**: Click dropdown at top of dashboard to filter data.

---

## Alert Configuration

CrashLens provides pre-configured Prometheus alert rules that integrate with Grafana annotations.

### Step 1: Load Alert Rules into Prometheus

**Alert Rules File**: `dashboards/crashlens-alert-rules.yml`

```yaml
groups:
  - name: crashlens_alerts
    interval: 30s
    rules:
      - alert: CrashLensHighCriticalViolations
        expr: sum(crashlens_violations_total{severity="critical"}) > 5
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High number of critical policy violations"
          description: "{{ $value }} critical violations detected"

      - alert: CrashLensHighFailureRate
        expr: (sum(rate(crashlens_traces_failed_total[5m])) / sum(rate(crashlens_traces_processed_total[5m]))) > 0.1
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "High trace processing failure rate"
          description: "Failure rate: {{ $value | humanizePercentage }}"

      - alert: CrashLensScanStale
        expr: time() - crashlens_last_run_timestamp_seconds{status="success"} > 3600
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CrashLens scan hasn't run recently"

      - alert: CrashLensSlowRuleEvaluation
        expr: crashlens_decision_latency_avg_seconds > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow policy rule evaluation"
```

**Add to Prometheus config** (`prometheus.yml`):
```yaml
rule_files:
  - "crashlens-alert-rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']  # Alertmanager
```

**Reload Prometheus**:
```bash
curl -X POST http://localhost:9090/-/reload
# Or restart: docker-compose restart prometheus
```

### Step 2: Configure Alertmanager (Optional)

**Install Alertmanager**:
```bash
docker run -d -p 9093:9093 \
  --name alertmanager \
  prom/alertmanager
```

**Configure notifications** (`alertmanager.yml`):
```yaml
route:
  receiver: 'slack'
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'slack'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
        channel: '#crashlens-alerts'
        title: 'CrashLens Alert: {{ .GroupLabels.alertname }}'
        text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'
```

### Step 3: View Alerts in Grafana

Alerts automatically appear as **annotations** on the dashboard:

- Red vertical lines on time series panels
- Hover to see alert details
- Click to jump to Alertmanager

**Verify annotations**:
1. Open dashboard
2. Look for red vertical lines on time series panels
3. Hover to see: "Alert: CrashLensHighCriticalViolations"

---

## Customization

### Modify Panel Queries

1. **Edit Dashboard**: Click ⚙️ icon at top → **Edit**
2. **Select Panel**: Click panel title → **Edit**
3. **Modify Query**:
   ```promql
   # Example: Filter by specific severity
   sum(crashlens_violations_total{severity="critical"})
   
   # Example: Calculate rate over 10m
   rate(crashlens_rule_hits_total[10m]) * 60
   
   # Example: Top 5 rules instead of 10
   topk(5, sum by (rule) (crashlens_rule_hits_total))
   ```
4. **Save**: Click **Apply** → **Save dashboard**

### Add Custom Panel

1. Click **Add panel** button (top right)
2. Select **Add a new panel**
3. Configure query:
   ```promql
   # Example: Average tokens wasted per trace
   sum(crashlens_tokens_wasted_total) / sum(crashlens_traces_processed_total)
   ```
4. Set visualization type (Time series, Stat, Gauge, etc.)
5. Configure thresholds and colors
6. Save panel

### Adjust Time Range

**Default**: Last 1 hour  
**Options**: 5m, 15m, 1h, 6h, 24h, 7d, 30d, custom

Change via dropdown at top right of dashboard.

### Set Auto-Refresh

Configure at top right: `Off`, `5s`, `10s`, `30s`, `1m`, `5m`, `15m`, `30m`, `1h`, `2h`, `1d`

**Recommended**: `30s` for live monitoring, `5m` for historical analysis.

### Create Dashboard Snapshot

Share dashboard without exposing Prometheus:

1. Click **Share** icon (top right)
2. Select **Snapshot** tab
3. Set expiration: 1 hour, 1 day, 1 week, never
4. Click **Publish to snapshot.raintank.io**
5. Copy snapshot URL

---

## Troubleshooting

### Problem: "No data" in panels

**Possible Causes**:
1. Prometheus not scraping CrashLens metrics
2. CrashLens not pushing/exposing metrics
3. Wrong time range selected
4. Incorrect data source configuration

**Solutions**:
```bash
# 1. Check Prometheus targets
curl http://localhost:9090/api/v1/targets
# Look for: "job=pushgateway" with state="up"

# 2. Verify metrics exist in Prometheus
curl http://localhost:9090/api/v1/query?query=crashlens_violations_total
# Should return: {"status":"success", "data":{"result":[...]}}

# 3. Check CrashLens is pushing metrics
crashlens scan sample.jsonl --push-metrics --pushgateway-url http://localhost:9091

# 4. Verify Pushgateway has metrics
curl http://localhost:9091/metrics | grep crashlens
```

### Problem: Dashboard not importing

**Error**: "Dashboard validation failed"

**Solution**:
- Ensure Grafana version ≥10.0 (schema v38 compatible)
- Check JSON syntax: `python -m json.tool dashboards/crashlens-policy-enforcement.json`
- Try importing via API instead of UI

### Problem: Annotations not showing

**Cause**: Alert rules not loaded in Prometheus

**Solution**:
```bash
# Check Prometheus has rules
curl http://localhost:9090/api/v1/rules | jq '.data.groups[] | select(.name=="crashlens_alerts")'

# Reload Prometheus config
curl -X POST http://localhost:9090/-/reload

# Verify alerts are firing
curl http://localhost:9090/api/v1/alerts
```

### Problem: Slow dashboard loading

**Causes**:
- Large time range (e.g., 30 days)
- High cardinality metrics (too many unique labels)
- Inefficient queries

**Solutions**:
```bash
# 1. Reduce time range (use 1h or 6h instead of 30d)

# 2. Enable cardinality cap in CrashLens
crashlens scan logs.jsonl --push-metrics --metrics-max-rules 500

# 3. Use recording rules in Prometheus
# Add to prometheus.yml:
groups:
  - name: crashlens_recordings
    interval: 1m
    rules:
      - record: crashlens:violations:rate5m
        expr: sum(rate(crashlens_violations_total[5m]))
```

### Problem: Template variables not working

**Symptom**: Filters don't affect panels

**Solution**:
- Verify variable name matches query: `{severity=~"$severity"}`
- Check variable type (Query, Custom, Interval)
- Test query in Explore tab first

### Problem: Metrics have wrong timestamps

**Cause**: CrashLens clock skew or timezone issues

**Solution**:
```bash
# Sync system clock
sudo ntpdate -s time.nist.gov

# Check CrashLens uses UTC
crashlens scan logs.jsonl --push-metrics --verbose
# Look for: "Pushing metrics with timestamp: ..."

# Verify Prometheus timezone
curl http://localhost:9090/api/v1/status/runtimeinfo | jq '.data.timeZone'
```

---

## Best Practices

### 1. Use Provisioning for Production

**Automate everything**:
```
grafana/
├── datasources/
│   └── prometheus.yml
├── dashboards/
│   ├── dashboard-provider.yml
│   └── crashlens-policy-enforcement.json
└── docker-compose.yml
```

**Benefits**:
- Version controlled dashboards
- Reproducible setups
- No manual clicks

### 2. Set Up Alerts

**Critical Alerts**:
- Critical violations >5 → PagerDuty
- Failure rate >10% → Slack
- Scan stale >1h → Email

**Alert Routing**:
```yaml
# alertmanager.yml
routes:
  - match:
      severity: critical
    receiver: pagerduty
  - match:
      severity: warning
    receiver: slack
```

### 3. Create Role-Based Dashboards

**For Executives** (simplified):
- Total violations (big number)
- Trend over 7 days
- Cost savings

**For Engineers** (detailed):
- All 15 panels
- Latency breakdown
- Failure reasons table

**For Security** (compliance):
- Critical violations only
- PII detection alerts
- Audit trail

### 4. Monitor Dashboard Performance

**Enable query inspector**:
- Click panel title → Inspect → Query
- Check query time (should be <1s)
- Look for slow queries

**Optimize queries**:
```promql
# Slow (scans all data)
sum(crashlens_violations_total)

# Fast (uses recording rule)
crashlens:violations:rate5m
```

### 5. Backup Dashboards

**Export via API**:
```bash
# Export all dashboards
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:3000/api/search?type=dash-db | \
  jq -r '.[].uid' | \
  xargs -I{} curl -H "Authorization: Bearer YOUR_API_KEY" \
    http://localhost:3000/api/dashboards/uid/{} > backup-{}.json
```

---

## Additional Resources

- **CrashLens Observability Guide**: [OBSERVABILITY.md](./OBSERVABILITY.md)
- **HTTP Server Security**: [HTTP_SERVER_SECURITY.md](./HTTP_SERVER_SECURITY.md)
- **Config Precedence**: [CONFIG_PRECEDENCE.md](./CONFIG_PRECEDENCE.md)
- **Grafana Documentation**: https://grafana.com/docs/
- **Prometheus Documentation**: https://prometheus.io/docs/

---

## Quick Reference

### URLs
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090
- **Pushgateway**: http://localhost:9091
- **Alertmanager**: http://localhost:9093

### Credentials (Default)
- **Grafana**: admin / admin
- **Prometheus**: No auth
- **Pushgateway**: No auth

### Key Files
- **Dashboard JSON**: `dashboards/crashlens-policy-enforcement.json`
- **Alert Rules**: `dashboards/crashlens-alert-rules.yml`
- **Example Prometheus Config**: `examples/prometheus.yml`

### Common Commands
```bash
# Generate fresh dashboard
python scripts/generate_dashboard.py

# Validate dashboard JSON
python -m json.tool dashboards/crashlens-policy-enforcement.json

# Test Prometheus connection
curl http://localhost:9090/api/v1/query?query=up

# Push metrics to test
crashlens scan sample.jsonl --push-metrics

# Restart Grafana
docker-compose restart grafana
```

---

**Need Help?**  
- GitHub Issues: https://github.com/crashlens/crashlens/issues
- Documentation: https://github.com/crashlens/crashlens/tree/main/docs
- Community: https://discord.gg/crashlens

---

**Document Version**: 1.0  
**Last Updated**: October 25, 2025  
**Compatible With**: CrashLens 2.10.0+, Grafana 10.0+, Prometheus 2.40+
