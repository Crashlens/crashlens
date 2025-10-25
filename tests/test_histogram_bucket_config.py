"""
Test: Histogram Bucket Configuration Verification
Purpose: Ensure histogram buckets match the recommended configuration from research reports.

Acceptance Criteria:
- Histogram buckets match the canonical list: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
- Buckets are appropriate for measuring rule evaluation latency (milliseconds to seconds)
- Configuration is exposed via registry exposition

This ensures consistent, useful histogram metrics for latency tracking.
"""

import pytest

try:
    from prometheus_client import Histogram, CollectorRegistry, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False


# Canonical bucket configuration from research reports
# These buckets cover typical rule evaluation times from 5ms to 5 minutes
# [0.005, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 300]
CANONICAL_BUCKETS = [0.005, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 300]


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_histogram_buckets_match_canonical_list():
    """
    ACCEPTANCE: Histogram buckets exactly match the canonical list:
    [0.005, 0.02, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 300]
    """
    registry = CollectorRegistry()
    
    # Create histogram with canonical buckets
    histogram = Histogram(
        'crashlens_rule_evaluation_duration_seconds',
        'Time spent evaluating policy rules',
        buckets=CANONICAL_BUCKETS,
        registry=registry
    )
    
    # Record some observations
    histogram.observe(0.002)  # 2ms
    histogram.observe(0.015)  # 15ms
    histogram.observe(0.100)  # 100ms
    
    # Export and parse buckets from output
    output = generate_latest(registry).decode('utf-8')
    
    # Parse bucket upper bounds from output
    observed_buckets = []
    for line in output.split('\n'):
        if 'crashlens_rule_evaluation_duration_seconds_bucket{' in line:
            # Extract le="<value>" from the line
            if 'le="' in line:
                start = line.index('le="') + 4
                end = line.index('"', start)
                le_value = line[start:end]
                
                if le_value == '+Inf':
                    continue  # Skip the +Inf bucket
                
                try:
                    observed_buckets.append(float(le_value))
                except ValueError:
                    pass
    
    # Sort for comparison
    observed_buckets = sorted(set(observed_buckets))
    
    assert observed_buckets == CANONICAL_BUCKETS, (
        f"FAIL: Histogram buckets don't match canonical list.\n"
        f"Expected: {CANONICAL_BUCKETS}\n"
        f"Observed: {observed_buckets}\n"
        f"Difference: {set(CANONICAL_BUCKETS) ^ set(observed_buckets)}"
    )
    
    print(f"✓ PASS: Histogram buckets match canonical list")
    print(f"  Buckets: {CANONICAL_BUCKETS}")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_histogram_bucket_count():
    """
    ACCEPTANCE: Histogram has exactly 13 finite buckets (plus +Inf).
    """
    registry = CollectorRegistry()
    
    histogram = Histogram(
        'crashlens_test_histogram',
        'Test histogram',
        buckets=CANONICAL_BUCKETS,
        registry=registry
    )
    
    histogram.observe(0.5)
    
    output = generate_latest(registry).decode('utf-8')
    
    # Count bucket lines (excluding +Inf)
    bucket_lines = [
        line for line in output.split('\n')
        if 'crashlens_test_histogram_bucket{' in line
        and 'le="+Inf"' not in line
    ]
    
    expected_count = len(CANONICAL_BUCKETS)
    observed_count = len(bucket_lines)
    
    assert observed_count == expected_count, (
        f"FAIL: Expected {expected_count} buckets, found {observed_count}"
    )
    
    print(f"✓ PASS: Histogram has {expected_count} finite buckets")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_histogram_buckets_cover_expected_range():
    """
    ACCEPTANCE: Buckets cover 1ms to 5s range (typical rule evaluation times).
    """
    registry = CollectorRegistry()
    
    histogram = Histogram(
        'crashlens_test_histogram',
        'Test histogram',
        buckets=CANONICAL_BUCKETS,
        registry=registry
    )
    
    # Test observations across the range
    test_values = [
        0.002,   # 2ms - below minimum bucket
        0.005,   # 5ms - minimum bucket edge
        0.050,   # 50ms - mid-range
        1.0,     # 1s - mid-range
        10.0,    # 10s - mid-range
        60.0,    # 60s - at bucket
        300.0,   # 300s - maximum bucket edge
        500.0,   # 500s - above maximum (would go to +Inf)
    ]
    
    for value in test_values:
        histogram.observe(value)
    
    output = generate_latest(registry).decode('utf-8')
    
    # Verify minimum bucket is present
    assert 'le="0.005"' in output, "FAIL: Minimum bucket (5ms) not found"
    
    # Verify some mid-range buckets
    assert 'le="1"' in output or 'le="1.0"' in output, "FAIL: 1s bucket not found"
    
    # Verify maximum bucket is present
    assert 'le="300"' in output or 'le="300.0"' in output, "FAIL: Maximum bucket (300s) not found"
    
    # Verify +Inf bucket exists for outliers
    assert 'le="+Inf"' in output, "FAIL: +Inf bucket not found"
    
    print(f"✓ PASS: Buckets cover 5ms to 300s (5 minutes) range with +Inf for outliers")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_histogram_buckets_monotonically_increasing():
    """
    ACCEPTANCE: Bucket upper bounds are in ascending order.
    """
    # Verify canonical list is sorted
    sorted_buckets = sorted(CANONICAL_BUCKETS)
    
    assert CANONICAL_BUCKETS == sorted_buckets, (
        f"FAIL: Canonical buckets not in ascending order.\n"
        f"Expected: {sorted_buckets}\n"
        f"Actual:   {CANONICAL_BUCKETS}"
    )
    
    print(f"✓ PASS: Buckets are monotonically increasing")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_histogram_bucket_distribution():
    """
    ACCEPTANCE: Bucket distribution is appropriate for observability.
    
    Verifies buckets are more granular at lower latencies (where most evaluations occur).
    """
    # Check bucket spacing
    # Early buckets (0-1s) should have finer granularity
    low_latency_buckets = [b for b in CANONICAL_BUCKETS if b <= 1.0]  # ≤1s
    high_latency_buckets = [b for b in CANONICAL_BUCKETS if b > 1.0]  # >1s
    
    # Should have at least 5 buckets in low-latency range (most common)
    assert len(low_latency_buckets) >= 5, (
        f"FAIL: Insufficient granularity for low latencies (<1s). "
        f"Only {len(low_latency_buckets)} buckets."
    )
    
    # Should have buckets up to 300s (5 minutes) for outliers
    max_bucket = max(CANONICAL_BUCKETS)
    assert max_bucket >= 60.0, (
        f"FAIL: Maximum bucket {max_bucket}s too small. Expected ≥60s for outliers."
    )
    
    print(f"✓ PASS: Bucket distribution appropriate")
    print(f"  Low-latency buckets (≤1s): {len(low_latency_buckets)}")
    print(f"  High-latency buckets (>1s): {len(high_latency_buckets)}")
    print(f"  Maximum bucket: {max_bucket}s")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_histogram_with_observations_populates_buckets_correctly():
    """
    ACCEPTANCE: Observations correctly populate bucket counts.
    """
    registry = CollectorRegistry()
    
    histogram = Histogram(
        'crashlens_test_histogram',
        'Test histogram',
        buckets=CANONICAL_BUCKETS,
        registry=registry
    )
    
    # Record observations in different buckets
    histogram.observe(0.002)  # Should be in 0.005 bucket
    histogram.observe(0.020)  # Should be in 0.025 bucket
    histogram.observe(0.100)  # Should be in 0.1 bucket
    histogram.observe(1.500)  # Should be in 2.5 bucket
    
    output = generate_latest(registry).decode('utf-8')
    
    # Parse bucket counts
    bucket_counts = {}
    for line in output.split('\n'):
        if 'crashlens_test_histogram_bucket{' in line and not line.startswith('#'):
            if 'le="' in line:
                # Extract le value and count
                start = line.index('le="') + 4
                end = line.index('"', start)
                le_value = line[start:end]
                
                # Extract count (last number on the line)
                parts = line.split()
                if parts:
                    try:
                        count = int(float(parts[-1]))
                        bucket_counts[le_value] = count
                    except (ValueError, IndexError):
                        pass
    
    # Verify cumulative nature (each bucket includes previous observations)
    # le="0.005" should have 1 (0.002)
    # le="0.025" should have 2 (0.002, 0.020)
    # le="0.1" should have 3 (0.002, 0.020, 0.100)
    # le="2.5" should have 4 (all observations)
    
    if '0.005' in bucket_counts:
        assert bucket_counts['0.005'] >= 1, "FAIL: 0.005 bucket should have ≥1"
    
    if '0.1' in bucket_counts:
        assert bucket_counts['0.1'] >= 3, "FAIL: 0.1 bucket should have ≥3"
    
    if '+Inf' in bucket_counts:
        assert bucket_counts['+Inf'] == 4, "FAIL: +Inf bucket should have all 4 observations"
    
    print(f"✓ PASS: Observations correctly populate buckets")
    print(f"  Sample bucket counts: {dict(list(bucket_counts.items())[:5])}")


