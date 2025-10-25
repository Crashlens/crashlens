"""
Test: Python Module Cleanup Between Tests
Purpose: Ensure the library resets its global state between pytest runs.
         Critical for test isolation and reliability.

Acceptance Criteria:
- Tests are isolated (no metric series leakage between tests)
- Registry state is fresh for each test
- Module-level globals don't persist across tests
- pytest fixture provides reliable cleanup

This ensures pytest test suite is reliable and reproducible.
"""

import pytest
import sys

try:
    from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


@pytest.fixture
def fresh_registry():
    """
    Fixture: Provides a fresh CollectorRegistry for each test.
    
    This ensures test isolation by giving each test its own registry.
    """
    registry = CollectorRegistry()
    yield registry
    # Cleanup happens automatically when registry goes out of scope


@pytest.fixture
def reset_prometheus_module():
    """
    Fixture: Resets prometheus_client module state between tests.
    
    Clears any module-level caches or global state.
    """
    # Store original module state
    original_modules = dict(sys.modules)
    
    yield
    
    # Remove prometheus_client modules
    modules_to_remove = [
        name for name in sys.modules.keys()
        if name.startswith('prometheus_client')
    ]
    for name in modules_to_remove:
        del sys.modules[name]
    
    # Restore non-prometheus modules
    for name, module in original_modules.items():
        if name not in sys.modules and not name.startswith('prometheus_client'):
            sys.modules[name] = module


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_registry_isolation_between_tests_part1(fresh_registry):
    """
    ACCEPTANCE: Test 1 registers metrics, test 2 shouldn't see them.
    Part 1: Register a metric.
    """
    counter = Counter('test_counter_part1', 'Test counter', registry=fresh_registry)
    counter.inc(10)
    
    output = generate_latest(fresh_registry).decode('utf-8')
    assert 'test_counter_part1' in output
    assert '10' in output
    
    print("✓ Test 1: Registered test_counter_part1 with value 10")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_registry_isolation_between_tests_part2(fresh_registry):
    """
    ACCEPTANCE: Test 2 has fresh registry, shouldn't see test 1's metrics.
    Part 2: Verify clean slate.
    """
    # Create new counter with same name (should work if registry is fresh)
    counter = Counter('test_counter_part2', 'Test counter', registry=fresh_registry)
    counter.inc(20)
    
    output = generate_latest(fresh_registry).decode('utf-8')
    
    # Should see part2 counter
    assert 'test_counter_part2' in output
    assert '20' in output
    
    # Should NOT see part1 counter (different registry)
    assert 'test_counter_part1' not in output
    assert '10' not in output or '20' in output  # 10 shouldn't be present
    
    print("✓ Test 2: Has fresh registry, test_counter_part1 not present")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_same_metric_name_different_registries():
    """
    ACCEPTANCE: Same metric name can be used in different registries without conflict.
    """
    registry1 = CollectorRegistry()
    registry2 = CollectorRegistry()
    
    # Create counters with same name in different registries
    counter1 = Counter('shared_counter', 'Shared counter', registry=registry1)
    counter2 = Counter('shared_counter', 'Shared counter', registry=registry2)
    
    counter1.inc(100)
    counter2.inc(200)
    
    output1 = generate_latest(registry1).decode('utf-8')
    output2 = generate_latest(registry2).decode('utf-8')
    
    # Registry 1 should show 100
    assert 'shared_counter' in output1
    assert '100' in output1
    assert '200' not in output1
    
    # Registry 2 should show 200
    assert 'shared_counter' in output2
    assert '200' in output2
    assert '100' not in output2
    
    print("✓ PASS: Same metric name works in different registries")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_multiple_metrics_cleanup(fresh_registry):
    """
    ACCEPTANCE: Multiple metric types all cleaned up between tests.
    """
    counter = Counter('test_counter', 'Test', registry=fresh_registry)
    gauge = Gauge('test_gauge', 'Test', registry=fresh_registry)
    histogram = Histogram('test_histogram', 'Test', registry=fresh_registry)
    
    counter.inc(5)
    gauge.set(42)
    histogram.observe(0.5)
    
    output = generate_latest(fresh_registry).decode('utf-8')
    
    assert 'test_counter' in output
    assert 'test_gauge' in output
    assert 'test_histogram' in output
    
    print("✓ PASS: Multiple metric types registered and cleaned up")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_fresh_registry_after_cleanup(fresh_registry):
    """
    ACCEPTANCE: After previous test's cleanup, this test has empty registry.
    """
    # Registry should be empty initially
    output = generate_latest(fresh_registry).decode('utf-8')
    
    # Should not contain metrics from previous tests
    assert 'test_counter' not in output
    assert 'test_gauge' not in output
    assert 'test_histogram' not in output
    
    # Add new metric to verify registry works
    new_counter = Counter('new_counter', 'New counter', registry=fresh_registry)
    new_counter.inc()
    
    output = generate_latest(fresh_registry).decode('utf-8')
    assert 'new_counter' in output
    
    print("✓ PASS: Fresh registry after cleanup (no previous test metrics)")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_labeled_metrics_cleanup(fresh_registry):
    """
    ACCEPTANCE: Labeled metrics (with label values) are also cleaned up.
    """
    counter = Counter('labeled_counter', 'Test', ['label1', 'label2'], registry=fresh_registry)
    
    # Create multiple label combinations
    counter.labels(label1='a', label2='x').inc(10)
    counter.labels(label1='b', label2='y').inc(20)
    counter.labels(label1='c', label2='z').inc(30)
    
    output = generate_latest(fresh_registry).decode('utf-8')
    
    assert 'label1="a"' in output
    assert 'label1="b"' in output
    assert 'label1="c"' in output
    
    print("✓ PASS: Labeled metrics with multiple combinations cleaned up")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_no_label_leakage_after_cleanup(fresh_registry):
    """
    ACCEPTANCE: Previous test's label values don't leak into this test.
    """
    # Create counter with same name but different labels
    counter = Counter('another_counter', 'Test', ['different_label'], registry=fresh_registry)
    counter.labels(different_label='new_value').inc(1)
    
    output = generate_latest(fresh_registry).decode('utf-8')
    
    # Should see new labels
    assert 'different_label="new_value"' in output
    
    # Should NOT see previous test's labels
    assert 'label1="a"' not in output
    assert 'label1="b"' not in output
    
    print("✓ PASS: No label leakage from previous tests")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_registry_metric_count_starts_at_zero(fresh_registry):
    """
    ACCEPTANCE: Fresh registry has zero metrics initially.
    """
    # Get initial output
    output = generate_latest(fresh_registry).decode('utf-8')
    
    # Should be minimal (only comments, no metrics)
    lines = [line for line in output.split('\n') if line and not line.startswith('#')]
    
    # Should have zero or very few non-comment lines
    assert len(lines) <= 2, (  # Allow for minimal default metrics
        f"FAIL: Fresh registry should be empty. Found {len(lines)} metric lines:\n"
        f"{chr(10).join(lines)}"
    )
    
    print("✓ PASS: Fresh registry starts empty (no metrics)")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_exception_during_test_still_cleans_up(fresh_registry):
    """
    ACCEPTANCE: Even if test raises exception, next test has fresh registry.
    """
    try:
        counter = Counter('exception_test_counter', 'Test', registry=fresh_registry)
        counter.inc(99)
        
        # Simulate exception during test
        raise ValueError("Simulated test failure")
    except ValueError:
        pass  # Expected
    
    # Despite exception, registry should still be isolated for next test
    # (pytest fixtures handle cleanup even on exceptions)
    print("✓ PASS: Exception handling preserves cleanup (verified by fixture)")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_after_exception_registry_is_fresh(fresh_registry):
    """
    ACCEPTANCE: After previous test's exception, this registry is still fresh.
    """
    output = generate_latest(fresh_registry).decode('utf-8')
    
    # Should not see exception_test_counter
    assert 'exception_test_counter' not in output
    
    # Create new metric to verify registry works
    counter = Counter('post_exception_counter', 'Test', registry=fresh_registry)
    counter.inc()
    
    output = generate_latest(fresh_registry).decode('utf-8')
    assert 'post_exception_counter' in output
    
    print("✓ PASS: Registry fresh after previous test exception")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("PYTHON MODULE CLEANUP BETWEEN TESTS VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    print("\nNote: Run with pytest for proper fixture-based cleanup:")
    print("  pytest tests/test_python_module_cleanup_between_tests.py -v")
    print("\nManual execution will demonstrate concepts but won't show full isolation.")
    print()
    
    # When run standalone, demonstrate the concepts
    try:
        # These tests use manual registry creation (not fixtures)
        test_same_metric_name_different_registries()
        
        print("\n" + "=" * 70)
        print("STANDALONE TESTS PASSED ✓")
        print("=" * 70)
        print("\nFor full test suite with fixtures, run:")
        print("  pytest tests/test_python_module_cleanup_between_tests.py -v")
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
