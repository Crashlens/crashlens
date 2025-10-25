"""
Benchmark per-rule sampling with 10k traces.

Phase 2 requirements:
- Prove constant memory with custom sampling rates
- Prove <10% overhead with mixed rates (0.01, 0.1, 1.0)
- Test memory growth with different sampling configurations

Usage:
    python scripts/benchmark_per_rule_sampling.py
"""

import sys
import time
import json
import random
import tempfile
import tracemalloc
from pathlib import Path
from typing import Dict, List

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crashlens.observability import initialize_metrics


def generate_test_trace(trace_id: int, rule_name: str) -> Dict:
    """Generate a single test trace"""
    return {
        'traceId': f'trace-{trace_id}',
        'startTime': '2025-01-25T10:00:00Z',
        'endTime': '2025-01-25T10:00:01Z',
        'model': 'gpt-4',
        'usage': {
            'prompt_tokens': random.randint(100, 1000),
            'completion_tokens': random.randint(50, 500)
        },
        'metadata': {
            'rule': rule_name,
            'detector': 'test_detector'
        }
    }


def generate_test_file(num_traces: int, num_rules: int) -> Path:
    """
    Generate test JSONL file with traces distributed across rules.
    
    Args:
        num_traces: Total number of traces to generate
        num_rules: Number of different rule names to use
    
    Returns:
        Path to generated test file
    """
    tmpfile = tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False)
    
    rule_names = [f'rule_{i:04d}' for i in range(num_rules)]
    
    for trace_id in range(num_traces):
        # Distribute traces across rules
        rule_name = rule_names[trace_id % num_rules]
        trace = generate_test_trace(trace_id, rule_name)
        tmpfile.write(json.dumps(trace) + '\n')
    
    tmpfile.close()
    return Path(tmpfile.name)


def benchmark_sampling(
    num_traces: int,
    num_rules: int,
    per_rule_rates: Dict[str, float],
    sample_rate: float = 1.0
) -> Dict:
    """
    Benchmark metrics collection with per-rule sampling.
    
    Args:
        num_traces: Number of traces to process
        num_rules: Number of different rules
        per_rule_rates: Dict of rule_name -> sample_rate
        sample_rate: Global sample rate (default)
    
    Returns:
        Dict with benchmark results
    """
    print(f"\n{'='*80}")
    print(f"Benchmarking: {num_traces:,} traces, {num_rules} rules")
    print(f"Global sample rate: {sample_rate}")
    print(f"Per-rule overrides: {len(per_rule_rates)} rules")
    print(f"{'='*80}\n")
    
    # Start memory tracking
    tracemalloc.start()
    start_memory = tracemalloc.get_traced_memory()[0]
    
    # Initialize metrics
    start_time = time.perf_counter()
    metrics = initialize_metrics(
        enabled=True,
        max_rules=500,  # Standard cardinality cap
        sample_rate=sample_rate,
        per_rule_rates=per_rule_rates
    )
    init_time = time.perf_counter() - start_time
    
    # Record rule hits (simulating scan)
    record_start = time.perf_counter()
    
    rule_names = [f'rule_{i:04d}' for i in range(num_rules)]
    for trace_id in range(num_traces):
        rule_name = rule_names[trace_id % num_rules]
        
        # Record rule hit (sampling happens inside)
        metrics.record_rule_hit(
            rule_name=rule_name,
            severity='high',
            waste_cost=1.5,
            waste_tokens=1000
        )
    
    record_time = time.perf_counter() - record_start
    
    # Get final memory usage
    peak_memory = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    
    memory_mb = (peak_memory - start_memory) / 1024 / 1024
    
    # Calculate throughput
    throughput = num_traces / record_time
    
    print(f"✓ Initialization time: {init_time*1000:.2f}ms")
    print(f"✓ Record time: {record_time:.3f}s")
    print(f"✓ Throughput: {throughput:,.0f} traces/sec")
    print(f"✓ Memory used: {memory_mb:.2f} MB")
    print(f"✓ Memory per trace: {memory_mb / num_traces * 1000:.3f} KB")
    
    return {
        'num_traces': num_traces,
        'num_rules': num_rules,
        'init_time_ms': init_time * 1000,
        'record_time_s': record_time,
        'throughput': throughput,
        'memory_mb': memory_mb,
        'memory_per_trace_kb': memory_mb / num_traces * 1000
    }


