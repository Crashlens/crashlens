#!/bin/bash
# Purpose: Make it trivial to run local benchmarks in the terminal.
# 
# This script runs the benchmark twice:
# 1. Baseline (metrics disabled) - PUSH_METRICS=0
# 2. With metrics (metrics enabled) - PUSH_METRICS=1, SAMPLE_RATE=0.1
#
# Acceptance Criteria:
# - Runtime overhead < 10%
# - Memory overhead < 30MB
# - Exit code 0 if pass, non-zero if fail

set -e

echo "========================================================================"
echo "CrashLens Prometheus Metrics Benchmark"
echo "========================================================================"
echo ""

# Ensure benchmark script exists
if [ ! -f "benchmarks/benchmark_memory_and_runtime.py" ]; then
    echo "❌ ERROR: benchmarks/benchmark_memory_and_runtime.py not found"
    echo "   Run from repo root: bash scripts/run_benchmark.sh"
    exit 1
fi

# Create temp files for JSON output
BASELINE_JSON=$(mktemp)
METRICS_JSON=$(mktemp)

# Cleanup on exit
trap "rm -f $BASELINE_JSON $METRICS_JSON" EXIT

echo "Running baseline (metrics disabled)..."
echo "----------------------------------------"
unset CRASHLENS_PUSHGATEWAY_URL
PUSH_METRICS=0 python benchmarks/benchmark_memory_and_runtime.py \
    --json-only \
    --output "$BASELINE_JSON"

if [ $? -ne 0 ]; then
    echo "❌ Baseline benchmark failed"
    exit 1
fi

echo "✓ Baseline complete"
echo ""

echo "Running with metrics enabled..."
echo "----------------------------------------"
export CRASHLENS_PUSHGATEWAY_URL="http://dummy-pushgateway:9091"
PUSH_METRICS=1 SAMPLE_RATE=0.1 python benchmarks/benchmark_memory_and_runtime.py \
    --json-only \
    --output "$METRICS_JSON"

if [ $? -ne 0 ]; then
    echo "❌ Metrics-enabled benchmark failed"
    exit 1
fi

echo "✓ Metrics-enabled complete"
echo ""

# Parse JSON results
echo "========================================================================"
echo "BENCHMARK COMPARISON"
echo "========================================================================"

# Extract values using Python (portable JSON parsing)
python3 << EOF
import json
import sys

# Load both JSON files
with open('$BASELINE_JSON') as f:
    baseline = json.load(f)
with open('$METRICS_JSON') as f:
    metrics = json.load(f)

# Extract key metrics
baseline_runtime = baseline['baseline']['runtime_s']
metrics_runtime = metrics['metrics_enabled']['runtime_s']
runtime_overhead_pct = metrics['overhead']['runtime_overhead_pct']

baseline_memory = baseline['baseline'].get('memory_mb')
metrics_memory = metrics['metrics_enabled'].get('memory_mb')
memory_overhead_mb = metrics['overhead'].get('memory_overhead_mb')

# Print comparison
print(f"Configuration:")
print(f"  Traces: {baseline['configuration']['traces']}")
print(f"  Policies: {baseline['configuration']['policies']}")
print(f"  Runs: {baseline['configuration']['runs']}")
print()

print(f"Runtime:")
print(f"  Baseline:  {baseline_runtime:.3f}s")
print(f"  With metrics: {metrics_runtime:.3f}s")
print(f"  Overhead:  {runtime_overhead_pct:+.2f}%")
print(f"  Threshold: <10%")
print(f"  Status:    {'✓ PASS' if runtime_overhead_pct < 10 else '✗ FAIL'}")
print()

if baseline_memory is not None and metrics_memory is not None:
    print(f"Memory:")
    print(f"  Baseline:  {baseline_memory:.1f}MB")
    print(f"  With metrics: {metrics_memory:.1f}MB")
    print(f"  Overhead:  {memory_overhead_mb:+.1f}MB")
    print(f"  Threshold: <30MB")
    print(f"  Status:    {'✓ PASS' if memory_overhead_mb < 30 else '✗ FAIL'}")
    print()
else:
    print(f"Memory: N/A (tracking unavailable)")
    print()

# Determine overall pass/fail
runtime_pass = runtime_overhead_pct < 10.0
memory_pass = memory_overhead_mb < 30.0 if memory_overhead_mb is not None else True

print("=" * 72)
if runtime_pass and memory_pass:
    print("OVERALL: ✓ PASS - Metrics overhead within acceptable limits")
    print("=" * 72)
    sys.exit(0)
else:
    print("OVERALL: ✗ FAIL - Metrics overhead exceeds thresholds")
    print("=" * 72)
    sys.exit(1)
EOF

exit $?
