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
from pathlib import Path


def run_single_scan(enable_metrics: bool) -> float:
    """Run single scan and return execution time."""
    
    cmd = [
        "poetry", "run", "crashlens", "scan",
        "large-test.jsonl",
        "--format", "json"
    ]
    
    if enable_metrics:
        cmd.extend([
            "--push-metrics",
            "--pushgateway-url", "http://localhost:9091"
        ])
    
    start = time.time()
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True
    )
    elapsed = time.time() - start
    
    if result.returncode != 0:
        print(f"ERROR: Scan failed with code {result.returncode}")
        print(result.stderr)
        sys.exit(1)
    
    return elapsed


def run_benchmark(iterations: int = 10):
    """Run full benchmark with statistics."""
    
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
    
    # With metrics (metrics enabled)
    print(f"[2/2] Running with metrics ({iterations} iterations)...")
    metrics_times = []
    for i in range(iterations):
        elapsed = run_single_scan(enable_metrics=True)
        metrics_times.append(elapsed)
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
    print()
    
    # Validate baseline
    if baseline_avg < 5.0:
        print("⚠️  WARNING: Baseline < 5 seconds (may be too small)")
        print("   Consider regenerating with more traces")
    
    # Decision gate
    print("=" * 70)
    print("DECISION GATE (10% threshold)")
    print("=" * 70)
    
    if overhead_pct > 10.0:
        print(f"✗ FAIL: Overhead {overhead_pct:.2f}% exceeds 10% threshold")
        print()
        print("ACTION REQUIRED:")
        print("1. Implement sampling (--metrics-sample-rate)")
        print("2. Re-run benchmark with sampling enabled")
        print("3. If still >10%, abort feature")
        return False
    else:
        print(f"✓ PASS: Overhead {overhead_pct:.2f}% is acceptable")
        print()
        print("Proceed to Hour 3 (Dashboard Script)")
        return True


if __name__ == "__main__":
    success = run_benchmark(iterations=10)
    sys.exit(0 if success else 1)
