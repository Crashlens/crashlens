#!/usr/bin/env python3
"""
Local test script to simulate the GitHub Actions workflow
Tests both valid and violating log files against schema contracts
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status"""
    print(f"\n[TEST] {description}")
    print("=" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        status = "PASSED" if success else "FAILED"
        print(f"\n{status} (Exit code: {result.returncode})")
        return success
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Main test function"""
    print("CrashLens Schema Contract Validation Test")
    print("=" * 60)
    print("This script simulates the GitHub Actions workflow locally")
    
    # Check if CrashLens is installed
    print("\nChecking CrashLens installation...")
    if not run_command("crashlens --help", "Verify CrashLens CLI is available"):
        print("CrashLens CLI not found. Please install with: pip install .")
        return False
    
    # Test schema contract info
    run_command(
        "crashlens scan --contract-info --log-format langfuse-v1",
        "Show Langfuse v1 schema contract requirements"
    )
    
    # Test with valid log file
    valid_test = run_command(
        "crashlens scan --contract-check tests/demo-logs/sample-valid.jsonl --log-format langfuse-v1",
        "Test valid log file (should PASS)"
    )
    
    # Test with violating log file  
    violating_test = run_command(
        "crashlens scan --contract-check tests/demo-logs/sample-violating.jsonl --log-format langfuse-v1",
        "Test violating log file (should FAIL)"
    )
    
    # Test with langfuse-v2 schema
    v2_test = run_command(
        "crashlens scan --contract-check tests/demo-logs/sample-valid.jsonl --log-format langfuse-v2",
        "Test valid file against v2 schema (should FAIL - missing userId)"
    )
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    results = [
        ("Valid file vs v1 schema", valid_test, True),
        ("Violating file vs v1 schema", not violating_test, True),  # Should fail
        ("Valid file vs v2 schema", not v2_test, True),  # Should fail (missing userId)
    ]
    
    all_passed = True
    for test_name, actual, expected in results:
        status = "PASS" if actual == expected else "FAIL"
        print(f"{status} {test_name}")
        if actual != expected:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("All tests behaved as expected!")
        print("The GitHub Actions workflow should work correctly")
    else:
        print("Some tests didn't behave as expected")
        print("Check the CrashLens contract validation logic")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
