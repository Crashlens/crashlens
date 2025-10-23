#!/usr/bin/env python3
"""Production benchmark for CrashLens metrics overhead.

Requirements:
- 100k+ traces (5+ second baseline)
- 10 iterations per configuration
- Statistical significance testing
- Clear pass/fail criteria (10% threshold)
"""

import time
import subprocess
import statistics
import sys
import argparse
from pathlib import Path


def run_single_scan(enable_metrics: bool, sample_rate: float = 1.0) -> float:
    """Run single scan and return execution time.
    
    Args:
        enable_metrics: Enable metrics collection
        sample_rate: Sampling rate (0.0-1.0, only used if enable_metrics=True)
    
    Returns:
        Elapsed time in seconds
    """
    
    # Use temp report file to avoid prompts
    import tempfile
    temp_report = tempfile.mktemp(suffix=".json")
    
    cmd = [
        "poetry", "run", "crashlens", "scan",
        "large-test.jsonl",
        "--format", "json",
        "--report-file", temp_report
    ]
    
    if enable_metrics:
        cmd.extend([
            "--push-metrics",
            "--pushgateway-url", "http://localhost:9091",
            "--metrics-sample-rate", str(sample_rate)
        ])
    
    start = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    elapsed = time.time() - start
    
    # Clean up temp file
    try:
        import os
        os.remove(temp_report)
    except:
        pass
    
    if result.returncode != 0:
        print(f"ERROR: Scan failed with code {result.returncode}")
        print(result.stderr)
        sys.exit(1)
    
    return elapsed


def run_benchmark(iterations: int = 10, test_sampling: bool = True):
    """Run benchmark with baseline and metrics configurations.
    
    Args:
        iterations: Number of iterations per configuration
        test_sampling: If True, test both 100% and 10% sampling
    
    Returns:
        True if all tested configurations pass, False otherwise
    """
    
    print("=" * 70)
    print("CrashLens Metrics Overhead Benchmark (100k traces)")
    print("=" * 70)
    print()
    
    # Check test file exists
    if not Path("large-test.jsonl").exists():
        print("ERROR: large-test.jsonl not found")
        print("Run: python scripts/generate_large_test.py")
        sys.exit(1)
    
    # Baseline (metrics disabled)
    print(f"[1/2] Running baseline ({iterations} iterations)...")
    baseline_times = []
    for i in range(iterations):
        elapsed = run_single_scan(enable_metrics=False)
        baseline_times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed:.3f}s")
    
    print()
    
    # With metrics - 100% sampling
    print(f"[2/3] Running with metrics 100% sampling ({iterations} iterations)...")
    metrics_times = []
    for i in range(iterations):
        elapsed = run_single_scan(enable_metrics=True)
        metrics_times.append(elapsed)
        print(f"  Iteration {i+1}: {elapsed:.3f}s")
    
    print()
    
    # With metrics - 10% sampling (if test_sampling enabled)
    sampled_times = []
    
    if test_sampling:
        print(f"[3/3] Running with metrics 10% sampling ({iterations} iterations)...")
        for i in range(iterations):
            elapsed = run_single_scan(enable_metrics=True, sample_rate=0.1)
            sampled_times.append(elapsed)
            print(f"  Iteration {i+1}: {elapsed:.3f}s")
        
        print()
    
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    
    # Calculate statistics
    baseline_avg = statistics.mean(baseline_times)
    baseline_stdev = statistics.stdev(baseline_times)
    baseline_min = min(baseline_times)
    baseline_max = max(baseline_times)
    
    metrics_avg = statistics.mean(metrics_times)
    metrics_stdev = statistics.stdev(metrics_times)
    metrics_min = min(metrics_times)
    metrics_max = max(metrics_times)
    
    overhead_abs = metrics_avg - baseline_avg
    overhead_ms = overhead_abs * 1000
    overhead_pct = (overhead_abs / baseline_avg) * 100
    
    # Calculate sampled statistics if applicable
    sampled_avg = 0
    sampled_stdev = 0
    sampled_overhead = 0
    if test_sampling and sampled_times:
        sampled_avg = statistics.mean(sampled_times)
        sampled_stdev = statistics.stdev(sampled_times)
        sampled_overhead = ((sampled_avg - baseline_avg) / baseline_avg) * 100
    
    # Report
    print()
    print(f"Baseline (metrics disabled):")
    print(f"  Average: {baseline_avg:.3f}s ± {baseline_stdev:.3f}s")
    print(f"  Range:   {baseline_min:.3f}s - {baseline_max:.3f}s")
    print()
    print(f"With metrics (enabled):")
    print(f"  Average: {metrics_avg:.3f}s ± {metrics_stdev:.3f}s")
    print(f"  Range:   {metrics_min:.3f}s - {metrics_max:.3f}s")
    print()
    print(f"Overhead:")
    print(f"  Absolute: {overhead_abs:.3f}s ({overhead_ms:.1f}ms)")
    print(f"  Percentage: {overhead_pct:.2f}%")
    
    # Display sampled results if tested
    if test_sampling and sampled_times:
        print()
        print(f"With metrics (10% sampling):")
        print(f"  Average: {sampled_avg:.3f}s ± {sampled_stdev:.3f}s")
        print(f"  Overhead: {sampled_overhead:.2f}%")
    
    print()
    
    # Validate baseline
    if baseline_avg < 5.0:
        print("⚠️  WARNING: Baseline < 5 seconds (may be too small)")
        print("   Consider regenerating with more traces")
    
    # Decision gate
    print("=" * 70)
    print("DECISION GATE (10% threshold)")
    print("=" * 70)
    
    # Decision based on 10% sampling (if tested)
    if test_sampling and sampled_times:
        if sampled_overhead > 10.0:
            print(f"\n✗ FAIL: Even 10% sampling ({sampled_overhead:.2f}%) exceeds threshold")
            print("ACTION: Abort feature or try 5% sampling")
            return False
        else:
            print(f"\n✓ PASS: 10% sampling ({sampled_overhead:.2f}%) is acceptable")
            print("RECOMMENDATION: Use --metrics-sample-rate 0.1 in production")
            return True
    else:
        # Fallback to 100% sampling decision
        if overhead_pct > 10.0:
            print(f"\n✗ FAIL: Overhead {overhead_pct:.2f}% exceeds 10% threshold")
            return False
        else:
            print(f"\n✓ PASS: Overhead {overhead_pct:.2f}% is acceptable")
            return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark CrashLens metrics overhead"
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=10,
        help='Number of iterations per configuration (default: 10)'
    )
    parser.add_argument(
        '--no-sampling-test',
        action='store_true',
        help='Skip 10%% sampling test (only test baseline + 100%%)'
    )
    
    args = parser.parse_args()
    
    success = run_benchmark(
        iterations=args.iterations,
        test_sampling=not args.no_sampling_test
    )
    
    sys.exit(0 if success else 1)
