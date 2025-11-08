"""
Test GUARD_ENFORCE environment variable fail-safe toggle
"""
import os
import json
from pathlib import Path
import subprocess
import sys

def test_guard_enforce():
    """Test GUARD_ENFORCE fail-safe toggle"""
    
    print("=" * 60)
    print("Testing GUARD_ENFORCE Fail-Safe Toggle")
    print("=" * 60)
    print()
    
    # Create test rule that will trigger violation
    test_rule = """version: 1
rules:
  - id: TEST_ENFORCE
    description: "Test enforcement toggle"
    severity: fatal
    if:
      input.model: "gpt-4o"
    then: fail_ci
    action: fail_ci
    message: "Test violation"
"""
    
    # Create test log that triggers violation
    test_log = """{"traceId": "test1", "input": {"model": "gpt-4o"}, "usage": {"prompt_tokens": 100, "completion_tokens": 50}}
"""
    
    test_dir = Path("test-guard-enforce")
    test_dir.mkdir(exist_ok=True)
    
    rule_file = test_dir / "test-rule.yaml"
    log_file = test_dir / "test-log.jsonl"
    
    rule_file.write_text(test_rule)
    log_file.write_text(test_log)
    
    tests = [
        {
            "name": "TEST 1: Enforcement ENABLED (default)",
            "env": {},
            "expected_exit": 1,
            "expected_message": "Failing due to policy violations"
        },
        {
            "name": "TEST 2: Enforcement ENABLED (explicit true)",
            "env": {"GUARD_ENFORCE": "true"},
            "expected_exit": 1,
            "expected_message": "Failing due to policy violations"
        },
        {
            "name": "TEST 3: Enforcement DISABLED (false)",
            "env": {"GUARD_ENFORCE": "false"},
            "expected_exit": 0,
            "expected_message": "Guard enforcement disabled"
        },
        {
            "name": "TEST 4: Enforcement DISABLED (0)",
            "env": {"GUARD_ENFORCE": "0"},
            "expected_exit": 0,
            "expected_message": "Guard enforcement disabled"
        },
        {
            "name": "TEST 5: Enforcement DISABLED (no)",
            "env": {"GUARD_ENFORCE": "no"},
            "expected_exit": 0,
            "expected_message": "Guard enforcement disabled"
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"\n{test['name']}")
        print("-" * 60)
        
        # Build command
        cmd = [
            sys.executable, "-m", "crashlens",
            "guard", str(log_file),
            "--rules", str(rule_file),
            "--fail-on-violations",
            "--output", "json"
        ]
        
        # Set environment
        env = os.environ.copy()
        # Remove GUARD_ENFORCE to test default behavior
        if 'GUARD_ENFORCE' in env and not test['env'].get('GUARD_ENFORCE'):
            del env['GUARD_ENFORCE']
        env.update(test['env'])
        
        # Run command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        
        # Check exit code
        exit_ok = result.returncode == test['expected_exit']
        stderr_text = result.stderr or ""
        message_ok = test['expected_message'] in stderr_text
        
        print(f"Environment: {test['env'] or '(default)'}")
        print(f"Expected exit: {test['expected_exit']}, Got: {result.returncode}")
        print(f"Expected message: '{test['expected_message']}'")
        print(f"Message present: {message_ok}")
        
        if exit_ok and message_ok:
            print("✅ PASS")
            passed += 1
        else:
            print("❌ FAIL")
            failed += 1
            print("\nStderr output:")
            print(result.stderr)
        
        print()
    
    # Summary
    print("=" * 60)
    print(f"SUMMARY: {passed}/{len(tests)} tests passed")
    print("=" * 60)
    
    # Cleanup
    rule_file.unlink()
    log_file.unlink()
    test_dir.rmdir()
    
    return failed == 0

if __name__ == "__main__":
    success = test_guard_enforce()
    sys.exit(0 if success else 1)
