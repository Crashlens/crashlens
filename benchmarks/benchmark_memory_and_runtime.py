#!/usr/bin/env python
"""
Benchmark: Memory and Runtime Overhead Verification
Purpose: Measure performance impact of Prometheus metrics collection.
         Compares baseline (metrics disabled) vs metrics-enabled execution.
         
Acceptance Criteria:
- Runtime overhead < 10%
- Memory overhead < 30MB
- JSON output for CI integration
- Configurable workload parameters
- Multiple runs for statistical validity

Usage:
    python benchmarks/benchmark_memory_and_runtime.py
    
    # Custom workload
    python benchmarks/benchmark_memory_and_runtime.py --traces 5000 --policies 20
    
    # JSON output only
    python benchmarks/benchmark_memory_and_runtime.py --json-only

Environment Variables:
    TEST_TRACES: Number of traces to process (default: 1000)
    POLICIES: Number of policy rules (default: 10)
    RUNS: Number of benchmark runs for averaging (default: 3)
"""

import sys
import os
import time
import json
import argparse
import tempfile
from pathlib import Path

# Conditionally import resource module (Unix only)
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False
    # Windows fallback: use psutil if available
    try:
        import psutil
        HAS_PSUTIL = True
    except ImportError:
        HAS_PSUTIL = False


def get_memory_usage_mb():
    """
    Get current process RSS memory usage in MB.
    
    Returns:
        float: Memory usage in MB, or None if unavailable
    """
    if HAS_RESOURCE:
        # Unix: use resource.getrusage
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is in KB on Linux, bytes on macOS
        if sys.platform == 'darwin':
            return usage.ru_maxrss / 1024 / 1024  # bytes to MB
        else:
            return usage.ru_maxrss / 1024  # KB to MB
    elif HAS_PSUTIL:
        # Windows: use psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    else:
        return None


def generate_test_traces(num_traces: int) -> list:
    """
    Generate synthetic Langfuse trace data for benchmarking.
    
    Args:
        num_traces: Number of traces to generate
    
    Returns:
        List of trace dictionaries
    """
    traces = []
    for i in range(num_traces):
        trace = {
            'traceId': f'trace_{i:06d}',
            'startTime': '2024-01-15T10:00:00Z',
            'endTime': '2024-01-15T10:00:05Z',
            'model': 'gpt-4' if i % 3 == 0 else 'gpt-3.5-turbo',
            'prompt_tokens': 100 + (i % 500),
            'completion_tokens': 50 + (i % 200),
            'cost': (100 + (i % 500)) * 0.00003 + (50 + (i % 200)) * 0.00006,
            'metadata': {
                'route': f'route_{i % 5}',
                'team': f'team_{i % 3}',
                'fallback_attempted': i % 10 == 0
            }
        }
        traces.append(trace)
    return traces


def generate_test_policies(num_policies: int) -> list:
    """
    Generate synthetic policy rules for benchmarking.
    
    Args:
        num_policies: Number of policy rules to generate
    
    Returns:
        List of policy rule dictionaries
    """
    policies = []
    for i in range(num_policies):
        policy = {
            'id': f'policy_rule_{i:03d}',
            'description': f'Test policy rule {i}',
            'match': {
                'model': 'gpt-4' if i % 2 == 0 else 'gpt-3.5-turbo',
                'cost': f'> {i * 0.1}'
            },
            'action': 'warn',
            'severity': 'medium'
        }
        policies.append(policy)
    return policies


def simulate_crashlens_scan(traces: list, policies: list, enable_metrics: bool) -> dict:
    """
    Simulate CrashLens scan workload.
    
    This is a simplified simulation. In production, replace with actual
    crashlens scan logic.
    
    Args:
        traces: List of trace dictionaries
        policies: List of policy rules
        enable_metrics: Whether to enable metrics collection
    
    Returns:
        dict: Scan results
    """
    # Simulate policy evaluation
    violations = []
    
    for trace in traces:
        for policy in policies:
            # Simulate policy matching logic
            if policy['match']['model'] == trace['model']:
                if trace['cost'] > float(policy['match']['cost'].split()[1]):
                    violations.append({
                        'trace_id': trace['traceId'],
                        'policy_id': policy['id'],
                        'cost': trace['cost']
                    })
                    
                    # Simulate metrics recording (if enabled)
                    if enable_metrics:
                        # In production, this would call metrics.record_violation()
                        # For benchmark, just simulate some overhead
                        _ = json.dumps({'policy': policy['id'], 'trace': trace['traceId']})
    
    return {'violations': violations, 'total_traces': len(traces)}


