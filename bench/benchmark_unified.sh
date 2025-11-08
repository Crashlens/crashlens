#!/bin/bash
# CrashLens Unified Engine Performance Benchmark
# Compares legacy guard vs unified engine performance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BENCH_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$BENCH_DIR")"
LOGS_DIR="$PROJECT_ROOT/sample-logs"
RESULTS_DIR="$BENCH_DIR/results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Performance thresholds (from spec)
MAX_TIME_OVERHEAD_PERCENT=15
MAX_MEMORY_OVERHEAD_PERCENT=25

# Create results directory
mkdir -p "$RESULTS_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CrashLens Unified Engine Benchmarks${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo "Results Dir:  $RESULTS_DIR"
echo "Timestamp:    $TIMESTAMP"
echo ""

# Check if test data exists
if [ ! -f "$LOGS_DIR/demo-logs.jsonl" ]; then
    echo -e "${RED}Error: demo-logs.jsonl not found in $LOGS_DIR${NC}"
    exit 1
fi

# Check if memory_profiler is installed
if ! command -v mprof &> /dev/null; then
    echo -e "${YELLOW}Warning: memory_profiler not installed. Installing...${NC}"
    pip install memory-profiler psutil 2>&1 | tail -3
fi

# Function to run a timed benchmark
run_benchmark() {
    local name="$1"
    local cmd="$2"
    local output_file="$RESULTS_DIR/${name}_${TIMESTAMP}.txt"
    
    echo -e "${BLUE}Running: $name${NC}"
    echo "Command: $cmd"
    
    # Run with time measurement
    /usr/bin/time -v $cmd > "$output_file" 2>&1 || true
    
    # Extract wall time and peak memory
    local wall_time=$(grep "Elapsed (wall clock) time" "$output_file" | awk '{print $8}' || echo "N/A")
    local peak_mem=$(grep "Maximum resident set size" "$output_file" | awk '{print $6}' || echo "N/A")
    
    echo "  Wall Time: $wall_time"
    echo "  Peak RSS:  ${peak_mem}KB"
    echo ""
    
    # Store results
    echo "$wall_time|$peak_mem" > "$RESULTS_DIR/${name}_${TIMESTAMP}.result"
}

# Function to run memory profiling
run_memory_profile() {
    local name="$1"
    local cmd="$2"
    local output_file="$RESULTS_DIR/${name}_${TIMESTAMP}_memory.dat"
    
    echo -e "${BLUE}Memory profiling: $name${NC}"
    
    # Run with memory profiler
    mprof run --output "$output_file" $cmd > /dev/null 2>&1 || true
    
    # Generate plot (optional)
    if command -v mprof &> /dev/null; then
        mprof plot "$output_file" -o "$RESULTS_DIR/${name}_${TIMESTAMP}_memory.png" 2>/dev/null || true
    fi
    
    echo "  Profile saved: $output_file"
    echo ""
}

# Prepare test rules
RULES_FILE="$PROJECT_ROOT/.crashlens/rules.yaml"
if [ ! -f "$RULES_FILE" ]; then
    echo -e "${YELLOW}Warning: Default rules.yaml not found, using retry-loop-detector${NC}"
    RULES_FILE="$PROJECT_ROOT/policies/retry-loop-detector.yaml"
fi

echo -e "${GREEN}=== Benchmark 1: Legacy Guard (Baseline) ===${NC}"
run_benchmark "legacy_guard" "poetry run crashlens guard $LOGS_DIR/demo-logs.jsonl --rules $RULES_FILE --output json --dry-run"

echo -e "${GREEN}=== Benchmark 2: Unified Guard (No Detectors) ===${NC}"
export CRASHLENS_USE_UNIFIED_ENGINE=1
run_benchmark "unified_guard_basic" "poetry run crashlens guard $LOGS_DIR/demo-logs.jsonl --rules $RULES_FILE --output json --dry-run"

echo -e "${GREEN}=== Benchmark 3: Policy-Check (Auto Unified) ===${NC}"
run_benchmark "policy_check" "poetry run crashlens policy-check $LOGS_DIR/demo-logs.jsonl --rules $RULES_FILE --output json --dry-run"

echo -e "${GREEN}=== Benchmark 4: Unified Guard with Detectors ===${NC}"
# Note: Detector support may not be fully implemented yet
# This is a placeholder for future detector integration
run_benchmark "unified_guard_detectors" "poetry run crashlens policy-check $LOGS_DIR/demo-logs.jsonl --rules $RULES_FILE --output json --dry-run"

# Memory profiling (optional, slower)
if [ "${RUN_MEMORY_PROFILE:-0}" = "1" ]; then
    echo ""
    echo -e "${GREEN}=== Memory Profiling ===${NC}"
    run_memory_profile "legacy_guard" "poetry run crashlens guard $LOGS_DIR/demo-logs.jsonl --rules $RULES_FILE --output json --dry-run"
    run_memory_profile "unified_guard" "poetry run crashlens policy-check $LOGS_DIR/demo-logs.jsonl --rules $RULES_FILE --output json --dry-run"
fi

# Compare results
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Performance Comparison${NC}"
echo -e "${BLUE}========================================${NC}"

# Parse results
if [ -f "$RESULTS_DIR/legacy_guard_${TIMESTAMP}.result" ] && [ -f "$RESULTS_DIR/unified_guard_basic_${TIMESTAMP}.result" ]; then
    legacy_result=$(cat "$RESULTS_DIR/legacy_guard_${TIMESTAMP}.result")
    unified_result=$(cat "$RESULTS_DIR/unified_guard_basic_${TIMESTAMP}.result")
    
    legacy_time=$(echo "$legacy_result" | cut -d'|' -f1)
    legacy_mem=$(echo "$legacy_result" | cut -d'|' -f2)
    unified_time=$(echo "$unified_result" | cut -d'|' -f1)
    unified_mem=$(echo "$unified_result" | cut -d'|' -f2)
    
    echo "Legacy Guard:"
    echo "  Time: $legacy_time"
    echo "  Memory: ${legacy_mem}KB"
    echo ""
    echo "Unified Guard (Basic):"
    echo "  Time: $unified_time"
    echo "  Memory: ${unified_mem}KB"
    echo ""
    
    # Calculate overhead (simplified - actual calculation would need proper time parsing)
    echo -e "${YELLOW}Note: Use bench/analyze_results.py for detailed overhead analysis${NC}"
fi

echo ""
echo -e "${GREEN}Benchmark complete!${NC}"
echo "Results saved to: $RESULTS_DIR"
echo ""
echo -e "${YELLOW}Performance Thresholds:${NC}"
echo "  Max Time Overhead:   +${MAX_TIME_OVERHEAD_PERCENT}%"
echo "  Max Memory Overhead: +${MAX_MEMORY_OVERHEAD_PERCENT}%"
echo ""
echo -e "${BLUE}To analyze results, run:${NC}"
echo "  python bench/analyze_results.py $RESULTS_DIR"