def benchmark_overhead_with_sampling(num_traces: int, num_rules: int) -> Dict:
    """
    Benchmark overhead of per-rule sampling vs. baseline.
    
    Tests:
    1. Baseline (no metrics)
    2. Global sampling (1.0 - capture all)
    3. Global sampling (0.1 - capture 10%)
    4. Per-rule sampling (mixed rates)
    """
    print(f"\n{'='*80}")
    print(f"OVERHEAD BENCHMARK: {num_traces:,} traces, {num_rules} rules")
    print(f"{'='*80}\n")
    
    # Generate test data
    print("Generating test data...")
    test_file = generate_test_file(num_traces, num_rules)
    
    # Baseline: No metrics (just reading file)
    print("\n[1/4] Baseline: No metrics...")
    start = time.perf_counter()
    with open(test_file) as f:
        for line in f:
            json.loads(line)
    baseline_time = time.perf_counter() - start
    print(f"✓ Baseline time: {baseline_time:.3f}s")
    
    # Test 1: Global sampling 1.0
    print("\n[2/4] Global sampling: 1.0 (capture all)...")
    start = time.perf_counter()
    metrics_100 = initialize_metrics(enabled=True, sample_rate=1.0)
    with open(test_file) as f:
        for line in f:
            data = json.loads(line)
            rule_name = data['metadata']['rule']
            metrics_100.record_rule_hit(rule_name, 'high', 1.5, 1000)
    time_100 = time.perf_counter() - start
    overhead_100 = (time_100 / baseline_time - 1.0) * 100
    print(f"✓ Time with metrics: {time_100:.3f}s")
    print(f"✓ Overhead: {overhead_100:.2f}%")
    
    # Test 2: Global sampling 0.1
    print("\n[3/4] Global sampling: 0.1 (capture 10%)...")
    start = time.perf_counter()
    metrics_10 = initialize_metrics(enabled=True, sample_rate=0.1)
    with open(test_file) as f:
        for line in f:
            data = json.loads(line)
            rule_name = data['metadata']['rule']
            metrics_10.record_rule_hit(rule_name, 'high', 1.5, 1000)
    time_10 = time.perf_counter() - start
    overhead_10 = (time_10 / baseline_time - 1.0) * 100
    print(f"✓ Time with metrics: {time_10:.3f}s")
    print(f"✓ Overhead: {overhead_10:.2f}%")
    
    # Test 3: Per-rule sampling (mixed rates)
    print("\n[4/4] Per-rule sampling: mixed rates...")
    per_rule_rates = {}
    rule_names = [f'rule_{i:04d}' for i in range(num_rules)]
    for i, rule_name in enumerate(rule_names):
        if i % 3 == 0:
            per_rule_rates[rule_name] = 1.0  # High-priority rules: 100%
        elif i % 3 == 1:
            per_rule_rates[rule_name] = 0.1  # Medium-priority: 10%
        # else: use global default (0.01 - 1%)
    
    start = time.perf_counter()
    metrics_mixed = initialize_metrics(
        enabled=True,
        sample_rate=0.01,  # Default for rules without override
        per_rule_rates=per_rule_rates
    )
    with open(test_file) as f:
        for line in f:
            data = json.loads(line)
            rule_name = data['metadata']['rule']
            metrics_mixed.record_rule_hit(rule_name, 'high', 1.5, 1000)
    time_mixed = time.perf_counter() - start
    overhead_mixed = (time_mixed / baseline_time - 1.0) * 100
    print(f"✓ Time with metrics: {time_mixed:.3f}s")
    print(f"✓ Overhead: {overhead_mixed:.2f}%")
    
    # Cleanup
    test_file.unlink()
    
    # Summary
    print(f"\n{'='*80}")
    print("OVERHEAD SUMMARY")
    print(f"{'='*80}")
    print(f"Baseline (no metrics):        {baseline_time:.3f}s")
    print(f"Global 100% sampling:         {time_100:.3f}s ({overhead_100:+.2f}%)")
    print(f"Global 10% sampling:          {time_10:.3f}s ({overhead_10:+.2f}%)")
    print(f"Per-rule mixed sampling:      {time_mixed:.3f}s ({overhead_mixed:+.2f}%)")
    print(f"\n✓ PASS: All overheads <10%" if all(x < 10 for x in [overhead_100, overhead_10, overhead_mixed]) else "❌ FAIL: Overhead >10%")
    
    return {
        'baseline_s': baseline_time,
        'global_100_s': time_100,
        'global_100_overhead_pct': overhead_100,
        'global_10_s': time_10,
        'global_10_overhead_pct': overhead_10,
        'per_rule_mixed_s': time_mixed,
        'per_rule_mixed_overhead_pct': overhead_mixed,
        'max_overhead_pct': max(overhead_100, overhead_10, overhead_mixed)
    }


