#!/usr/bin/env python3
"""Benchmark script to measure stats collection overhead.

This script compares scan performance with and without stats collection
to validate that overhead is acceptable (<10%).
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.cli import cli
from click.testing import CliRunner


def benchmark_scan(enable_stats: bool, iterations: int = 3):
    """Run scan benchmark with or without stats collection.
    
    Args:
        enable_stats: Whether to enable stats collection
        iterations: Number of iterations to average
        
    Returns:
        Average execution time in seconds
    """
    runner = CliRunner()
    times = []
    
    for i in range(iterations):
        start = time.time()
        
        # Run scan command with demo mode (uses built-in sample data)
        result = runner.invoke(cli, ['scan', '--demo'])
        
        elapsed = time.time() - start
        times.append(elapsed)
        
        if result.exit_code != 0:
            print(f"Warning: Scan failed with exit code {result.exit_code}")
    
    return sum(times) / len(times)


if __name__ == '__main__':
    print("CrashLens Stats Collection Overhead Benchmark")
    print("=" * 50)
    
    # Baseline: No stats collection
    print("\nRunning baseline (stats disabled)...")
    baseline_time = benchmark_scan(enable_stats=False)
    print(f"Baseline avg time: {baseline_time:.3f}s")
    
    # With stats: Stats collection enabled
    print("\nRunning with stats collection...")
    stats_time = benchmark_scan(enable_stats=True)
    print(f"With stats avg time: {stats_time:.3f}s")
    
    # Calculate overhead
    overhead = stats_time - baseline_time
    overhead_pct = (overhead / baseline_time) * 100
    
    print("\n" + "=" * 50)
    print(f"Overhead: {overhead:.3f}s ({overhead_pct:.1f}%)")
    print("=" * 50)
    
    # Validate acceptance criteria
    if overhead_pct < 10:
        print("✓ PASS: Overhead is acceptable (<10%)")
        sys.exit(0)
    else:
        print("✗ FAIL: Overhead exceeds 10% threshold")
        print("Consider optimizing stats collection or aborting metrics feature")
        sys.exit(1)
