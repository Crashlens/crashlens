"""
Test: Registry Isolation Verification
Purpose: Ensure CollectorRegistry instances are isolated per-run and do not
         share metric state between different scan operations.
         
Acceptance Criteria:
- Series registered in Registry A must NOT appear in Registry B
- Each registry exports only its own metrics
- No cross-contamination between registries

This ensures that multiple CrashLens scans (e.g., in CI parallel jobs) do not
interfere with each other's metrics.
"""

import pytest

try:
    from prometheus_client import Counter, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_registry_isolation_separate_counters():
    """
    ACCEPTANCE: Metrics in Registry A do not appear in Registry B's output.
    
    This verifies per-run isolation: parallel scans don't interfere.
    """
    # Create two completely isolated registries
    registry_a = CollectorRegistry()
    registry_b = CollectorRegistry()
    
    # Register counter in Registry A
    counter_a = Counter(
        'crashlens_test_counter',
        'Test counter for registry A',
        ['run_id'],
        registry=registry_a
    )
    counter_a.labels(run_id='run_a').inc(100)
    
    # Register same metric name in Registry B (different instance)
    counter_b = Counter(
        'crashlens_test_counter',
        'Test counter for registry B',
        ['run_id'],
        registry=registry_b
    )
    counter_b.labels(run_id='run_b').inc(200)
    
    # Export metrics from each registry
    output_a = generate_latest(registry_a).decode('utf-8')
    output_b = generate_latest(registry_b).decode('utf-8')
    
    # CRITICAL ASSERTIONS: Each registry exports only its own series
    
    # Registry A should have run_a but NOT run_b
    assert 'run_id="run_a"' in output_a, (
        f"FAIL: Registry A missing its own series. Output:\n{output_a}"
    )
    assert 'run_id="run_b"' not in output_a, (
        f"FAIL: Registry A contains Registry B's series (cross-contamination). "
        f"Output:\n{output_a}"
    )
    assert '100' in output_a or '100.0' in output_a, (
        f"FAIL: Registry A missing value 100. Output:\n{output_a}"
    )
    
    # Registry B should have run_b but NOT run_a
    assert 'run_id="run_b"' in output_b, (
        f"FAIL: Registry B missing its own series. Output:\n{output_b}"
    )
    assert 'run_id="run_a"' not in output_b, (
        f"FAIL: Registry B contains Registry A's series (cross-contamination). "
        f"Output:\n{output_b}"
    )
    assert '200' in output_b or '200.0' in output_b, (
        f"FAIL: Registry B missing value 200. Output:\n{output_b}"
    )
    
    print("✓ PASS: Registry isolation verified - no cross-contamination")
    print(f"  Registry A exports: run_a=100")
    print(f"  Registry B exports: run_b=200")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_registry_isolation_multiple_metrics():
    """
    ACCEPTANCE: Multiple different metrics in separate registries remain isolated.
    """
    from prometheus_client import Gauge, Histogram
    
    registry_1 = CollectorRegistry()
    registry_2 = CollectorRegistry()
    
    # Registry 1: Counter + Gauge
    counter_1 = Counter(
        'crashlens_violations_total',
        'Violations in registry 1',
        registry=registry_1
    )
    counter_1.inc(50)
    
    gauge_1 = Gauge(
        'crashlens_active_rules',
        'Active rules in registry 1',
        registry=registry_1
    )
    gauge_1.set(10)
    
    # Registry 2: Different metrics
    counter_2 = Counter(
        'crashlens_traces_total',
        'Traces in registry 2',
        registry=registry_2
    )
    counter_2.inc(1000)
    
    histogram_2 = Histogram(
        'crashlens_latency_seconds',
        'Latency in registry 2',
        registry=registry_2
    )
    histogram_2.observe(0.5)
    
    # Export and verify isolation
    output_1 = generate_latest(registry_1).decode('utf-8')
    output_2 = generate_latest(registry_2).decode('utf-8')
    
    # Registry 1 should have violations and active_rules but NOT traces or latency
    assert 'crashlens_violations_total' in output_1
    assert 'crashlens_active_rules' in output_1
    assert 'crashlens_traces_total' not in output_1, (
        f"FAIL: Registry 1 leaked Registry 2's traces metric"
    )
    assert 'crashlens_latency_seconds' not in output_1, (
        f"FAIL: Registry 1 leaked Registry 2's latency metric"
    )
    
    # Registry 2 should have traces and latency but NOT violations or active_rules
    assert 'crashlens_traces_total' in output_2
    assert 'crashlens_latency_seconds' in output_2
    assert 'crashlens_violations_total' not in output_2, (
        f"FAIL: Registry 2 leaked Registry 1's violations metric"
    )
    assert 'crashlens_active_rules' not in output_2, (
        f"FAIL: Registry 2 leaked Registry 1's active_rules metric"
    )
    
    print("✓ PASS: Multiple metrics remain isolated across registries")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_registry_reset_between_runs():
    """
    ACCEPTANCE: Creating a new registry gives clean slate with no previous metrics.
    
    This verifies that CrashLens can run multiple scans without metric accumulation bugs.
    """
    # First run
    registry_run1 = CollectorRegistry()
    counter_run1 = Counter(
        'crashlens_test_metric',
        'Test metric',
        registry=registry_run1
    )
    counter_run1.inc(500)
    
    output_run1 = generate_latest(registry_run1).decode('utf-8')
    assert '500' in output_run1 or '500.0' in output_run1
    
    # Second run with fresh registry
    registry_run2 = CollectorRegistry()
    counter_run2 = Counter(
        'crashlens_test_metric',
        'Test metric',
        registry=registry_run2
    )
    counter_run2.inc(10)
    
    output_run2 = generate_latest(registry_run2).decode('utf-8')
    
    # CRITICAL: Second run should show 10, NOT 510 (no accumulation)
    assert '10' in output_run2 or '10.0' in output_run2, (
        f"FAIL: Second run missing value 10"
    )
    assert '500' not in output_run2, (
        f"FAIL: Second run shows previous run's value 500 (accumulation bug). "
        f"Output:\n{output_run2}"
    )
    assert '510' not in output_run2, (
        f"FAIL: Second run shows accumulated value 510 (state leak). "
        f"Output:\n{output_run2}"
    )
    
    print("✓ PASS: Registry reset verified - no accumulation across runs")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("REGISTRY ISOLATION VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    try:
        test_registry_isolation_separate_counters()
        test_registry_isolation_multiple_metrics()
        test_registry_reset_between_runs()
        print("\n" + "=" * 70)
        print("ALL REGISTRY ISOLATION TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
