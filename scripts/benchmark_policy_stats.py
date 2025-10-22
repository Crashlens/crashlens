#!/usr/bin/env python3
"""Benchmark script to measure PolicyEngine stats collection overhead.

This script directly tests PolicyEngine performance with and without stats
to isolate the overhead measurement.
"""

import sys
import time
import yaml
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.policy.engine import PolicyEngine


def create_sample_policy_file():
    """Create a temporary sample policy file."""
    policy = {
        'version': 1,
        'global': {'max_violations_per_rule': 100},
        'rules': [
            {
                'id': 'rule_1',
                'description': 'Test rule 1',
                'match': {'model': 'gpt-4'},
                'action': 'warn',
                'severity': 'high',
                'suggestion': 'Use cheaper model'
            },
            {
                'id': 'rule_2',
                'description': 'Test rule 2',
                'match': {'prompt_tokens': '>1000'},
                'action': 'warn',
                'severity': 'medium',
                'suggestion': 'Reduce prompt size'
            },
            {
                'id': 'rule_3',
                'description': 'Test rule 3',
                'match': {'cost': '>0.01'},
                'action': 'fail',
                'severity': 'critical',
                'suggestion': 'Review costs'
            },
            {
                'id': 'rule_4',
                'description': 'Test rule 4',
                'match': {'metadata.fallback_attempted': True},
                'action': 'warn',
                'severity': 'low',
                'suggestion': 'Check fallback logic'
            },
            {
                'id': 'rule_5',
                'description': 'Test rule 5',
                'match': {'retry_count': '>3'},
                'action': 'fail',
                'severity': 'critical',
                'suggestion': 'Implement exponential backoff'
            }
        ]
    }
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8')
    yaml.dump(policy, temp_file)
    temp_file.close()
    return Path(temp_file.name)


def create_sample_logs(count: int = 1000):
    """Create sample log entries for testing."""
    logs = []
    for i in range(count):
        logs.append({
            'traceId': f'trace_{i}',
            'model': 'gpt-4' if i % 3 == 0 else 'gpt-3.5-turbo',
            'prompt_tokens': 500 + (i % 600),
            'completion_tokens': 200,
            'cost': 0.001 * (i % 20),
            'metadata': {
                'fallback_attempted': i % 5 == 0
            },
            'retry_count': i % 5
        })
    return logs


def benchmark_policy_engine(enable_stats: bool, iterations: int = 5):
    """Benchmark PolicyEngine with or without stats collection.
    
    Args:
        enable_stats: Whether to enable stats collection
        iterations: Number of iterations to average
        
    Returns:
        Average execution time in seconds
    """
    policy_file = create_sample_policy_file()
    logs = create_sample_logs(1000)  # 1000 log entries
    
    times = []
    
    try:
        for i in range(iterations):
            engine = PolicyEngine(policy_file)
            
            if enable_stats:
                engine.enable_stats_collection()
            
            start = time.perf_counter()
            violations, warnings = engine.evaluate_logs(logs)
            elapsed = time.perf_counter() - start
            
            times.append(elapsed)
    finally:
        # Clean up temp file
        policy_file.unlink(missing_ok=True)
    
    return sum(times) / len(times)


if __name__ == '__main__':
    print("CrashLens PolicyEngine Stats Collection Overhead Benchmark")
    print("=" * 70)
    print("Configuration:")
    print("  - Log entries: 1,000")
    print("  - Policy rules: 5")
    print("  - Iterations: 5")
    print("  - Total evaluations per run: 5,000 (1,000 logs × 5 rules)")
    print("=" * 70)
    
    # Baseline: No stats collection
    print("\nRunning baseline (stats disabled)...")
    baseline_time = benchmark_policy_engine(enable_stats=False)
    print(f"  Baseline avg time: {baseline_time:.4f}s")
    print(f"  Per-evaluation: {(baseline_time / 5000) * 1000:.4f}ms")
    
    # With stats: Stats collection enabled
    print("\nRunning with stats collection...")
    stats_time = benchmark_policy_engine(enable_stats=True)
    print(f"  With stats avg time: {stats_time:.4f}s")
    print(f"  Per-evaluation: {(stats_time / 5000) * 1000:.4f}ms")
    
    # Calculate overhead
    overhead = stats_time - baseline_time
    overhead_pct = (overhead / baseline_time) * 100 if baseline_time > 0 else 0
    
    print("\n" + "=" * 70)
    print(f"RESULTS:")
    print(f"  Absolute overhead: {overhead:.4f}s ({overhead * 1000:.2f}ms)")
    print(f"  Percentage overhead: {overhead_pct:.2f}%")
    print(f"  Per-evaluation overhead: {(overhead / 5000) * 1000000:.2f}μs")
    print("=" * 70)
    
    # Validate acceptance criteria
    if overhead_pct < 10:
        print("\n✓ PASS: Overhead is acceptable (<10%)")
        print(f"  Stats collection adds only {overhead_pct:.2f}% overhead")
        sys.exit(0)
    else:
        print("\n✗ FAIL: Overhead exceeds 10% threshold")
        print("  Consider optimizing stats collection or aborting metrics feature")
        sys.exit(1)
