# CrashLens Grafana Dashboard - Quick Reference Card

**Dashboard Version**: 2.0 (Production)  
**File**: `dashboards/crashlens-policy-enforcement.json`  
**Alert Rules**: `dashboards/crashlens-alert-rules.yml`

---

## 🚀 Quick Import

```bash
# 1. Start services
docker run -d -p 9091:9091 prom/pushgateway
docker run -d -p 9090:9090 -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml prom/prometheus
docker run -d -p 3000:3000 grafana/grafana

# 2. Import dashboard
# Grafana → Dashboards → Import → Upload crashlens-policy-enforcement.json

# 3. Push metrics
poetry run crashlens scan logs.jsonl --push-metrics
```

---

## 📊 Panel Quick Reference

| # | Panel Name | Type | What It Shows | Alert Threshold |
|---|------------|------|---------------|-----------------|
| 1 | Total Violations | Stat | All violations count | >100 (red) |
| 2 | Critical Violations | Stat | Critical severity count | >5 (red) |
| 3 | Traces Processed | Stat | Successfully processed | N/A |
| 4 | Failure Rate | Gauge | % of failed traces | >10% (red) |
| 5 | Rule Hits Rate | Time Series | Triggers per minute | >50/min (red) |
| 6 | Violations by Severity | Time Series | Stacked severity breakdown | N/A |
| 7 | Severity Distribution | Pie Chart | Current violation % | N/A |
| 8 | Top 10 Rules | Bar Gauge | Most triggered rules | N/A |
| 9 | Trace Processing Rate | Time Series | Success vs failure rate | N/A |
| 10 | Rule Evaluation Latency | Time Series | Rule eval time (ms) | >100ms (red) |
| 11 | Last Scan Status | Stat | Minutes since last scan | >60min (red) |
| 12 | Failure Reasons | Table | Breakdown by error type | N/A |

---

## 🎛️ Template Variables

| Variable | Purpose | Example Use |
|----------|---------|-------------|
| `$job` | Filter by job name | Focus on specific CI/CD pipeline |
| `$severity` | Filter by severity | Show only critical/high violations |
| `$rule` | Filter by rule | Debug specific policy rule |
| `$mode` | Filter by mode | Compare scan vs guard |
| `$interval` | Auto-adjust rate window | Optimizes query performance |

**Pro Tip**: Select "All" in dropdowns to see complete picture, or select specific values to drill down.

---

## 🚨 Alert Rules (Prometheus)

| Alert | Condition | Duration | Severity | Action |
|-------|-----------|----------|----------|--------|
| HighCriticalViolations | >5 critical | 5m | Critical | Page on-call |
| HighFailureRate | >10% failures | 10m | Warning | Notify team |
| ScanStale | >1hr no scan | 10m | Warning | Check scheduler |
| SlowRuleEvaluation | >100ms latency | 5m | Warning | Optimize rule |
| MetricsPushFailure | Push status=0 | 5m | Info | Check pushgateway |

---

## 🎨 Color Legend

**Severity Colors**:
- 🔴 **Critical**: Dark Red - Immediate action required
- 🟠 **High**: Dark Orange - High priority
- 🟡 **Medium**: Dark Yellow - Medium priority
- 🔵 **Low**: Dark Blue - Low priority

**Threshold Colors**:
- 🟢 **Green**: Healthy state, no issues
- 🟡 **Yellow**: Warning state, monitor closely
- 🔴 **Red**: Critical state, take action

---

## 🔍 Common PromQL Queries

### Total Violations
```promql
sum(crashlens_violations_total)
```

### Critical Violations in Last Hour
```promql
sum(increase(crashlens_violations_total{severity="critical"}[1h]))
```

### Rule Hit Rate (per minute)
```promql
sum by (rule) (rate(crashlens_rule_hits_total[5m])) * 60
```

### Failure Rate (%)
```promql
(sum(crashlens_traces_failed_total) / 
 (sum(crashlens_traces_processed_total) + sum(crashlens_traces_failed_total))) * 100
```

### Top 10 Slowest Rules
```promql
topk(10, crashlens_decision_latency_avg_seconds) * 1000
```

### Time Since Last Scan (minutes)
```promql
(time() - crashlens_last_run_timestamp_seconds{status="success"}) / 60
```

---

## ⚡ Keyboard Shortcuts (Grafana)

| Shortcut | Action |
|----------|--------|
| `d + k` | Open dashboard picker |
| `d + h` | Go to home dashboard |
| `t + z` | Zoom out time range |
| `Ctrl + S` | Save dashboard |
| `?` | Show keyboard shortcuts |
| `Esc` | Exit fullscreen |

---

## 🔧 Quick Troubleshooting

### No Data Showing?
```bash
# Check metrics in pushgateway
curl http://localhost:9091/metrics | grep crashlens

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.scrapePool=="pushgateway")'

# Push test metrics
poetry run crashlens scan sample-logs/demo-logs.jsonl --push-metrics
```

### Alerts Not Firing?
```bash
# Check alert rules loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[].name'

# Check current alerts
curl http://localhost:9090/api/v1/alerts | jq '.data.alerts[].labels.alertname'
```

### Slow Dashboard?
- Reduce time range (top-right picker)
- Use template variables to filter data
- Check Prometheus query performance: http://localhost:9090/graph

---

## 📖 Useful URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Grafana | http://localhost:3000 | Dashboard UI |
| Prometheus | http://localhost:9090 | Query metrics |
| Pushgateway | http://localhost:9091 | View pushed metrics |
| Prometheus Targets | http://localhost:9090/targets | Check scrape status |
| Prometheus Alerts | http://localhost:9090/alerts | View alert status |

---

## 🎯 Best Practices

✅ **DO**:
- Use template variables to filter data
- Monitor dashboard daily in production
- Set appropriate time ranges (1h, 24h, 7d)
- Watch for trends, not just point values
- Use shared crosshair to correlate events

❌ **DON'T**:
- Query very large time ranges (>30d)
- Ignore yellow/red threshold indicators
- Disable alerts without investigation
- Use "All" filters for very high-cardinality labels

---

## 📚 Documentation Links

- **Full Dashboard Guide**: `dashboards/README.md`
- **Observability Docs**: `docs/OBSERVABILITY.md`
- **Command Reference**: `docs/COMMAND-REFERENCE.md`
- **Grafana Docs**: https://grafana.com/docs/
- **PromQL Guide**: https://prometheus.io/docs/prometheus/latest/querying/basics/

---

## 🆘 Getting Help

1. **Check troubleshooting section** in `dashboards/README.md`
2. **Review Prometheus logs**: `docker logs prometheus`
3. **Check Grafana logs**: `docker logs grafana`
4. **Open GitHub Issue** with screenshot and error message

---

**Print this card and keep near your monitoring station! 📋**
