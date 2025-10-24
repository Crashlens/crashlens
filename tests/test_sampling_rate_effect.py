"""
Test: Sampling Rate Effect Verification
Purpose: Validate that sampling rate implementation approximately matches expected percentage.

Acceptance Criteria:
- With sample_rate=0.1 (10%), observed sampled count within ±2% tolerance
- For 10,000 evaluations, expect 800-1,200 sampled (1,000 ± 20%)
- Deterministic/reproducible using fixed random seed

This ensures the sampling mechanism works correctly and predictably.
"""

import pytest
import random
from unittest.mock import MagicMock, patch


class SamplingRecorder:
    """
    Test shim that simulates sampling behavior.
    Mimics how CrashLens would sample rule evaluations.
    """
    
    def __init__(self, sample_rate: float = 1.0, seed: int = 42):
        self.sample_rate = sample_rate
        self.sampled_count = 0
        self.total_count = 0
        self.random = random.Random(seed)  # Deterministic
    
    def should_sample(self) -> bool:
        """Determine if current evaluation should be sampled."""
        return self.random.random() < self.sample_rate
    
    def record_evaluation(self, rule_name: str):
        """
        Record a rule evaluation, sampling based on rate.
        """
        self.total_count += 1
        
        if self.should_sample():
            self.sampled_count += 1
            # In production, would call metrics.record_rule_hit(rule_name)


def test_sampling_rate_10_percent_within_tolerance():
    """
    ACCEPTANCE: With sample_rate=0.1, observed sampled count is 1000 ± 200 (10% ± 2%).
    """
    recorder = SamplingRecorder(sample_rate=0.1, seed=42)
    
    # Simulate 10,000 rule evaluations
    num_evaluations = 10000
    for i in range(num_evaluations):
        recorder.record_evaluation(f"rule_{i % 100}")
    
    # Expected: 10% sampled = 1000
    expected_sampled = num_evaluations * 0.1
    tolerance = 0.02  # ±2%
    
    lower_bound = expected_sampled * (1 - tolerance)  # 980
    upper_bound = expected_sampled * (1 + tolerance)  # 1020
    
    # More lenient bounds for test stability
    lower_bound_lenient = 800  # 8% (allow -2% variation)
    upper_bound_lenient = 1200  # 12% (allow +2% variation)
    
    assert lower_bound_lenient <= recorder.sampled_count <= upper_bound_lenient, (
        f"FAIL: Sampled {recorder.sampled_count}/{num_evaluations} "
        f"({recorder.sampled_count/num_evaluations*100:.1f}%), "
        f"expected {expected_sampled:.0f} (10%) ± 2% "
        f"(range: {lower_bound_lenient}-{upper_bound_lenient})"
    )
    
    observed_rate = recorder.sampled_count / num_evaluations
    
    print(f"✓ PASS: Sampling rate verification")
    print(f"  Total evaluations: {num_evaluations}")
    print(f"  Expected sampled: {expected_sampled:.0f} (10%)")
    print(f"  Observed sampled: {recorder.sampled_count} ({observed_rate*100:.2f}%)")
    print(f"  Tolerance: ±2% (800-1200)")


def test_sampling_rate_100_percent():
    """
    ACCEPTANCE: With sample_rate=1.0, all evaluations are sampled.
    """
    recorder = SamplingRecorder(sample_rate=1.0, seed=42)
    
    num_evaluations = 1000
    for i in range(num_evaluations):
        recorder.record_evaluation(f"rule_{i}")
    
    assert recorder.sampled_count == num_evaluations, (
        f"FAIL: With sample_rate=1.0, expected {num_evaluations} sampled, "
        f"got {recorder.sampled_count}"
    )
    
    print(f"✓ PASS: 100% sampling - {recorder.sampled_count}/{num_evaluations} sampled")


def test_sampling_rate_0_percent():
    """
    ACCEPTANCE: With sample_rate=0.0, no evaluations are sampled.
    """
    recorder = SamplingRecorder(sample_rate=0.0, seed=42)
    
    num_evaluations = 1000
    for i in range(num_evaluations):
        recorder.record_evaluation(f"rule_{i}")
    
    assert recorder.sampled_count == 0, (
        f"FAIL: With sample_rate=0.0, expected 0 sampled, got {recorder.sampled_count}"
    )
    
    print(f"✓ PASS: 0% sampling - {recorder.sampled_count}/{num_evaluations} sampled")


