#!/bin/bash
# Quick Verification Script for Prometheus Test Suite
# Run this to validate all tests pass in one command
# 
# Usage: bash scripts/run_all_prometheus_tests.sh

set -e  # Exit on error

echo "========================================================================"
echo "CRASHLENS PROMETHEUS INTEGRATION TEST SUITE"
echo "========================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILED_TESTS=""

echo "${YELLOW}[1/9]${NC} Running test_lazy_import.py..."
if pytest tests/test_lazy_import.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_lazy_import.py"
fi
echo ""

echo "${YELLOW}[2/9]${NC} Running test_registry_isolation.py..."
if pytest tests/test_registry_isolation.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_registry_isolation.py"
fi
echo ""

echo "${YELLOW}[3/9]${NC} Running test_cardinality_cap_and_overflow.py..."
if pytest tests/test_cardinality_cap_and_overflow.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_cardinality_cap_and_overflow.py"
fi
echo ""

echo "${YELLOW}[4/9]${NC} Running test_fire_and_forget_push_default_non_blocking.py..."
if pytest tests/test_fire_and_forget_push_default_non_blocking.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_fire_and_forget_push_default_non_blocking.py"
fi
echo ""

echo "${YELLOW}[5/9]${NC} Running test_fire_and_forget_push_strict_mode_fails.py..."
if pytest tests/test_fire_and_forget_push_strict_mode_fails.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_fire_and_forget_push_strict_mode_fails.py"
fi
echo ""

echo "${YELLOW}[6/9]${NC} Running test_push_success_failure_counters.py..."
if pytest tests/test_push_success_failure_counters.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_push_success_failure_counters.py"
fi
echo ""

echo "${YELLOW}[7/9]${NC} Running test_registry_cardinality_gauge_value.py..."
if pytest tests/test_registry_cardinality_gauge_value.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_registry_cardinality_gauge_value.py"
fi
echo ""

echo "${YELLOW}[8/9]${NC} Running test_log_rotation_to_tmp.py..."
if pytest tests/test_log_rotation_to_tmp.py -v; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS test_log_rotation_to_tmp.py"
fi
echo ""

echo "${YELLOW}[9/9]${NC} Running benchmark_memory_and_runtime.py..."
if python benchmarks/benchmark_memory_and_runtime.py; then
    echo "${GREEN}✓${NC} PASSED"
else
    echo "${RED}✗${NC} FAILED"
    FAILED_TESTS="$FAILED_TESTS benchmark_memory_and_runtime.py"
fi
echo ""

echo "========================================================================"
if [ -z "$FAILED_TESTS" ]; then
    echo "${GREEN}ALL TESTS PASSED ✓${NC}"
    echo "========================================================================"
    echo "Production Readiness: ✅ VERIFIED"
    echo "  - Lazy loading: ✅"
    echo "  - Registry isolation: ✅"
    echo "  - Cardinality cap (500): ✅"
    echo "  - Non-blocking push: ✅"
    echo "  - Strict mode: ✅"
    echo "  - Push counters: ✅"
    echo "  - Cardinality gauge: ✅"
    echo "  - Log rotation: ✅"
    echo "  - Performance (<10% overhead): ✅"
    echo "========================================================================"
    exit 0
else
    echo "${RED}SOME TESTS FAILED ✗${NC}"
    echo "========================================================================"
    echo "Failed tests:"
    for test in $FAILED_TESTS; do
        echo "  ${RED}✗${NC} $test"
    done
    echo "========================================================================"
    exit 1
fi
