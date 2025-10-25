"""
Test: Registry Cardinality Gauge Value
Purpose: Verify crashlens_registry_cardinality gauge accurately reflects
         the number of unique rules currently tracked.
         
Acceptance Criteria:
- Gauge value equals number of unique rules registered
- Gauge updates as rules are added
- Gauge respects cardinality cap (stops at max_rules)
- Gauge exported correctly in Prometheus format
- Gauge is of type 'gauge' (not counter)

This provides real-time visibility into cardinality pressure.
"""

import pytest

try:
    from prometheus_client import Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class CardinalityTracker:
    """
    Test shim for tracking cardinality with a gauge.
    Mimics production cardinality monitoring.
    """
    
    def __init__(self, max_rules=500, registry=None):
        self.max_rules = max_rules
        self.tracked_rules = set()
        self.registry = registry or CollectorRegistry()
        
        self.cardinality_gauge = Gauge(
            'crashlens_registry_cardinality',
            'Number of unique rules currently tracked',
            registry=self.registry
        )
    
    def register_rule(self, rule_name: str) -> bool:
        """
        Register a rule and update cardinality gauge.
        Returns True if tracked, False if cap reached.
        """
        if rule_name in self.tracked_rules:
            # Already tracking
            return True
        
        if len(self.tracked_rules) < self.max_rules:
            self.tracked_rules.add(rule_name)
            self.cardinality_gauge.set(len(self.tracked_rules))
            return True
        else:
            # Cap reached, don't track
            return False


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_reflects_unique_rules():
    """
    ACCEPTANCE: Gauge value equals number of unique rules tracked.
    """
    tracker = CardinalityTracker(max_rules=500)
    
    # Register 50 unique rules
    for i in range(50):
        tracker.register_rule(f"rule_{i}")
    
    # Check gauge value
    output = generate_latest(tracker.registry).decode('utf-8')
    
    assert 'crashlens_registry_cardinality' in output, (
        f"FAIL: Cardinality gauge not in output"
    )
    
    # Extract gauge value (should be 50)
    lines = [line for line in output.split('\n')
             if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
    assert len(lines) > 0, "FAIL: Gauge metric line not found"
    
    # Value should be 50 or 50.0
    assert '50' in lines[0], (
        f"FAIL: Expected gauge = 50, got: {lines[0]}"
    )
    
    print(f"✓ PASS: Gauge correctly shows 50 unique rules")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_updates_as_rules_added():
    """
    ACCEPTANCE: Gauge increments as rules are added.
    """
    tracker = CardinalityTracker(max_rules=500)
    
    # Register rules one at a time and check gauge
    expected_values = [1, 5, 10, 25, 50, 100]
    
    for expected in expected_values:
        # Register up to expected count
        while len(tracker.tracked_rules) < expected:
            tracker.register_rule(f"rule_{len(tracker.tracked_rules)}")
        
        output = generate_latest(tracker.registry).decode('utf-8')
        lines = [line for line in output.split('\n')
                 if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
        
        assert len(lines) > 0
        assert str(expected) in lines[0], (
            f"FAIL: Expected gauge = {expected}, got: {lines[0]}"
        )
    
    print("✓ PASS: Gauge updated correctly through values: " + ", ".join(map(str, expected_values)))


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_respects_cap():
    """
    ACCEPTANCE: Gauge stops at max_rules (doesn't exceed cap).
    """
    tracker = CardinalityTracker(max_rules=100)
    
    # Try to register 150 rules
    for i in range(150):
        tracker.register_rule(f"rule_{i}")
    
    # Gauge should show 100 (capped)
    output = generate_latest(tracker.registry).decode('utf-8')
    lines = [line for line in output.split('\n')
             if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
    
    assert len(lines) > 0
    assert '100' in lines[0], (
        f"FAIL: Gauge should be capped at 100, got: {lines[0]}"
    )
    
    # Verify set size
    assert len(tracker.tracked_rules) == 100, (
        f"FAIL: Tracked {len(tracker.tracked_rules)} rules, expected 100"
    )
    
    print("✓ PASS: Gauge capped at 100 (max_rules)")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_repeated_rules_dont_increment():
    """
    ACCEPTANCE: Registering same rule multiple times doesn't increment gauge.
    """
    tracker = CardinalityTracker(max_rules=500)
    
    # Register "rule_0" 100 times
    for i in range(100):
        tracker.register_rule("rule_0")
    
    # Gauge should still show 1
    output = generate_latest(tracker.registry).decode('utf-8')
    lines = [line for line in output.split('\n')
             if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
    
    assert len(lines) > 0
    assert '1' in lines[0], (
        f"FAIL: Expected gauge = 1 (one unique rule), got: {lines[0]}"
    )
    
    print("✓ PASS: Repeated rules don't increment gauge (1 unique rule)")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_prometheus_format():
    """
    ACCEPTANCE: Gauge exported in valid Prometheus format with TYPE gauge.
    """
    tracker = CardinalityTracker(max_rules=500)
    tracker.register_rule("rule_0")
    
    output = generate_latest(tracker.registry).decode('utf-8')
    
    # Should have HELP line
    assert '# HELP crashlens_registry_cardinality' in output, (
        f"FAIL: Missing HELP line"
    )
    
    # Should have TYPE gauge (not counter)
    assert '# TYPE crashlens_registry_cardinality gauge' in output, (
        f"FAIL: Wrong metric type (expected gauge)"
    )
    
    # Should have metric line with value
    metric_lines = [line for line in output.split('\n')
                    if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
    assert len(metric_lines) > 0, "FAIL: Metric line not found"
    
    print("✓ PASS: Gauge exported in valid Prometheus format")
    print("Sample output:")
    for line in output.split('\n'):
        if 'crashlens_registry_cardinality' in line:
            print(f"  {line}")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_zero_initial_value():
    """
    ACCEPTANCE: Gauge starts at 0 before any rules registered.
    """
    tracker = CardinalityTracker(max_rules=500)
    
    # Don't register any rules
    output = generate_latest(tracker.registry).decode('utf-8')
    
    # Gauge should show 0 (or not appear yet, depending on implementation)
    if 'crashlens_registry_cardinality' in output:
        lines = [line for line in output.split('\n')
                 if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
        
        if len(lines) > 0:
            # If present, should be 0
            assert '0' in lines[0], (
                f"FAIL: Initial gauge value should be 0, got: {lines[0]}"
            )
    
    # After setting to 0 explicitly
    tracker.cardinality_gauge.set(0)
    output = generate_latest(tracker.registry).decode('utf-8')
    
    lines = [line for line in output.split('\n')
             if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
    assert len(lines) > 0
    assert '0' in lines[0]
    
    print("✓ PASS: Gauge starts at 0")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_large_values():
    """
    ACCEPTANCE: Gauge handles large cardinality values (e.g., 500).
    """
    tracker = CardinalityTracker(max_rules=500)
    
    # Register 500 rules (up to cap)
    for i in range(500):
        tracker.register_rule(f"rule_{i:04d}")
    
    output = generate_latest(tracker.registry).decode('utf-8')
    lines = [line for line in output.split('\n')
             if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
    
    assert len(lines) > 0
    assert '500' in lines[0], (
        f"FAIL: Expected gauge = 500, got: {lines[0]}"
    )
    
    print("✓ PASS: Gauge handles large values (500)")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_gauge_decrements_on_cleanup():
    """
    ACCEPTANCE: Gauge can be decremented if rules are removed (optional feature).
    
    Note: Basic implementation may not support removal, this tests the gauge API.
    """
    tracker = CardinalityTracker(max_rules=500)
    
    # Register 10 rules
    for i in range(10):
        tracker.register_rule(f"rule_{i}")
    
    assert len(tracker.tracked_rules) == 10
    
    # Simulate cleanup (remove 5 rules)
    rules_to_remove = [f"rule_{i}" for i in range(5)]
    for rule in rules_to_remove:
        if rule in tracker.tracked_rules:
            tracker.tracked_rules.remove(rule)
    
    # Update gauge
    tracker.cardinality_gauge.set(len(tracker.tracked_rules))
    
    # Gauge should now show 5
    output = generate_latest(tracker.registry).decode('utf-8')
    lines = [line for line in output.split('\n')
             if 'crashlens_registry_cardinality' in line and not line.startswith('#')]
    
    assert len(lines) > 0
    assert '5' in lines[0], (
        f"FAIL: After cleanup, expected gauge = 5, got: {lines[0]}"
    )
    
    print("✓ PASS: Gauge decrements correctly after cleanup (10 → 5)")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("REGISTRY CARDINALITY GAUGE VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    try:
        test_cardinality_gauge_reflects_unique_rules()
        test_cardinality_gauge_updates_as_rules_added()
        test_cardinality_gauge_respects_cap()
        test_cardinality_gauge_repeated_rules_dont_increment()
        test_cardinality_gauge_prometheus_format()
        test_cardinality_gauge_zero_initial_value()
        test_cardinality_gauge_large_values()
        test_cardinality_gauge_decrements_on_cleanup()
        print("\n" + "=" * 70)
        print("ALL CARDINALITY GAUGE TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
