# CrashLens Observability Quick Reference Card

## 🚀 Quick Start (5 Minutes)

### Enable Metrics
```bash
crashlens scan logs.jsonl --push-metrics
```

### With Custom Config
```bash
crashlens scan logs.jsonl --push-metrics \
  --pushgateway-url http://prometheus.internal:9091 \
  --metrics-job production_scan \
  --metrics-max-rules 500 \
  --metrics-sample-rate 1.0
```

### Disable Globally
```bash
export CRASHLENS_DISABLE_METRICS=true
crashlens scan logs.jsonl --push-metrics  # No metrics collected
```

---

## 📊 Metrics Reference

### Counters
| Metric | Labels | Description |
|--------|--------|-------------|
| `crashlens_rule_hits_total` | rule, severity, mode | Total policy rule triggers |
| `crashlens_violations_total` | severity | Total violations by severity |
| `crashlens_traces_processed_total` | - | Total traces analyzed |
| `crashlens_traces_failed_total` | reason | Failed trace processing |
| `crashlens_rule_label_overflow_total` | - | Cardinality cap overflow events |

### Gauges
| Metric | Labels | Description |
|--------|--------|-------------|
| `crashlens_decision_latency_avg_seconds` | rule | Average rule evaluation latency |
| `crashlens_last_run_timestamp_seconds` | status | Unix timestamp of last run |
| `crashlens_metrics_push_status` | - | Push success (1) or failure (0) |

---

## 🔧 Configuration Options

### CLI Flags
```bash
--push-metrics                    # Enable metrics push to Pushgateway
--pushgateway-url <url>          # Gateway URL (default: http://localhost:9091)
--metrics-job <name>             # Job name for grouping (default: crashlens_scan)
--metrics-max-rules <int>        # Max unique rules (default: 500)
--metrics-sample-rate <float>    # Sampling rate 0.0-1.0 (default: 1.0)
```

### Environment Variables
```bash
CRASHLENS_DISABLE_METRICS=true              # Kill-switch (highest precedence)
CRASHLENS_PUSHGATEWAY_URL=http://...        # Override gateway URL
CRASHLENS_METRICS_JOB=my_job               # Override job name
CRASHLENS_METRICS_MAX_RULES=500            # Override cardinality cap
CRASHLENS_METRICS_SAMPLE_RATE=1.0          # Override sampling rate
```

---

## 🧹 Pushgateway Cleanup

### Delete Specific Job
```bash
curl -X DELETE http://localhost:9091/metrics/job/crashlens_scan
```

### Delete Job with Grouping Labels
```bash
curl -X DELETE http://localhost:9091/metrics/job/crashlens_scan/project/my-project
```

### Emergency Wipe (All Metrics)
```bash
curl -X PUT http://localhost:9091/api/v1/admin/wipe
```

### Verify Deletion
```bash
curl http://localhost:9091/metrics | grep crashlens
```

---

## 🎯 Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'pushgateway'
    honor_labels: true  # CRITICAL!
    static_configs:
      - targets: ['localhost:9091']
```

**⚠️ Important**: `honor_labels: true` is REQUIRED to preserve grouping keys.

---

## 📈 Grafana Dashboard

### Import Dashboard
1. Navigate to Grafana → Dashboards → Import
2. Upload: `dashboards/crashlens-policy-enforcement.json`
3. Select data source: CrashLens Prometheus
4. Click Import

### Key Panels
- **Total Violations**: All-time violation count
- **Critical Violations**: High-priority alerts
- **Rule Hits Rate**: Triggers per minute
- **Severity Distribution**: Pie chart breakdown
- **Top 10 Rules**: Most frequent violators
- **Trace Processing Rate**: Success vs failure
- **Rule Evaluation Latency**: Performance monitoring

### Template Variables
- `$job`: Filter by job name
- `$severity`: Filter by severity level
- `$rule`: Filter by specific rule
- `$mode`: Filter by execution mode
- `$interval`: Auto-adjust time range

---

## 🔍 PromQL Query Examples

### Total Violations (Last Hour)
```promql
increase(crashlens_violations_total[1h])
```

### Critical Violations Rate
```promql
rate(crashlens_violations_total{severity="critical"}[5m])
```

### Top 10 Rules by Hit Count
```promql
topk(10, sum by (rule) (crashlens_rule_hits_total))
```

### Failure Rate Percentage
```promql
(
  sum(rate(crashlens_traces_failed_total[5m]))
  / 
  sum(rate(crashlens_traces_processed_total[5m]))
) * 100
```

### Average Latency by Rule
```promql
avg by (rule) (crashlens_decision_latency_avg_seconds)
```

### Cardinality Check (Overflow Events)
```promql
increase(crashlens_rule_label_overflow_total[1h])
```

---

## 🚨 Alert Rules

### Critical Violations Spike
```yaml
- alert: CrashLensCriticalViolationSpike
  expr: rate(crashlens_violations_total{severity="critical"}[5m]) > 0.1
  for: 5m
  annotations:
    summary: "Critical policy violations spiking"
