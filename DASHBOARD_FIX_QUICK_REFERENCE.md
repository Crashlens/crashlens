# ⚡ Quick Reference: Dashboard Fix

## 🎯 What Was Fixed
**Panel #6** - Query changed from `severity="critical"` to `severity="high"`

## 📁 File to Import
```
dashboards/crashlens-policy-enforcement.json
```

## 🚀 Import to Grafana (3 Steps)
1. Open http://localhost:3000
2. Dashboards → Import → Upload JSON
3. Select Prometheus datasource → Import

## 📊 Populate Metrics
```bash
crashlens scan logs.jsonl --push-metrics \
  --pushgateway-url http://localhost:9091
```

## ✅ Validation
```bash
python check_dashboard_queries.py
```
**Expected:** ✅ DASHBOARD VALIDATION PASSED

## 🔍 Why It Failed Before
- **Query used:** `severity="critical"`
- **Problem:** No detector produces "critical" severity
- **Valid values:** `high`, `medium`, `low`
- **Result:** Prometheus returned no data → Grafana showed empty panel

## 📚 More Info
- **DASHBOARD_QUERY_FIX_REPORT.md** - Complete analysis
- **DASHBOARD_UPLOAD_GUIDE.md** - Full import guide

---

## 🎓 Valid Severity Values

| Severity | Detectors Produce | Backend Accepts | Grafana Query |
|----------|-------------------|-----------------|---------------|
| `high` | ✅ Yes | ✅ Yes | ✅ Works |
| `medium` | ✅ Yes | ✅ Yes | ✅ Works |
| `low` | ✅ Yes | ✅ Yes | ✅ Works |
| `critical` | ❌ **No** | ✅ Yes (unused) | ❌ **Returns no data** |
| `info` | ❌ No | ✅ Yes (unused) | ❌ Returns no data |

## 📊 All Metrics in Dashboard

| Metric | Panels Using It |
|--------|-----------------|
| `crashlens_violations_total` | 4 panels (incl. Panel #6) |
| `crashlens_rule_hits_total` | 3 panels |
| `crashlens_cost_savings_total` | 2 panels (FinOps) |
| `crashlens_tokens_wasted_total` | 1 panel (FinOps) |
| `crashlens_total_llm_cost` | 1 panel (FinOps) |
| `crashlens_last_run_timestamp_seconds` | 1 panel |
| `crashlens_rule_label_overflow_total` | 1 panel |
| `crashlens_metrics_push_status` | 1 panel |

**Total:** 8 metrics across 15 panels ✅

---

## 🛠️ Troubleshooting

### Panels show "No data" after import?
1. Check Prometheus scraping: `curl http://localhost:9090/api/v1/targets`
2. Verify metrics exist: `curl http://localhost:9090/api/v1/query?query=crashlens_violations_total`
3. Run scan with `--push-metrics`
4. Wait 15-30 seconds for scrape
5. Refresh Grafana

### "Datasource not found" error?
- During import, select your Prometheus datasource from dropdown
- The `${DS_PROMETHEUS}` variable will auto-populate

### Panel #6 still empty?
- Old query: `severity="critical"` ❌
- New query: `severity="high"` ✅
- Re-upload JSON if you uploaded before the fix

---

**Status:** ✅ Dashboard validated and fixed - ready for production!
