#!/usr/bin/env python3
"""Find all dashboard query issues"""
import json

# Load dashboard
with open('dashboards/crashlens-policy-enforcement.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Extract panels
panels = [p for p in data.get('panels', []) if p.get('type') != 'row']

print("=" * 100)
print("🔍 CRASHLENS DASHBOARD QUERY VALIDATION")
print("=" * 100)
print(f"\nTotal data panels: {len(panels)}\n")

# Valid severity values
VALID_SEVERITIES = ['high', 'medium', 'low']

# Collect all issues
issues = []
warnings = []

for panel in panels:
    panel_id = panel.get('id')
    panel_title = panel.get('title', 'Untitled')
    
    for target in panel.get('targets', []):
        expr = target.get('expr', '')
        if not expr or 'crashlens_' not in expr:
            continue
        
        # Check for invalid "critical" severity
        if 'severity="critical"' in expr or "severity='critical'" in expr:
            issues.append({
                'type': 'INVALID_SEVERITY',
                'panel_id': panel_id,
                'panel_title': panel_title,
                'query': expr,
                'issue': 'Uses severity="critical" (should be "high", "medium", or "low")'
            })
        
        # Check for _created metrics
        if '_created' in expr:
            warnings.append({
                'type': 'CREATED_METRIC',
                'panel_id': panel_id,
                'panel_title': panel_title,
                'query': expr,
                'warning': 'Queries _created timestamp (auto-generated, may not be useful)'
            })
        
        # Check if query is missing job filter for metrics that should have it
        if 'crashlens_rule_hits_total' in expr and 'job=' not in expr and 'job~' not in expr:
            warnings.append({
                'type': 'MISSING_JOB_FILTER',
                'panel_id': panel_id,
                'panel_title': panel_title,
                'query': expr,
                'warning': 'Missing job label filter (may aggregate all jobs incorrectly)'
            })

# Print issues
print("=" * 100)
print("❌ CRITICAL ISSUES (MUST FIX)")
print("=" * 100)

if issues:
    for i, issue in enumerate(issues, 1):
        print(f"\n{i}. Panel #{issue['panel_id']}: {issue['panel_title']}")
        print(f"   Issue: {issue['issue']}")
        print(f"   Query: {issue['query'][:80]}..." if len(issue['query']) > 80 else f"   Query: {issue['query']}")
        print(f"\n   🔧 FIX: Change severity=\"critical\" to severity=\"high\" or severity=~\"high|medium\"")
else:
    print("\n✅ No critical issues found!")

# Print warnings
print("\n" + "=" * 100)
print("⚠️  WARNINGS (REVIEW RECOMMENDED)")
print("=" * 100)

if warnings:
    for i, warn in enumerate(warnings, 1):
        print(f"\n{i}. Panel #{warn['panel_id']}: {warn['panel_title']}")
        print(f"   Warning: {warn['warning']}")
        print(f"   Query: {warn['query'][:80]}..." if len(warn['query']) > 80 else f"   Query: {warn['query']}")
else:
    print("\n✅ No warnings!")

# List all crashlens metrics being queried
print("\n" + "=" * 100)
print("📊 ALL CRASHLENS METRICS IN DASHBOARD")
print("=" * 100)

metrics_used = set()
for panel in panels:
    for target in panel.get('targets', []):
        expr = target.get('expr', '')
        if 'crashlens_' in expr:
            # Extract metric name (first crashlens_* word)
            import re
            match = re.search(r'crashlens_[a-z_]+', expr)
            if match:
                metrics_used.add(match.group(0))

print("\nMetrics found in dashboard queries:")
for metric in sorted(metrics_used):
    print(f"   ✓ {metric}")

# Valid metrics from backend
VALID_METRICS = {
    'crashlens_rule_hits_total',
    'crashlens_violations_total',
    'crashlens_traces_processed_total',
    'crashlens_traces_failed_total',
    'crashlens_rule_label_overflow_total',
    'crashlens_cost_savings_total',
    'crashlens_total_llm_cost',
    'crashlens_tokens_wasted_total',
    'crashlens_decision_latency_avg_seconds',
    'crashlens_last_run_timestamp_seconds',
    'crashlens_metrics_push_status',
}

print("\n" + "=" * 100)
print("✅ VALIDATION SUMMARY")
print("=" * 100)

invalid_metrics = metrics_used - VALID_METRICS
missing_metrics = VALID_METRICS - metrics_used

if invalid_metrics:
    print(f"\n❌ {len(invalid_metrics)} metrics queried but NOT implemented in backend:")
    for metric in sorted(invalid_metrics):
        print(f"   ✗ {metric} (will show 'No data' in Grafana)")

if missing_metrics:
    print(f"\n⚠️  {len(missing_metrics)} metrics implemented but NOT used in dashboard:")
    for metric in sorted(missing_metrics):
        print(f"   • {metric}")

print(f"\n✅ {len(metrics_used & VALID_METRICS)} metrics correctly implemented AND used")

# Final verdict
print("\n" + "=" * 100)
if issues:
    print("❌ DASHBOARD HAS CRITICAL ISSUES - MUST FIX BEFORE DEPLOYMENT")
    print("=" * 100)
    print(f"\nFound {len(issues)} critical issue(s):")
    print("   1. Fix severity=\"critical\" → use severity=\"high\" or severity=~\"high|medium\"")
    exit(1)
else:
    print("✅ DASHBOARD VALIDATION PASSED")
    print("=" * 100)
    if warnings:
        print(f"\nNote: {len(warnings)} warnings found (optional improvements)")
    exit(0)