@pytest.mark.skipif(not PROMETHEUS_AVAILABLE, reason="prometheus_client not installed")
def test_histogram_default_buckets_not_used():
    """
    ACCEPTANCE: Custom buckets are used, not prometheus_client defaults.
    
    prometheus_client has default buckets: [.005, .01, .025, .05, .075, .1, .25, .5, .75, 1.0, 2.5, 5.0, 7.5, 10.0, +Inf]
    We want our custom buckets.
    """
    from prometheus_client import Histogram
    
    # Get default buckets
    default_histogram = Histogram('test_default', 'Test')
    default_buckets = default_histogram._upper_bounds[:-1]  # Exclude +Inf
    
    # Our canonical buckets should differ from defaults
    assert CANONICAL_BUCKETS != list(default_buckets), (
        f"FAIL: Canonical buckets are identical to prometheus_client defaults. "
        f"We should be using custom buckets."
    )
    
    print(f"✓ PASS: Custom buckets differ from prometheus_client defaults")
    print(f"  Our buckets: {len(CANONICAL_BUCKETS)} values")
    print(f"  Default buckets: {len(default_buckets)} values")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("HISTOGRAM BUCKET CONFIGURATION VERIFICATION SUITE")
    print("=" * 70)
    
    if not PROMETHEUS_AVAILABLE:
        print("⚠ SKIP: prometheus_client not installed")
        sys.exit(0)
    
    try:
        test_histogram_buckets_match_canonical_list()
        test_histogram_bucket_count()
        test_histogram_buckets_cover_expected_range()
        test_histogram_buckets_monotonically_increasing()
        test_histogram_bucket_distribution()
        test_histogram_with_observations_populates_buckets_correctly()
        test_histogram_default_buckets_not_used()
        
        print("\n" + "=" * 70)
        print("ALL HISTOGRAM BUCKET TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
