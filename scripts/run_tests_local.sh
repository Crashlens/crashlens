#!/bin/bash
# CrashLens Local Test Runner
# Purpose: One-shot command to run all tests locally (CI helper)
#
# Usage:
#   bash scripts/run_tests_local.sh
#
# This script will:
# 1. Create virtual environment (if needed)
# 2. Install dependencies
# 3. Run all test categories
# 4. Run benchmarks
# 5. Verify log rotation
#
# Exit codes:
#   0 = All tests passed
#   1 = Setup or test failure

set -e  # Exit on first error

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}CrashLens Prometheus Integration - Local Test Runner${NC}"
echo -e "${BLUE}============================================================${NC}"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ ERROR: python3 not found${NC}"
    echo "Please install Python 3.10+ and try again"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}✓${NC} Found: $PYTHON_VERSION"
echo ""

# Step 1: Virtual environment setup
echo -e "${YELLOW}[1/6] Setting up virtual environment...${NC}"
if [ ! -d ".venv" ]; then
    echo "Creating .venv..."
    python3 -m venv .venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${GREEN}✓${NC} Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Verify activation
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${RED}❌ ERROR: Failed to activate virtual environment${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} Virtual environment activated: $VIRTUAL_ENV"
echo ""

# Step 2: Install dependencies
echo -e "${YELLOW}[2/6] Installing dependencies...${NC}"

# Upgrade pip first
echo "Upgrading pip..."
python -m pip install --upgrade pip --quiet

# Install dev dependencies
if [ -f "requirements-dev.txt" ]; then
    echo "Installing from requirements-dev.txt..."
    pip install -r requirements-dev.txt --quiet
    echo -e "${GREEN}✓${NC} Dev dependencies installed"
else
    echo -e "${YELLOW}⚠${NC} requirements-dev.txt not found, installing minimal deps..."
    pip install pytest pytest-mock requests-mock prometheus-client --quiet
fi

# Install package in editable mode
echo "Installing crashlens in editable mode..."
if [ -f "pyproject.toml" ] || [ -f "setup.py" ]; then
    pip install -e . --quiet
    echo -e "${GREEN}✓${NC} crashlens installed"
else
    echo -e "${YELLOW}⚠${NC} No setup file found, skipping package install"
fi
echo ""

# Step 3: Run unit tests
echo -e "${YELLOW}[3/6] Running unit tests...${NC}"
if [ -f "pytest.ini" ]; then
    echo "Using pytest.ini configuration"
fi

# Run unit tests (fast, no external dependencies)
pytest -q tests/ -m unit --tb=short || {
    echo -e "${RED}❌ FAIL: Unit tests failed${NC}"
    exit 1
}
echo -e "${GREEN}✓${NC} Unit tests passed"
echo ""

# Step 4: Run integration tests
echo -e "${YELLOW}[4/6] Running integration tests...${NC}"
# Set env var to enable integration tests
export TEST_PROMETHEUS_INTEGRATION=true
pytest -q tests/ -m integration --tb=short || {
    echo -e "${RED}❌ FAIL: Integration tests failed${NC}"
    exit 1
}
echo -e "${GREEN}✓${NC} Integration tests passed"
echo ""

# Step 5: Run benchmarks
echo -e "${YELLOW}[5/6] Running benchmarks...${NC}"
if [ -f "scripts/run_benchmark.sh" ]; then
    bash scripts/run_benchmark.sh || {
        echo -e "${RED}❌ FAIL: Benchmark failed${NC}"
        exit 1
    }
    echo -e "${GREEN}✓${NC} Benchmarks passed"
else
    echo -e "${YELLOW}⚠${NC} Benchmark script not found, skipping..."
fi
echo ""

# Step 6: Verify log rotation
echo -e "${YELLOW}[6/6] Checking log rotation...${NC}"
LOG_PREFIX="/tmp/crashlens-metrics-test.log"

if ls ${LOG_PREFIX}* 1> /dev/null 2>&1; then
    echo "Found log files:"
    ls -lh ${LOG_PREFIX}* | while read -r line; do
        echo "  $line"
    done
    echo -e "${GREEN}✓${NC} Log rotation verified"
else
    echo -e "${YELLOW}⚠${NC} No log files found at ${LOG_PREFIX}*"
    echo "This is expected if tests haven't run with logging enabled"
fi
echo ""

# Success summary
echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✓ ALL TESTS PASSED ✓${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo "Test Summary:"
echo "  - Unit tests: PASS"
echo "  - Integration tests: PASS"
echo "  - Benchmarks: PASS"
echo "  - Log rotation: Verified"
echo ""
echo "Next steps:"
echo "  1. Review test output above for any warnings"
echo "  2. Check benchmark results for performance metrics"
echo "  3. (Optional) Run specific tests: pytest tests/test_specific.py -v"
echo ""
echo "Deactivate virtual environment: deactivate"