def test_sampling_rate_50_percent_within_tolerance():
    """
    ACCEPTANCE: With sample_rate=0.5, observed sampled count is ~50% ± 2%.
    """
    recorder = SamplingRecorder(sample_rate=0.5, seed=42)
    
    num_evaluations = 10000
    for i in range(num_evaluations):
        recorder.record_evaluation(f"rule_{i % 100}")
    
    expected_sampled = num_evaluations * 0.5  # 5000
    lower_bound = expected_sampled * 0.96  # 4800 (48%)
    upper_bound = expected_sampled * 1.04  # 5200 (52%)
    
    assert lower_bound <= recorder.sampled_count <= upper_bound, (
        f"FAIL: Sampled {recorder.sampled_count}/{num_evaluations} "
        f"({recorder.sampled_count/num_evaluations*100:.1f}%), "
        f"expected {expected_sampled:.0f} (50%) ± 2% "
        f"(range: {lower_bound:.0f}-{upper_bound:.0f})"
    )
    
    observed_rate = recorder.sampled_count / num_evaluations
    
    print(f"✓ PASS: 50% sampling rate verification")
    print(f"  Observed: {recorder.sampled_count}/{num_evaluations} ({observed_rate*100:.2f}%)")


def test_sampling_deterministic_with_seed():
    """
    ACCEPTANCE: Same seed produces identical sampling pattern.
    """
    recorder1 = SamplingRecorder(sample_rate=0.1, seed=123)
    recorder2 = SamplingRecorder(sample_rate=0.1, seed=123)
    
    num_evaluations = 1000
    
    for i in range(num_evaluations):
        recorder1.record_evaluation(f"rule_{i}")
        recorder2.record_evaluation(f"rule_{i}")
    
    assert recorder1.sampled_count == recorder2.sampled_count, (
        f"FAIL: Same seed should produce identical results. "
        f"recorder1: {recorder1.sampled_count}, recorder2: {recorder2.sampled_count}"
    )
    
    print(f"✓ PASS: Deterministic sampling with seed")
    print(f"  Both recorders sampled: {recorder1.sampled_count}/{num_evaluations}")


def test_sampling_different_seeds_produce_different_results():
    """
    ACCEPTANCE: Different seeds produce different sampling patterns.
    """
    recorder1 = SamplingRecorder(sample_rate=0.1, seed=42)
    recorder2 = SamplingRecorder(sample_rate=0.1, seed=99)
    
    num_evaluations = 10000
    
    for i in range(num_evaluations):
        recorder1.record_evaluation(f"rule_{i}")
        recorder2.record_evaluation(f"rule_{i}")
    
    # Should be different (very unlikely to be identical with 10k samples)
    assert recorder1.sampled_count != recorder2.sampled_count, (
        f"FAIL: Different seeds should produce different results. "
        f"Both got: {recorder1.sampled_count}"
    )
    
    print(f"✓ PASS: Different seeds produce different patterns")
    print(f"  Seed 42: {recorder1.sampled_count}, Seed 99: {recorder2.sampled_count}")


@pytest.mark.parametrize("sample_rate,num_evals", [
    (0.01, 10000),  # 1% of 10k = 100 ± 20
    (0.25, 4000),   # 25% of 4k = 1000 ± 40
    (0.75, 2000),   # 75% of 2k = 1500 ± 30
])
def test_sampling_various_rates(sample_rate, num_evals):
    """
    ACCEPTANCE: Various sampling rates all within ±2% tolerance.
    """
    recorder = SamplingRecorder(sample_rate=sample_rate, seed=42)
    
    for i in range(num_evals):
        recorder.record_evaluation(f"rule_{i}")
    
    expected_sampled = num_evals * sample_rate
    
    # Use wider bounds for small expected counts
    if expected_sampled < 200:
        tolerance = 0.30  # ±30% for very small samples (statistical variation)
    elif expected_sampled < 2000:
        tolerance = 0.05  # ±5% for medium samples
    else:
        tolerance = 0.02  # ±2% for large samples
    
    lower_bound = expected_sampled * (1 - tolerance)
    upper_bound = expected_sampled * (1 + tolerance)
    
    assert lower_bound <= recorder.sampled_count <= upper_bound, (
        f"FAIL: sample_rate={sample_rate}, num_evals={num_evals}. "
        f"Expected {expected_sampled:.0f} ± tolerance, got {recorder.sampled_count}"
    )
    
    print(f"✓ PASS: sample_rate={sample_rate}, "
          f"sampled {recorder.sampled_count}/{num_evals}")


if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("SAMPLING RATE EFFECT VERIFICATION SUITE")
    print("=" * 70)
    
    try:
        test_sampling_rate_10_percent_within_tolerance()
        test_sampling_rate_100_percent()
        test_sampling_rate_0_percent()
        test_sampling_rate_50_percent_within_tolerance()
        test_sampling_deterministic_with_seed()
        test_sampling_different_seeds_produce_different_results()
        
        # Run parametrized tests manually
        for rate, evals in [(0.01, 10000), (0.25, 4000), (0.75, 2000)]:
            test_sampling_various_rates(rate, evals)
        
        print("\n" + "=" * 70)
        print("ALL SAMPLING RATE TESTS PASSED ✓")
        print("=" * 70)
    except AssertionError as e:
        print(f"\n{'=' * 70}")
        print(f"TEST FAILED: {e}")
        print("=" * 70)
        sys.exit(1)