def benchmark_memory_scaling(base_traces: int, multiplier: int) -> Dict:
    """
    Benchmark memory scaling with different trace counts.
    
    Tests constant-memory architecture claim:
    - Memory should grow <2x when traces grow 100x
    """
    print(f"\n{'='*80}")
    print(f"MEMORY SCALING BENCHMARK")
    print(f"{'='*80}\n")
    
    # Test with base trace count
    print(f"[1/2] Testing with {base_traces:,} traces...")
    result_base = benchmark_sampling(
        num_traces=base_traces,
        num_rules=50,
        per_rule_rates={'rule_0001': 1.0, 'rule_0002': 0.1},
        sample_rate=0.01
    )
    
    # Test with multiplier (e.g., 100x more traces)
    large_traces = base_traces * multiplier
    print(f"\n[2/2] Testing with {large_traces:,} traces ({multiplier}x more)...")
    result_large = benchmark_sampling(
        num_traces=large_traces,
        num_rules=50,
        per_rule_rates={'rule_0001': 1.0, 'rule_0002': 0.1},
        sample_rate=0.01
    )
    
    # Calculate memory growth ratio
    memory_ratio = result_large['memory_mb'] / result_base['memory_mb']
    
    print(f"\n{'='*80}")
    print("MEMORY SCALING SUMMARY")
    print(f"{'='*80}")
    print(f"{base_traces:,} traces:     {result_base['memory_mb']:.2f} MB")
    print(f"{large_traces:,} traces:   {result_large['memory_mb']:.2f} MB")
    print(f"Growth ratio:          {memory_ratio:.2f}x")
    print(f"\n✓ PASS: Memory <2x" if memory_ratio < 2.0 else f"❌ FAIL: Memory >={memory_ratio:.2f}x (threshold: 2.0x)")
    
    return {
        'base_traces': base_traces,
        'large_traces': large_traces,
        'multiplier': multiplier,
        'base_memory_mb': result_base['memory_mb'],
        'large_memory_mb': result_large['memory_mb'],
        'memory_growth_ratio': memory_ratio,
        'passes_threshold': memory_ratio < 2.0
    }


def main():
    """Run all benchmarks"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                    PER-RULE SAMPLING BENCHMARK                             ║
║                                                                            ║
║  Phase 2 Validation:                                                       ║
║  • Constant memory with custom sampling rates                              ║
║  • <10% overhead with mixed rates (0.01, 0.1, 1.0)                         ║
║  • Memory growth <2x for 100x more traces                                  ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    results = {}
    
    # Benchmark 1: Basic per-rule sampling
    print("\n" + "="*80)
    print("BENCHMARK 1: Basic Per-Rule Sampling")
    print("="*80)
    results['basic'] = benchmark_sampling(
        num_traces=10_000,
        num_rules=50,
        per_rule_rates={
            'rule_0001': 1.0,   # Critical rule: 100%
            'rule_0002': 0.5,   # Important rule: 50%
            'rule_0003': 0.1,   # Standard rule: 10%
            'rule_0004': 0.01,  # Low-priority: 1%
        },
        sample_rate=0.01  # Default for other rules
    )
    
    # Benchmark 2: Overhead comparison
    print("\n" + "="*80)
    print("BENCHMARK 2: Overhead Comparison")
    print("="*80)
    results['overhead'] = benchmark_overhead_with_sampling(
        num_traces=10_000,
        num_rules=50
    )
    
    # Benchmark 3: Memory scaling
    print("\n" + "="*80)
    print("BENCHMARK 3: Memory Scaling (Constant Memory Proof)")
    print("="*80)
    results['memory_scaling'] = benchmark_memory_scaling(
        base_traces=1_000,
        multiplier=100  # 100x more traces
    )
    
    # Final summary
    print(f"\n{'='*80}")
    print("FINAL VALIDATION RESULTS")
    print(f"{'='*80}")
    
    overhead_pass = results['overhead']['max_overhead_pct'] < 10.0
    memory_pass = results['memory_scaling']['passes_threshold']
    
    print(f"\n✓ Overhead test:     {'PASS' if overhead_pass else 'FAIL'} "
          f"(max: {results['overhead']['max_overhead_pct']:.2f}%, threshold: <10%)")
    print(f"✓ Memory scaling:    {'PASS' if memory_pass else 'FAIL'} "
          f"(ratio: {results['memory_scaling']['memory_growth_ratio']:.2f}x, threshold: <2.0x)")
    
    all_pass = overhead_pass and memory_pass
    print(f"\n{'✓ ALL TESTS PASSED' if all_pass else '❌ SOME TESTS FAILED'}")
    print(f"{'='*80}\n")
    
    # Save results
    results_file = Path(__file__).parent.parent / 'benchmark_per_rule_sampling_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {results_file}")
    
    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
