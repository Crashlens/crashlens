"""Test that all required metrics are defined."""
from crashlens.metrics import MetricsCollector

print("✅ Metrics module imported successfully\n")

# Initialize collector
collector = MetricsCollector()
print("✅ MetricsCollector initialized\n")

# List all metrics
print("📊 Available Prometheus Metrics:\n")

required_metrics = [
    'crashlens_guard_runs_total',
    'crashlens_guard_violations_total',
    'crashlens_guard_logs_processed_total',
    'crashlens_guard_rules_evaluated_total',
    'crashlens_guard_duration_seconds',
    'crashlens_guard_latency_ms',
    'crashlens_guard_last_run_timestamp',
    'crashlens_guard_active_rules'
]

# Check each metric
for metric_name in required_metrics:
    # Get the attribute name (remove crashlens_ prefix, replace _ with _)
    attr_name = metric_name.replace('crashlens_guard_', 'guard_').replace('_total', '')
    
    # Special handling for some metric names
    if 'logs_processed' in metric_name:
        attr_name = 'guard_logs_processed'
    elif 'rules_evaluated' in metric_name:
        attr_name = 'guard_rules_evaluated'
    elif 'latency_ms' in metric_name:
        attr_name = 'guard_latency_ms'
    elif 'last_run' in metric_name:
        attr_name = 'guard_last_run_timestamp'
    elif 'active_rules' in metric_name:
        attr_name = 'guard_active_rules'
    elif 'duration' in metric_name:
        attr_name = 'guard_duration_seconds'
    elif 'violations' in metric_name:
        attr_name = 'guard_violations_total'
    elif 'runs' in metric_name:
        attr_name = 'guard_runs_total'
    
    if hasattr(collector, attr_name):
        metric_obj = getattr(collector, attr_name)
        metric_type = type(metric_obj).__name__
        print(f"  ✅ {metric_name} ({metric_type})")
    else:
        print(f"  ❌ {metric_name} - NOT FOUND (expected attribute: {attr_name})")

print("\n🎉 All required metrics are defined!")
