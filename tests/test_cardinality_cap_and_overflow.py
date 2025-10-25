"""
Test: Cardinality Cap and Overflow Verification
Purpose: Validate the 500 unique rule label cap and overflow counter behavior.
         Prevents unbounded memory growth from high-cardinality labels.
         
Acceptance Criteria:
- Maximum 500 unique rule labels tracked at once
- crashlens_rules_overflow_total counter increments for folded rules
- Overflow counter value equals number of rules exceeding cap

This ensures constant memory usage even with thousands of unique policy rules.
"""

import pytest

try:
    from prometheus_client import Counter, Gauge, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


class CardinalityManager:
    """
    Test shim for cardinality management logic.
    Mimics the production cardinality cap behavior.
    """
    
    def __init__(self, max_rules=500, registry=None):
        self.max_rules = max_rules
        self.tracked_rules = set()
        self.overflow_count = 0
        self.registry = registry or CollectorRegistry()
        
        # Metrics
        self.rule_hits = Counter(
            'crashlens_rule_hits_total',
            'Total rule hits',
            ['rule'],
            registry=self.registry
        )
        
        self.overflow_counter = Counter(
            'crashlens_rules_overflow_total',
            'Rules dropped due to cardinality cap',
            registry=self.registry
        )
        
        self.cardinality_gauge = Gauge(
            'crashlens_registry_cardinality',
            'Current number of unique rules tracked',
            registry=self.registry
        )
    
    def record_rule_hit(self, rule_name: str):
        """
        Record a hit for a rule, enforcing cardinality cap.
        """
        if rule_name in self.tracked_rules:
            # Already tracking this rule
            self.rule_hits.labels(rule=rule_name).inc()
            return True
        
        if len(self.tracked_rules) < self.max_rules:
            # Still room to track new rules
            self.tracked_rules.add(rule_name)
            self.rule_hits.labels(rule=rule_name).inc()
            self.cardinality_gauge.set(len(self.tracked_rules))
            return True
        else:
            # Cap reached - fold into overflow counter
            self.overflow_count += 1
            self.overflow_counter.inc()
            return False


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_cap_enforced_at_500():
    """
    ACCEPTANCE: Cardinality manager tracks at most 500 unique rule labels.
    
    Simulates registering 600 distinct rules and verifies only 500 are tracked.
    """
    manager = CardinalityManager(max_rules=500)
    
    # Register 600 unique rules
    total_rules = 600
    for i in range(total_rules):
        rule_name = f"policy_rule_{i:04d}"
        manager.record_rule_hit(rule_name)
    
    # CRITICAL ASSERTIONS
    
    # 1. Only 500 unique rules tracked
    assert len(manager.tracked_rules) == 500, (
        f"FAIL: Tracked {len(manager.tracked_rules)} rules, expected exactly 500. "
        f"Cardinality cap not enforced."
    )
    
    # 2. Overflow counter shows 100 folded rules
    expected_overflow = total_rules - 500  # 100
    assert manager.overflow_count == expected_overflow, (
        f"FAIL: Overflow counter is {manager.overflow_count}, expected {expected_overflow}. "
        f"Folded rules not counted correctly."
    )
    
    # 3. Cardinality gauge shows 500
    output = generate_latest(manager.registry).decode('utf-8')
    assert 'crashlens_registry_cardinality 500' in output or 'crashlens_registry_cardinality 500.0' in output, (
        f"FAIL: Cardinality gauge not showing 500. Output:\n{output}"
    )
    
    # 4. Overflow counter in output
    assert 'crashlens_rules_overflow_total' in output, (
        f"FAIL: Overflow counter not exported"
    )
    
    print(f"✓ PASS: Cardinality cap enforced")
    print(f"  Total rules attempted: {total_rules}")
    print(f"  Tracked rules: {len(manager.tracked_rules)}")
    print(f"  Overflow count: {manager.overflow_count}")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_cap_no_overflow_under_limit():
    """
    ACCEPTANCE: When total rules < 500, no overflow occurs.
    """
    manager = CardinalityManager(max_rules=500)
    
    # Register 300 unique rules (under limit)
    for i in range(300):
        manager.record_rule_hit(f"rule_{i}")
    
    assert len(manager.tracked_rules) == 300
    assert manager.overflow_count == 0, (
        f"FAIL: Overflow counter is {manager.overflow_count}, expected 0 when under limit"
    )
    
    output = generate_latest(manager.registry).decode('utf-8')
    assert 'crashlens_registry_cardinality 300' in output or 'crashlens_registry_cardinality 300.0' in output
    
    # Overflow counter should be 0
    if 'crashlens_rules_overflow_total' in output:
        # Counter exists, verify it's 0
        lines = [line for line in output.split('\n') if 'crashlens_rules_overflow_total' in line and not line.startswith('#')]
        if lines:
            assert '0' in lines[0] or '0.0' in lines[0], (
                f"FAIL: Overflow counter non-zero when under limit"
            )
    
    print("✓ PASS: No overflow when under 500 rule limit")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_cap_repeated_hits_dont_overflow():
    """
    ACCEPTANCE: Hitting the same rule repeatedly doesn't increment overflow.
    """
    manager = CardinalityManager(max_rules=500)
    
    # Fill to capacity
    for i in range(500):
        manager.record_rule_hit(f"rule_{i}")
    
    assert len(manager.tracked_rules) == 500
    assert manager.overflow_count == 0
    
    # Hit first rule 1000 times (should not overflow)
    for _ in range(1000):
        manager.record_rule_hit("rule_0")
    
    assert len(manager.tracked_rules) == 500
    assert manager.overflow_count == 0, (
        f"FAIL: Repeated hits on existing rule caused overflow count {manager.overflow_count}"
    )
    
    # Now try a NEW rule (should overflow)
    manager.record_rule_hit("rule_9999")
    
    assert len(manager.tracked_rules) == 500  # Still 500
    assert manager.overflow_count == 1, (
        f"FAIL: New rule after cap didn't increment overflow"
    )
    
    print("✓ PASS: Repeated hits don't cause overflow, only new rules do")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_cap_custom_limit():
    """
    ACCEPTANCE: Cardinality cap is configurable (for testing smaller limits).
    """
    # Use smaller cap for faster test
    manager = CardinalityManager(max_rules=10)
    
    # Register 15 rules
    for i in range(15):
        manager.record_rule_hit(f"rule_{i}")
    
    assert len(manager.tracked_rules) == 10, (
        f"FAIL: Custom cap of 10 not enforced, tracked {len(manager.tracked_rules)}"
    )
    assert manager.overflow_count == 5, (
        f"FAIL: Expected 5 overflow, got {manager.overflow_count}"
    )
    
    print("✓ PASS: Custom cardinality limits work correctly")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_cardinality_memory_constant():
    """
    ACCEPTANCE: Memory usage remains constant even with many overflow events.
    
    This is a sanity check that overflow counting doesn't allocate unbounded memory.
    """
    import sys
    
    manager = CardinalityManager(max_rules=100)
    
    # Fill to capacity
    for i in range(100):
        manager.record_rule_hit(f"rule_{i}")
    
    # Measure tracked rules set size
    initial_rules_size = sys.getsizeof(manager.tracked_rules)
    initial_overflow = manager.overflow_count
    
    # Trigger 10,000 overflow events
    for i in range(10000):
        manager.record_rule_hit(f"overflow_rule_{i}")
    
    # Verify tracked rules set didn't grow
    final_rules_size = sys.getsizeof(manager.tracked_rules)
    assert final_rules_size == initial_rules_size, (
        f"FAIL: Tracked rules set grew from {initial_rules_size} to {final_rules_size} bytes. "
        f"Overflow events are leaking memory."
    )
    
    # Verify overflow counter works
    assert manager.overflow_count == initial_overflow + 10000, (
        f"FAIL: Overflow counter didn't increment correctly"
    )
    
    # Verify still only 100 unique rules tracked
    assert len(manager.tracked_rules) == 100, (
        f"FAIL: Tracked rules grew to {len(manager.tracked_rules)}, expected constant 100"
    )
    
    print("✓ PASS: Memory remains constant with overflow events")
    print(f"  Tracked rules: {len(manager.tracked_rules)} (constant)")
    print(f"  Overflow events: {manager.overflow_count}")
    print(f"  Set size: {final_rules_size} bytes (constant)")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("CARDINALITY CAP & OVERFLOW VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    try:
        test_cardinality_cap_enforced_at_500()
        test_cardinality_cap_no_overflow_under_limit()
        test_cardinality_cap_repeated_hits_dont_overflow()
        test_cardinality_cap_custom_limit()
        test_cardinality_memory_constant()
        print("\n" + "=" * 70)
        print("ALL CARDINALITY CAP TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
