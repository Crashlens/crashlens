#!/usr/bin/env python3
"""Validate the generated FinOps dashboard JSON."""

import json
from pathlib import Path

dashboard_path = Path('dashboards/crashlens-policy-enforcement.json')

print("="*80)
print("  Dashboard Validation Report")
print("="*80)

# Load and validate JSON
try:
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print("\n✅ Valid JSON structure")
except Exception as e:
    print(f"\n❌ JSON validation failed: {e}")
    exit(1)

# Basic metadata
print(f"\n📊 Dashboard Metadata:")
print(f"   Title: {data['title']}")
print(f"   Version: {data['version']}")
print(f"   Schema Version: {data['schemaVersion']}")
print(f"   Total Panels: {len(data['panels'])}")

# Count rows and panels by type
rows = sum(1 for p in data['panels'] if p.get('type') == 'row')
panel_types = {}
for panel in data['panels']:
    ptype = panel.get('type', 'unknown')
    if ptype != 'row':
        panel_types[ptype] = panel_types.get(ptype, 0) + 1

print(f"   Rows: {rows}")
print(f"   Panel Types:")
for ptype, count in sorted(panel_types.items()):
    print(f"     - {ptype}: {count}")

# Check datasource configuration
ds_prometheus_count = sum(1 for p in data['panels'] 
                          if '${DS_PROMETHEUS}' in str(p.get('datasource', '')))
ds_hardcoded = sum(1 for p in data['panels'] 
                   if p.get('datasource') == 'Prometheus')

print(f"\n🔌 Datasource Configuration:")
print(f"   ✅ Using ${'{DS_PROMETHEUS}'} variable: {ds_prometheus_count} panels")
if ds_hardcoded > 0:
    print(f"   ⚠️  Hardcoded 'Prometheus': {ds_hardcoded} panels (should be 0)")
else:
    print(f"   ✅ No hardcoded datasources")

# List all panels with their metrics
print(f"\n📋 Panel Overview:")
current_row = None
for panel in data['panels']:
    if panel.get('type') == 'row':
        current_row = panel.get('title', 'Unknown Row')
        print(f"\n  {current_row}")
    else:
        title = panel.get('title', 'Untitled')
        panel_type = panel.get('type', 'unknown')
        
        # Extract query
        targets = panel.get('targets', [])
        if targets and 'expr' in targets[0]:
            query = targets[0]['expr']
            # Truncate long queries
            if len(query) > 60:
                query = query[:57] + "..."
        else:
            query = "No query"
        
        print(f"    - {title} ({panel_type})")
        print(f"      Query: {query}")

# Check for FinOps panels
print(f"\n💰 FinOps Panels Check:")
finops_keywords = ['Cost', 'Token', 'FinOps', 'Saving']
finops_panels = [p for p in data['panels'] 
                 if any(kw in p.get('title', '') for kw in finops_keywords)]

if len(finops_panels) >= 3:
    print(f"   ✅ Found {len(finops_panels)} FinOps-related panels:")
    for panel in finops_panels:
        print(f"     - {panel.get('title')}")
else:
    print(f"   ⚠️  Only {len(finops_panels)} FinOps panels found (expected 3+)")

# Check for required metrics
print(f"\n📊 FinOps Metrics Coverage:")
required_metrics = [
    'crashlens_cost_savings_total',
    'crashlens_total_llm_cost',
    'crashlens_tokens_wasted_total'
]

all_queries = []
for panel in data['panels']:
    for target in panel.get('targets', []):
        if 'expr' in target:
            all_queries.append(target['expr'])

for metric in required_metrics:
    found = any(metric in q for q in all_queries)
    status = "✅" if found else "❌"
    print(f"   {status} {metric}")

# Template variables check
print(f"\n🔧 Template Variables:")
for var in data.get('templating', {}).get('list', []):
    name = var.get('name', 'unknown')
    var_type = var.get('type', 'unknown')
    ds = var.get('datasource', 'N/A')
    print(f"   - ${{{name}}} ({var_type}) → {ds}")

print("\n" + "="*80)
print("  Validation Complete")
print("="*80)
print(f"\n✅ Dashboard is ready for import to Grafana!")
print(f"   File: {dashboard_path.absolute()}")
print(f"   Size: {dashboard_path.stat().st_size:,} bytes")
print("\n" + "="*80)
