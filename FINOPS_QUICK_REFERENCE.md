# FinOps Metrics Quick Reference Guide

## 🚀 Quick Start

Enable FinOps metrics in 3 steps:

```bash
# 1. Run CrashLens with metrics enabled
crashlens scan logs.jsonl --push-metrics --pushgateway-url http://localhost:9091

# 2. Import Grafana dashboard
# Dashboard → Import → Upload dashboards/crashlens-policy-enforcement.json

# 3. View FinOps panels (automatically populated!)
# - Total Cost Savings
# - Cost Per Violation  
# - Tokens Wasted
```

## 📊 Available Metrics

### crashlens_cost_savings_total
- **Type**: Counter
- **Description**: Total estimated cost savings from detecting wasteful patterns
- **Unit**: USD
- **Source**: Sum of `waste_cost` from all detections
- **Example PromQL**: `sum(crashlens_cost_savings_total)`

### crashlens_total_llm_cost
- **Type**: Counter
- **Description**: Total LLM API costs observed in traces
- **Unit**: USD
- **Source**: Sum of `cost` field from all trace records
- **Example PromQL**: `sum(crashlens_total_llm_cost)`

### crashlens_tokens_wasted_total
- **Type**: Counter
- **Description**: Total tokens wasted (prompt + completion)
- **Unit**: Tokens
- **Source**: Sum of `waste_tokens` from all detections
- **Example PromQL**: `sum(crashlens_tokens_wasted_total)`

## 🎯 Common Use Cases

### Calculate ROI
```promql
# Cost savings rate (per hour)
rate(crashlens_cost_savings_total[1h]) * 3600
```

### Cost Efficiency
```promql
# Cost per violation (average)
sum(crashlens_total_llm_cost) / sum(crashlens_violations_total)
```

### Waste Trend Analysis
```promql
# Token waste rate (per minute)
rate(crashlens_tokens_wasted_total[5m]) * 60
```

### Savings Percentage
```promql
# What % of total cost was wasted?
(sum(crashlens_cost_savings_total) / sum(crashlens_total_llm_cost)) * 100
```

## 🚨 Alert Rules

Edit `dashboards/crashlens-alert-rules.yml` and uncomment:

### High Cost Per Violation
```yaml
- alert: CrashLensHighCostPerViolation
  expr: '(sum(crashlens_total_llm_cost) / sum(crashlens_violations_total)) > 10'
  for: 15m
  labels:
    severity: warning
```
**Triggers when**: Average cost per violation exceeds $10

### Low Cost Savings
```yaml
- alert: CrashLensLowCostSavings
  expr: 'rate(crashlens_cost_savings_total[1h]) < 1'
  for: 1h
  labels:
    severity: info
```
**Triggers when**: Savings rate drops below $1/hour

### High Token Waste
```yaml
- alert: CrashLensHighTokenWaste
  expr: 'rate(crashlens_tokens_wasted_total[5m]) > 10000'
  for: 10m
  labels:
    severity: critical
```
**Triggers when**: Token waste exceeds 10,000 tokens/min

## 🔧 Configuration

### Metrics Sampling
Control overhead with sampling rate:

```bash
# 100% sampling (default)
crashlens scan logs.jsonl --push-metrics

# 10% sampling (lower overhead, less granularity)
export CRASHLENS_SAMPLE_RATE=0.1
crashlens scan logs.jsonl --push-metrics
```

### Pushgateway URL
Configure via flag or environment variable:

```bash
# Via flag
--pushgateway-url http://localhost:9091

# Via environment
export CRASHLENS_PUSHGATEWAY_URL=http://my-pushgateway:9091
```

### Job Name
Group metrics by environment:

```bash
--metrics-job crashlens_production
--metrics-job crashlens_staging
--metrics-job crashlens_dev
```

## 📈 Grafana Dashboard Panels

### Panel 1: Total Cost Savings
- **Query**: `sum(crashlens_cost_savings_total)`
- **Visualization**: Stat panel with time series graph
- **Interpretation**: Higher is better (more waste detected = more savings)

### Panel 2: Cost Per Violation
- **Query**: `sum(crashlens_total_llm_cost) / sum(crashlens_violations_total)`
- **Visualization**: Gauge
- **Interpretation**: Lower is better (violations should be cheap to detect)

### Panel 3: Tokens Wasted
- **Query**: `sum(crashlens_tokens_wasted_total)`
- **Visualization**: Stat panel with sparkline
- **Interpretation**: Shows scale of waste problem

## 🐛 Troubleshooting

### Metrics not appearing in Grafana?

**Check 1: Metrics enabled?**
```bash
# Look for this line in scan output:
✓ Metrics collection enabled (100% sampling)
```

**Check 2: Push successful?**
```bash
# Look for this line:
✓ Metrics pushed to http://localhost:9091
```

**Check 3: Pushgateway running?**
```bash
curl http://localhost:9091/metrics | grep crashlens_cost
```

**Check 4: Prometheus scraping pushgateway?**
```bash
# Check Prometheus targets page:
http://localhost:9090/targets
```

**Check 5: Data in Prometheus?**
```bash
# Query Prometheus directly:
http://localhost:9090/graph?g0.expr=crashlens_cost_savings_total
```

### Panels show "No data"?

- **Cause**: No scans run with `--push-metrics` flag
- **Fix**: Run at least one scan with metrics enabled
- **Note**: Counters start at 0, need at least one detection to populate

### Metrics reset to zero?

- **Expected Behavior**: Counters persist across scans (cumulative)
- **Reset Triggers**:
  - Pushgateway restart
  - Prometheus restart without persistence
  - Manual deletion: `curl -X DELETE http://localhost:9091/metrics/job/crashlens_production`

## 📚 Additional Resources

- **Full Implementation Docs**: `FINOPS_METRICS_IMPLEMENTATION.md`
- **Test Script**: `test_finops_metrics.py`
- **Dashboard JSON**: `dashboards/crashlens-policy-enforcement.json`
- **Alert Rules**: `dashboards/crashlens-alert-rules.yml`
- **Observability Guide**: `docs/OBSERVABILITY.md`

## 💡 Best Practices

1. **Always use `--push-metrics` in production** to track ROI
2. **Set up alerts** to catch cost anomalies early
3. **Review FinOps panels weekly** to spot trends
4. **Compare savings across teams** using `--metrics-job` labels
5. **Document cost reduction wins** using Grafana screenshots

## 🎓 Example Workflow

```bash
# Morning: Run scan with metrics
crashlens scan daily-logs.jsonl \
  --push-metrics \
  --pushgateway-url http://pushgateway.prod:9091 \
  --metrics-job crashlens_ai_team

# Afternoon: Check Grafana dashboard
# - Review cost savings trend
# - Identify high-cost violations
# - Export report for stakeholders

# Weekly: Generate cost report
# - Screenshot FinOps panels
# - Calculate ROI: savings / (CrashLens cost)
# - Share with finance team
```

---

**Need Help?** Open an issue at https://github.com/Crashlens/crashlens/issues