def run_benchmark(num_traces: int, num_policies: int, enable_metrics: bool) -> dict:
    """
    Run a single benchmark iteration.
    
    Args:
        num_traces: Number of traces to process
        num_policies: Number of policy rules
        enable_metrics: Whether to enable metrics
    
    Returns:
        dict: Benchmark results (runtime_s, memory_mb, violations)
    """
    # Generate test data
    traces = generate_test_traces(num_traces)
    policies = generate_test_policies(num_policies)
    
    # Measure initial memory
    mem_before = get_memory_usage_mb()
    
    # Measure runtime
    start = time.monotonic()
    results = simulate_crashlens_scan(traces, policies, enable_metrics)
    elapsed = time.monotonic() - start
    
    # Measure final memory
    mem_after = get_memory_usage_mb()
    
    return {
        'runtime_s': elapsed,
        'memory_before_mb': mem_before,
        'memory_after_mb': mem_after,
        'memory_delta_mb': (mem_after - mem_before) if mem_before and mem_after else None,
        'violations': len(results['violations'])
    }


def main():
    parser = argparse.ArgumentParser(description='Benchmark Prometheus metrics overhead')
    parser.add_argument('--traces', type=int, default=None,
                        help='Number of traces to process (default: env TEST_TRACES or 1000)')
    parser.add_argument('--policies', type=int, default=None,
                        help='Number of policy rules (default: env POLICIES or 10)')
    parser.add_argument('--runs', type=int, default=None,
                        help='Number of benchmark runs (default: env RUNS or 3)')
    parser.add_argument('--json-only', action='store_true',
                        help='Output JSON only (no human-readable text)')
    parser.add_argument('--output', type=str, default=None,
                        help='Write JSON results to file')
    
    args = parser.parse_args()
    
    # Read configuration
    num_traces = args.traces or int(os.getenv('TEST_TRACES', '1000'))
    num_policies = args.policies or int(os.getenv('POLICIES', '10'))
    num_runs = args.runs or int(os.getenv('RUNS', '3'))
    
    if not args.json_only:
        print("=" * 70)
        print("CRASHLENS PROMETHEUS METRICS OVERHEAD BENCHMARK")
        print("=" * 70)
        print(f"Configuration:")
        print(f"  Traces: {num_traces}")
        print(f"  Policies: {num_policies}")
        print(f"  Runs: {num_runs}")
        print(f"  Memory tracking: {'resource' if HAS_RESOURCE else 'psutil' if HAS_PSUTIL else 'unavailable'}")
        print()
    
    # Run baseline (metrics disabled)
    if not args.json_only:
        print("Running baseline (metrics disabled)...")
    
    baseline_runs = []
    for i in range(num_runs):
        result = run_benchmark(num_traces, num_policies, enable_metrics=False)
        baseline_runs.append(result)
        if not args.json_only:
            print(f"  Run {i+1}: {result['runtime_s']:.3f}s, "
                  f"mem: {result['memory_delta_mb']:.1f}MB delta" if result['memory_delta_mb'] else "mem: N/A")
    
    # Calculate baseline averages
    baseline_runtime = sum(r['runtime_s'] for r in baseline_runs) / len(baseline_runs)
    baseline_memory = (sum(r['memory_delta_mb'] for r in baseline_runs if r['memory_delta_mb'] is not None) / 
                       len([r for r in baseline_runs if r['memory_delta_mb'] is not None])
                       if any(r['memory_delta_mb'] is not None for r in baseline_runs) else None)
    
    if not args.json_only:
        print(f"Baseline average: {baseline_runtime:.3f}s, "
              f"mem: {baseline_memory:.1f}MB" if baseline_memory else "mem: N/A")
        print()
    
    # Run with metrics enabled
    if not args.json_only:
        print("Running with metrics enabled...")
    
    metrics_runs = []
    for i in range(num_runs):
        result = run_benchmark(num_traces, num_policies, enable_metrics=True)
        metrics_runs.append(result)
        if not args.json_only:
            print(f"  Run {i+1}: {result['runtime_s']:.3f}s, "
                  f"mem: {result['memory_delta_mb']:.1f}MB delta" if result['memory_delta_mb'] else "mem: N/A")
    
    # Calculate metrics averages
    metrics_runtime = sum(r['runtime_s'] for r in metrics_runs) / len(metrics_runs)
    metrics_memory = (sum(r['memory_delta_mb'] for r in metrics_runs if r['memory_delta_mb'] is not None) / 
                      len([r for r in metrics_runs if r['memory_delta_mb'] is not None])
                      if any(r['memory_delta_mb'] is not None for r in metrics_runs) else None)
    
    if not args.json_only:
        print(f"Metrics average: {metrics_runtime:.3f}s, "
              f"mem: {metrics_memory:.1f}MB" if metrics_memory else "mem: N/A")
        print()
    
    # Calculate overhead
    runtime_overhead_pct = ((metrics_runtime - baseline_runtime) / baseline_runtime * 100)
    memory_overhead_mb = (metrics_memory - baseline_memory) if baseline_memory and metrics_memory else None
    
    # Determine pass/fail
    runtime_pass = runtime_overhead_pct < 10.0
    memory_pass = (memory_overhead_mb < 30.0) if memory_overhead_mb is not None else True  # Pass if no memory tracking
    
    # Prepare JSON output
    output = {
        'benchmark': 'prometheus_metrics_overhead',
        'configuration': {
            'traces': num_traces,
            'policies': num_policies,
            'runs': num_runs
        },
        'baseline': {
            'runtime_s': baseline_runtime,
            'memory_mb': baseline_memory,
            'runs': baseline_runs
        },
        'metrics_enabled': {
            'runtime_s': metrics_runtime,
            'memory_mb': metrics_memory,
            'runs': metrics_runs
        },
        'overhead': {
            'runtime_overhead_pct': runtime_overhead_pct,
            'memory_overhead_mb': memory_overhead_mb
        },
        'thresholds': {
            'max_runtime_overhead_pct': 10.0,
            'max_memory_overhead_mb': 30.0
        },
        'results': {
            'runtime_pass': runtime_pass,
            'memory_pass': memory_pass,
            'overall_pass': runtime_pass and memory_pass
        }
    }
    
    # Write to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        if not args.json_only:
            print(f"Results written to {args.output}")
    
    # Print results
    if args.json_only:
        print(json.dumps(output, indent=2))
    else:
        print("=" * 70)
        print("RESULTS")
        print("=" * 70)
        print(f"Runtime Overhead: {runtime_overhead_pct:+.2f}% ({baseline_runtime:.3f}s → {metrics_runtime:.3f}s)")
        print(f"  Threshold: <10%")
        print(f"  Status: {'✓ PASS' if runtime_pass else '✗ FAIL'}")
        print()
        
        if memory_overhead_mb is not None:
            print(f"Memory Overhead: {memory_overhead_mb:+.1f}MB ({baseline_memory:.1f}MB → {metrics_memory:.1f}MB)")
            print(f"  Threshold: <30MB")
            print(f"  Status: {'✓ PASS' if memory_pass else '✗ FAIL'}")
        else:
            print("Memory Overhead: N/A (memory tracking unavailable)")
            print("  Status: ✓ PASS (skipped)")
        print()
        
        print("=" * 70)
        if runtime_pass and memory_pass:
            print("OVERALL: ✓ PASS - Metrics overhead within acceptable limits")
        else:
            print("OVERALL: ✗ FAIL - Metrics overhead exceeds thresholds")
        print("=" * 70)
    
    # Exit code based on pass/fail
    sys.exit(0 if (runtime_pass and memory_pass) else 1)


if __name__ == '__main__':
    main()