```

### High Failure Rate
```yaml
- alert: CrashLensHighFailureRate
  expr: |
    (
      sum(rate(crashlens_traces_failed_total[5m]))
      / 
      sum(rate(crashlens_traces_processed_total[5m]))
    ) > 0.1
  for: 10m
  annotations:
    summary: "Trace failure rate > 10%"
```

### Cardinality Overflow
```yaml
- alert: CrashLensCardinalityOverflow
  expr: increase(crashlens_rule_label_overflow_total[1h]) > 10
  for: 5m
  annotations:
    summary: "Rule cardinality cap breached"
```

### Pushgateway Push Failure
```yaml
- alert: CrashLensMetricsPushFailure
  expr: crashlens_metrics_push_status == 0
  for: 5m
  annotations:
    summary: "Metrics push to Pushgateway failing"
```

---

## 🛠️ Troubleshooting

### Metrics Not Appearing in Grafana

**Check 1**: Verify `--push-metrics` flag used
```bash
crashlens scan logs.jsonl --push-metrics
```

**Check 2**: Confirm Pushgateway URL
```bash
curl http://localhost:9091/metrics | grep crashlens
```

**Check 3**: Validate Prometheus scrape config
```bash
grep -A5 "pushgateway" prometheus.yml
# Should show: honor_labels: true
```

**Check 4**: Check Prometheus targets
- Navigate to Prometheus → Status → Targets
- Verify `pushgateway` job is UP

---

### Kill-Switch Not Working

**Check 1**: Verify environment variable set
```bash
echo $CRASHLENS_DISABLE_METRICS  # Should be 'true'
```

**Check 2**: Check CLI output
```bash
crashlens scan --push-metrics 2>&1 | grep "disabled"
# Should see: "Metrics disabled via CRASHLENS_DISABLE_METRICS"
```

---

### High Cardinality Warnings

**Symptom**: `Rule label limit reached` warnings in logs

**Solution 1**: Increase cap
```bash
crashlens scan --push-metrics --metrics-max-rules 1000
```

**Solution 2**: Check overflow counter
```promql
crashlens_rule_label_overflow_total
```

**Solution 3**: Review rule naming (consolidate similar rules)

---

### Performance Degradation

**Symptom**: Slow CLI execution with metrics enabled

**Solution 1**: Reduce sampling rate
```bash
crashlens scan --push-metrics --metrics-sample-rate 0.1  # 10% sampling
```

**Solution 2**: Disable metrics temporarily
```bash
export CRASHLENS_DISABLE_METRICS=true
```

**Solution 3**: Check gateway reachability
```bash
curl -I http://localhost:9091
```

---

## 📚 Additional Resources

- **Full Documentation**: `docs/OBSERVABILITY.md`
- **Grafana Setup**: `docs/GRAFANA_SETUP.md`
- **Dashboard README**: `dashboards/README.md`
- **Metrics Implementation**: `crashlens/observability/metrics.py`
- **Cleanup Runbook**: `tests/observability-evidence/PUSHGATEWAY_CLEANUP_RUNBOOK.md`
- **Verification Report**: `tests/observability-evidence/VERIFICATION_REPORT.md`

---

## 📞 Support

**Issue Tracker**: GitHub Issues  
**Documentation**: `docs/` directory  
**Examples**: `examples/` directory

---

**Version**: Phase 2 (October 2025)  
**Status**: Production Ready ✅  
**Last Updated**: 2025-10-25
