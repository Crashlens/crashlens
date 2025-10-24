"""
CrashLens Prometheus Integration - Production Readiness Verification Suite

This script runs the 5 critical verification tests required for production release:

1. Lazy Loading (Do No Harm) - Proves zero performance penalty for non-users
2. Push Timeout (Failure-Proof) - Proves 2s timeout protects CI pipelines
3. On-Failure Metrics - Proves accurate failure tracking
4. Cardinality Cap (OOM Protection) - Proves memory protection works
5. Configuration Gates - Proves opt-in behavior and kill switch work

Usage:
    python tests/run_verification_suite.py
    
Exit Codes:
    0 - All tests passed
    1 - One or more tests failed
"""

import sys
import subprocess
from pathlib import Path
from typing import List, Tuple
import time


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text: str):
    """Print a styled header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")


def print_test_result(test_name: str, passed: bool, duration: float):
    """Print test result with color coding"""
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"  {status} {test_name} ({duration:.2f}s)")


def run_test(test_file: str) -> Tuple[bool, float, str]:
    """
    Run a single test file and return success status, duration, and output.
    
    Returns:
        (success, duration_seconds, output)
    """
    start = time.monotonic()
    
    try:
        result = subprocess.run(
            ['pytest', test_file, '-v', '--tb=short'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent
        )
        
        duration = time.monotonic() - start
        success = result.returncode == 0
        output = result.stdout + result.stderr
        
        return success, duration, output
        
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - start
        return False, duration, f"Test timed out after 60 seconds"
    except Exception as e:
        duration = time.monotonic() - start
        return False, duration, f"Test execution error: {str(e)}"


def main():
    """Run all verification tests and generate report"""
    
    print_header("CrashLens Prometheus Integration - Verification Suite")
    
    # Define the 5 critical tests
    tests = [
        {
            'file': 'tests/test_lazy_import.py',
            'name': 'Test 1: Lazy Loading (Do No Harm)',
            'description': 'Proves zero performance penalty for non-users'
        },
        {
            'file': 'tests/test_fire_and_forget_push_default_non_blocking.py',
            'name': 'Test 2: Push Timeout (Failure-Proof)',
            'description': 'Proves 2s timeout protects CI pipelines'
        },
        {
            'file': 'tests/test_push_success_failure_counters.py',
            'name': 'Test 3: On-Failure Metrics',
            'description': 'Proves accurate failure tracking'
        },
        {
            'file': 'tests/test_cardinality_cap_and_overflow.py',
            'name': 'Test 4: Cardinality Cap (OOM Protection)',
            'description': 'Proves memory protection works'
        },
        {
            'file': 'tests/test_metrics_disabled_by_default.py',
            'name': 'Test 5: Configuration Gates',
            'description': 'Proves opt-in behavior and kill switch work'
        },
    ]
    
    results = []
    total_duration = 0
    
    print(f"{Colors.BOLD}Running 5 Critical Verification Tests...{Colors.END}\n")
    
    # Run each test
    for i, test in enumerate(tests, 1):
        print(f"{Colors.BOLD}[{i}/5] {test['name']}{Colors.END}")
        print(f"      {test['description']}")
        
        success, duration, output = run_test(test['file'])
        total_duration += duration
        
        results.append({
            'test': test,
            'success': success,
            'duration': duration,
            'output': output
        })
        
        print_test_result(test['name'], success, duration)
    
    # Print summary
    print_header("Verification Suite Results")
    
    passed_count = sum(1 for r in results if r['success'])
    failed_count = len(results) - passed_count
    
    print(f"{Colors.BOLD}Summary:{Colors.END}")
    print(f"  Total Tests:  {len(results)}")
    print(f"  {Colors.GREEN}Passed:       {passed_count}{Colors.END}")
    print(f"  {Colors.RED}Failed:       {failed_count}{Colors.END}")
    print(f"  Total Time:   {total_duration:.2f}s")
    
    # Show details for failed tests
    if failed_count > 0:
        print(f"\n{Colors.BOLD}{Colors.RED}Failed Test Details:{Colors.END}\n")
        for result in results:
            if not result['success']:
                print(f"{Colors.RED}✗ {result['test']['name']}{Colors.END}")
                print(f"  File: {result['test']['file']}")
                print(f"  Duration: {result['duration']:.2f}s")
                print(f"\n  Output (last 50 lines):")
                output_lines = result['output'].split('\n')[-50:]
                for line in output_lines:
                    print(f"    {line}")
                print()
    
    # Final verdict
    print(f"\n{Colors.BOLD}{'='*80}{Colors.END}")
    
    if failed_count == 0:
        print(f"{Colors.BOLD}{Colors.GREEN}{'✓ ALL VERIFICATION TESTS PASSED'.center(80)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'Prometheus Integration is PRODUCTION READY'.center(80)}{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
        return 0
    else:
        print(f"{Colors.BOLD}{Colors.RED}{'✗ VERIFICATION FAILED'.center(80)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.RED}{f'{failed_count} test(s) failed - NOT PRODUCTION READY'.center(80)}{Colors.END}")
        print(f"{Colors.BOLD}{'='*80}{Colors.END}\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
