"""Test script to validate JSON formatter output structure"""
import json

# Load the generated report
with open('report.md', 'r') as f:
    data = json.load(f)

print("JSON Structure Validation:")
print("=" * 50)

# Validate metadata
print(f"\nMetadata keys: {list(data['metadata'].keys())}")
assert 'scan_time' in data['metadata']
assert 'health_score' in data['metadata']
print("  ✓ Metadata complete")

# Validate summary
print(f"\nSummary keys: {list(data['summary'].keys())}")
assert 'total_issues' in data['summary']
assert 'potential_savings' in data['summary']
print("  ✓ Summary complete")

# Validate issues
print(f"\nTotal issues: {len(data['issues'])}")
if len(data['issues']) > 0:
    sample_issue = data['issues'][0]
    print(f"Sample issue keys: {list(sample_issue.keys())}")
    assert 'type' in sample_issue
    assert 'severity' in sample_issue
    assert 'cost' in sample_issue
    print("  ✓ Issues structure valid")

# Validate traces
print(f"\nTotal traces: {len(data['traces'])}")
if len(data['traces']) > 0:
    sample_trace = data['traces'][0]
    print(f"Sample trace keys: {list(sample_trace.keys())}")
    assert 'trace_id' in sample_trace
    assert 'total_cost' in sample_trace
    print("  ✓ Traces structure valid")

# Validate models
print(f"\nProviders: {list(data['models']['by_provider'].keys())}")
assert 'by_provider' in data['models']
assert 'top_models' in data['models']
print("  ✓ Models structure valid")

# Validate timeline
print(f"\nTimeline events: {len(data['timeline'])}")
print("  ✓ Timeline present")

# Validate recommendations
print(f"\nRecommendations: {len(data['recommendations'])}")
if len(data['recommendations']) > 0:
    sample_rec = data['recommendations'][0]
    print(f"Sample recommendation keys: {list(sample_rec.keys())}")
    assert 'priority' in sample_rec
    assert 'estimated_savings' in sample_rec
    print("  ✓ Recommendations structure valid")

# Validate alerts
print(f"\nAlerts: {len(data['alerts'])}")
print("  ✓ Alerts present")

# Validate export options
print(f"\nExport formats: {data['export_options']['formats']}")
assert 'json' in data['export_options']['formats']
print("  ✓ Export options valid")

print("\n" + "=" * 50)
print("All sections present and valid: ✓ OK")
print(f"Health Score: {data['metadata']['health_score']}")
print(f"Total Cost: ${data['summary']['total_cost']}")
print(f"Potential Savings: ${data['summary']['potential_savings']}")
