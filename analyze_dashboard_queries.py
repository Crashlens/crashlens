#!/usr/bin/env python3
"""
Analyze Grafana Dashboard Queries for CrashLens
Validates metric names and labels against backend implementation
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Valid metrics from crashlens/observability/metrics.py
VALID_METRICS = {
    # Counters
    "crashlens_rule_hits_total": {"labels": ["job", "rule", "severity", "mode"]},
    "crashlens_violations_total": {"labels": ["severity"]},
    "crashlens_traces_processed_total": {"labels": []},
    "crashlens_traces_failed_total": {"labels": ["reason"]},
    "crashlens_rule_label_overflow_total": {"labels": []},
    "crashlens_cost_savings_total": {"labels": []},
    "crashlens_total_llm_cost": {"labels": []},
    "crashlens_tokens_wasted_total": {"labels": []},
    
    # Gauges
    "crashlens_decision_latency_avg_seconds": {"labels": ["rule"]},
    "crashlens_last_run_timestamp_seconds": {"labels": ["status"]},
    "crashlens_metrics_push_status": {"labels": []},
}

# Valid severity values (not "critical" which user flagged)
VALID_SEVERITIES = ["high", "medium", "low"]

def extract_queries(dashboard_path: Path) -> List[Tuple[int, str]]:
    """Extract all Prometheus queries from dashboard JSON."""
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all "expr": "..." patterns with line numbers
    queries = []
    for i, line in enumerate(content.split('\n'), 1):
        if '"expr":' in line:
            # Extract the query expression
            match = re.search(r'"expr":\s*"([^"]+)"', line)
            if match:
                queries.append((i, match.group(1)))
    
    return queries

def analyze_query(line_num: int, query: str) -> Dict:
    """Analyze a single query for issues."""
    issues = []
    warnings = []
    metric_name = None
    
    # Extract metric name (first word before { or whitespace)
    metric_match = re.match(r'([a-z_]+)', query)
    if metric_match:
        metric_name = metric_match.group(1)
    
    # Skip non-crashlens metrics
    if not metric_name or not metric_name.startswith('crashlens_'):
        return {
            "line": line_num,
            "query": query,
            "metric": metric_name,
            "valid": True,
            "issues": [],
            "warnings": [],
            "skip": True
        }
    
    # Check if metric exists
    if metric_name not in VALID_METRICS:
        issues.append(f"❌ Metric '{metric_name}' does not exist in backend")
    
    # Check for "critical" severity (should be "high", "medium", or "low")
    if 'severity="critical"' in query or "severity='critical'" in query:
        issues.append('❌ Invalid severity: "critical" (use "high", "medium", or "low")')
    
    # Check for _created suffix (auto-generated, shouldn't be queried directly)
    if '_created' in query:
        warnings.append('⚠️  Querying _created timestamp (auto-generated, may not be useful)')
    
    # Check for job label filter
    if 'job=' not in query and 'job~' not in query and metric_name in [
        "crashlens_rule_hits_total",
        "crashlens_cost_savings_total",
        "crashlens_tokens_wasted_total",
        "crashlens_total_llm_cost"
    ]:
        warnings.append('⚠️  Missing job label filter (may aggregate all jobs)')
    
    # Check for template variable usage
    if '$job' not in query and 'job=' not in query and metric_name == "crashlens_rule_hits_total":
        warnings.append('⚠️  Not using $job template variable (may show wrong data)')
    
    return {
        "line": line_num,
        "query": query,
        "metric": metric_name,
        "valid": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "skip": False
    }

def main():
    dashboard_path = Path(__file__).parent / "dashboards" / "crashlens-policy-enforcement.json"
    
    print("═" * 100)
    print("🔍 CRASHLENS DASHBOARD QUERY ANALYSIS")
    print("═" * 100)
    print(f"\n📁 Analyzing: {dashboard_path}")
    print(f"📏 Dashboard size: {dashboard_path.stat().st_size:,} bytes\n")
    
    # Extract all queries
    queries = extract_queries(dashboard_path)
    print(f"✅ Found {len(queries)} total queries\n")
    
    # Analyze each query
    results = []
    for line_num, query in queries:
        result = analyze_query(line_num, query)
        if not result["skip"]:
            results.append(result)
    
    # Filter to crashlens metrics only
    crashlens_queries = [r for r in results if not r["skip"]]
    print(f"🎯 CrashLens metrics: {len(crashlens_queries)} queries\n")
    
    # Separate valid and invalid
    valid = [r for r in crashlens_queries if r["valid"]]
    invalid = [r for r in crashlens_queries if not r["valid"]]
    with_warnings = [r for r in crashlens_queries if r["warnings"]]
    
    # Print summary
    print("─" * 100)
    print("📊 SUMMARY")
    print("─" * 100)
    print(f"✅ Valid queries: {len(valid)}")
    print(f"❌ Invalid queries: {len(invalid)}")
    print(f"⚠️  Queries with warnings: {len(with_warnings)}\n")
    
    # Show invalid queries
    if invalid:
        print("═" * 100)
        print("❌ INVALID QUERIES (MUST FIX)")
        print("═" * 100)
        for result in invalid:
            print(f"\n📍 Line {result['line']}")
            print(f"   Query: {result['query']}")
            print(f"   Metric: {result['metric']}")
            for issue in result['issues']:
                print(f"   {issue}")
    
    # Show warnings
    if with_warnings:
        print("\n" + "═" * 100)
        print("⚠️  QUERIES WITH WARNINGS (REVIEW)")
        print("═" * 100)
        for result in with_warnings:
            print(f"\n📍 Line {result['line']}")
            print(f"   Query: {result['query']}")
            print(f"   Metric: {result['metric']}")
            for warning in result['warnings']:
                print(f"   {warning}")
    
    # Show valid metrics being used
    if valid:
        print("\n" + "═" * 100)
        print("✅ VALID METRICS IN USE")
        print("═" * 100)
        metrics_used = {}
        for result in valid:
            metric = result['metric']
            if metric not in metrics_used:
                metrics_used[metric] = 0
            metrics_used[metric] += 1
        
        for metric, count in sorted(metrics_used.items()):
            labels = VALID_METRICS[metric]["labels"]
            label_str = f"[{', '.join(labels)}]" if labels else "[no labels]"
            print(f"   ✓ {metric:<50} {label_str:<30} ({count} queries)")
    
    # Check for missing metrics
    print("\n" + "═" * 100)
    print("🔍 METRICS AVAILABILITY CHECK")
    print("═" * 100)
    
    metrics_queried = set(r['metric'] for r in crashlens_queries)
    
    print("\n✅ Metrics implemented AND used in dashboard:")
    for metric in sorted(metrics_queried):
        if metric in VALID_METRICS:
            print(f"   ✓ {metric}")
    
    print("\n⚠️  Metrics implemented but NOT used in dashboard:")
    for metric in sorted(VALID_METRICS.keys()):
        if metric not in metrics_queried:
            labels = VALID_METRICS[metric]["labels"]
            label_str = f" [{', '.join(labels)}]" if labels else ""
            print(f"   • {metric}{label_str}")
    
    print("\n❌ Metrics queried but NOT implemented:")
    for metric in sorted(metrics_queried):
        if metric not in VALID_METRICS:
            print(f"   ✗ {metric} (will show 'No data' in Grafana)")
    
    # Final recommendations
    print("\n" + "═" * 100)
    print("💡 RECOMMENDATIONS")
    print("═" * 100)
    
    if invalid:
        print("\n🔴 CRITICAL FIXES NEEDED:")
        print("   1. Fix 'severity=\"critical\"' → Use 'severity=\"high\"' or 'severity=~\"high|medium\"'")
        print("   2. Remove queries for non-existent metrics")
        print("   3. Ensure all metrics match backend implementation")
    
    if with_warnings:
        print("\n🟡 RECOMMENDED IMPROVEMENTS:")
        print("   1. Add job label filters where missing: {job=~\"$job\"}")
        print("   2. Use template variables: $job, $severity, $rule, $mode")
        print("   3. Review _created queries (usually not needed)")
    
    print("\n🟢 VALIDATION CHECKLIST:")
    print("   [ ] All severity values are: high, medium, or low (NOT critical)")
    print("   [ ] All metric names exist in crashlens/observability/metrics.py")
    print("   [ ] Job labels use {job=~\"$job\"} template variable")
    print("   [ ] No _created suffixes in queries")
    print("   [ ] FinOps metrics (cost_savings, tokens_wasted, total_llm_cost) are present")
    
    print("\n" + "═" * 100)
    
    # Exit code
    if invalid:
        print("❌ ANALYSIS FAILED - Invalid queries found")
        print("═" * 100)
        return 1
    else:
        print("✅ ANALYSIS COMPLETE - All queries valid")
        print("═" * 100)
        return 0

if __name__ == "__main__":
    exit(main())
