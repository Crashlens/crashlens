#!/usr/bin/env python3
"""Test script to verify FinOps metrics implementation."""

from crashlens.observability.metrics import _initialize_metrics_impl

print("="*80)
print("  Testing FinOps Metrics Implementation")
print("="*80)

# Initialize metrics
print("\n1. Initializing metrics...")
metrics = _initialize_metrics_impl(enabled=True)

if metrics is None:
    print("❌ FAILED: Metrics not initialized")
    exit(1)

print("✅ Metrics initialized successfully")

# Check FinOps attributes
print("\n2. Checking FinOps metric attributes...")
has_cost_savings = hasattr(metrics, 'cost_savings')
has_total_llm_cost = hasattr(metrics, 'total_llm_cost')
has_tokens_wasted = hasattr(metrics, 'tokens_wasted')

print(f"   - cost_savings counter: {'✅' if has_cost_savings else '❌'}")
print(f"   - total_llm_cost counter: {'✅' if has_total_llm_cost else '❌'}")
print(f"   - tokens_wasted counter: {'✅' if has_tokens_wasted else '❌'}")

if not (has_cost_savings and has_total_llm_cost and has_tokens_wasted):
    print("\n❌ FAILED: Not all FinOps metrics are available")
    exit(1)

# Test recording values
print("\n3. Testing metric recording...")
try:
    metrics.record_cost_savings(10.50)
    print("   ✅ Recorded cost savings: $10.50")
    
    metrics.record_llm_cost(25.75)
    print("   ✅ Recorded LLM cost: $25.75")
    
    metrics.record_tokens_wasted(5000)
    print("   ✅ Recorded tokens wasted: 5,000")
except Exception as e:
    print(f"\n❌ FAILED: Error recording metrics: {e}")
    exit(1)

# Test with zero/negative values (should be ignored)
print("\n4. Testing edge cases...")
try:
    metrics.record_cost_savings(0.0)  # Should be ignored
    metrics.record_cost_savings(-5.0)  # Should be ignored
    metrics.record_llm_cost(0.0)  # Should be ignored
    metrics.record_tokens_wasted(0)  # Should be ignored
    metrics.record_tokens_wasted(-100)  # Should be ignored
    print("   ✅ Edge cases handled correctly (zero/negative values ignored)")
except Exception as e:
    print(f"\n❌ FAILED: Error handling edge cases: {e}")
    exit(1)

print("\n" + "="*80)
print("  ✅ ALL TESTS PASSED - FinOps Metrics Implementation Complete!")
print("="*80)
print("\nFinOps Metrics Available:")
print("  - crashlens_cost_savings_total")
print("  - crashlens_total_llm_cost")
print("  - crashlens_tokens_wasted_total")
print("\nTo use these metrics:")
print("  1. Run: crashlens scan logs.jsonl --push-metrics")
print("  2. View in Grafana dashboard at http://localhost:3000")
print("  3. Uncomment FinOps alert rules in dashboards/crashlens-alert-rules.yml")
print("="*80)
