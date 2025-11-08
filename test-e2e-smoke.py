"""
E2E Smoke Tests for Guard Command
Tests guard on production-like logs with comprehensive scenarios
"""
import subprocess
import sys
import json
from pathlib import Path

def run_command(cmd, env=None):
    """Run command and return result"""
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        env=env
    )
    return result

def test_e2e_smoke():
    """Run comprehensive E2E smoke tests"""
    
    print("=" * 70)
    print("E2E Smoke Tests - Guard Command")
    print("=" * 70)
    print()
    
    tests = []
    
    # Test 1: Demo logs with test rules
    print("TEST 1: Demo logs with boolean logic rules")
    print("-" * 70)
    
    result = run_command([
        sys.executable, "-m", "crashlens",
        "guard", "sample-logs/demo-logs.jsonl",
        "--rules", "test-rules.yaml",
        "--output", "json",
        "--report-path", "test-e2e-demo.json"
    ])
    
    try:
        report = json.loads(result.stdout)
        summary = report['summary']
        
        test1_pass = (
            result.returncode in [0, 1] and
            'total_rules' in summary and
            'violations' in summary and
            summary['total_rules'] > 0
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Total rules: {summary['total_rules']}")
        print(f"Violations: {summary['violations']}")
        print(f"Status: {'✅ PASS' if test1_pass else '❌ FAIL'}")
        
        tests.append(("Demo logs", test1_pass))
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        print(f"Stdout: {result.stdout[:500]}")
        print(f"Stderr: {result.stderr[:500]}")
        tests.append(("Demo logs", False))
    
    print()
    
    # Test 2: PII stripping
    print("TEST 2: PII stripping functionality")
    print("-" * 70)
    
    result = run_command([
        sys.executable, "-m", "crashlens",
        "guard", "sample-logs/demo-logs.jsonl",
        "--rules", "test-rules.yaml",
        "--strip-pii",
        "--output", "json"
    ])
    
    try:
        report = json.loads(result.stdout)
        
        # Check that examples don't contain obvious PII patterns
        pii_found = False
        for rule_data in report['rules'].values():
            for example in rule_data.get('examples', []):
                prompt = example.get('prompt', '')
                # Simple check - real emails should be stripped
                if '@' in prompt and '.com' in prompt:
                    pii_found = True
        
        test2_pass = result.returncode in [0, 1] and not pii_found
        
        print(f"Exit code: {result.returncode}")
        print(f"PII found: {pii_found}")
        print(f"Status: {'✅ PASS' if test2_pass else '❌ FAIL'}")
        
        tests.append(("PII stripping", test2_pass))
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        tests.append(("PII stripping", False))
    
    print()
    
    # Test 3: Multiple output formats
    print("TEST 3: Multiple output formats")
    print("-" * 70)
    
    formats = ["json", "md", "text", "html"]
    format_results = []
    
    for fmt in formats:
        result = run_command([
            sys.executable, "-m", "crashlens",
            "guard", "sample-logs/demo-logs.jsonl",
            "--rules", "test-rules.yaml",
            "--output", fmt
        ])
        
        format_ok = result.returncode in [0, 1] and len(result.stdout) > 0
        format_results.append((fmt, format_ok))
        print(f"  {fmt}: {'✅' if format_ok else '❌'}")
    
    test3_pass = all(ok for _, ok in format_results)
    print(f"Status: {'✅ PASS' if test3_pass else '❌ FAIL'}")
    tests.append(("Output formats", test3_pass))
    
    print()
    
    # Test 4: Dry-run mode (never fails)
    print("TEST 4: Dry-run mode enforcement")
    print("-" * 70)
    
    # Create test files for dry-run test
    test_dir = Path("test-e2e-dryrun")
    test_dir.mkdir(exist_ok=True)
    
    test_rule = """version: 1
rules:
  - id: TEST_DRYRUN
    description: "Test dry-run"
    severity: fatal
    if:
      input.model: "gpt-4o"
    then: fail_ci
    action: fail_ci
    message: "Test violation"
"""
    
    test_log = """{"traceId": "test1", "input": {"model": "gpt-4o"}, "usage": {"prompt_tokens": 100, "completion_tokens": 50}}
"""
    
    rule_file = test_dir / "test-rule.yaml"
    log_file = test_dir / "test-log.jsonl"
    
    rule_file.write_text(test_rule)
    log_file.write_text(test_log)
    
    result = run_command([
        sys.executable, "-m", "crashlens",
        "guard", str(log_file),
        "--rules", str(rule_file),
        "--fail-on-violations",
        "--dry-run",
        "--output", "json"
    ])
    
    test4_pass = result.returncode == 0 and "dry-run" in result.stderr.lower()
    
    print(f"Exit code: {result.returncode} (expected: 0)")
    print(f"Dry-run message: {'present' if 'dry-run' in result.stderr.lower() else 'missing'}")
    print(f"Status: {'✅ PASS' if test4_pass else '❌ FAIL'}")
    
    tests.append(("Dry-run mode", test4_pass))
    
    # Cleanup
    rule_file.unlink()
    log_file.unlink()
    test_dir.rmdir()
    
    print()
    
    # Test 5: Rule suppression
    print("TEST 5: Rule suppression")
    print("-" * 70)
    
    # First get violations without suppression
    result1 = run_command([
        sys.executable, "-m", "crashlens",
        "guard", "sample-logs/demo-logs.jsonl",
        "--rules", "test-rules.yaml",
        "--output", "json"
    ])
    
    try:
        report1 = json.loads(result1.stdout)
        violations_before = report1['summary']['violations']
        
        # Get first rule ID if any violations
        if violations_before > 0:
            first_rule_id = next(
                (rid for rid, data in report1['rules'].items() if data['count'] > 0),
                None
            )
            
            if first_rule_id:
                # Run with suppression
                result2 = run_command([
                    sys.executable, "-m", "crashlens",
                    "guard", "sample-logs/demo-logs.jsonl",
                    "--rules", "test-rules.yaml",
                    "--suppress", first_rule_id,
                    "--output", "json"
                ])
                
                report2 = json.loads(result2.stdout)
                violations_after = report2['summary']['violations']
                
                test5_pass = violations_after < violations_before
                
                print(f"Violations before: {violations_before}")
                print(f"Violations after suppressing {first_rule_id}: {violations_after}")
                print(f"Status: {'✅ PASS' if test5_pass else '❌ FAIL'}")
                
                tests.append(("Rule suppression", test5_pass))
            else:
                print("⚠️ SKIP: No violations to suppress")
                tests.append(("Rule suppression", True))
        else:
            print("⚠️ SKIP: No violations found")
            tests.append(("Rule suppression", True))
            
    except Exception as e:
        print(f"❌ FAIL: {e}")
        tests.append(("Rule suppression", False))
    
    print()
    
    # Test 6: Stdin input
    print("TEST 6: Stdin input handling")
    print("-" * 70)
    
    # Read demo logs content
    log_content = Path("sample-logs/demo-logs.jsonl").read_text()
    
    result = run_command([
        sys.executable, "-m", "crashlens",
        "guard", "-",
        "--rules", "test-rules.yaml",
        "--output", "json"
    ])
    
    # Send log content via stdin
    result = subprocess.run(
        [sys.executable, "-m", "crashlens", "guard", "-", 
         "--rules", "test-rules.yaml", "--output", "json"],
        input=log_content,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace'
    )
    
    try:
        report = json.loads(result.stdout)
        test6_pass = (
            result.returncode in [0, 1] and
            'summary' in report and
            report['summary']['total_rules'] > 0
        )
        
        print(f"Exit code: {result.returncode}")
        print(f"Total rules: {report['summary']['total_rules']}")
        print(f"Status: {'✅ PASS' if test6_pass else '❌ FAIL'}")
        
        tests.append(("Stdin input", test6_pass))
        
    except Exception as e:
        print(f"❌ FAIL: {e}")
        tests.append(("Stdin input", False))
    
    print()
    
    # Summary
    print("=" * 70)
    passed = sum(1 for _, ok in tests if ok)
    total = len(tests)
    print(f"SUMMARY: {passed}/{total} tests passed")
    print("=" * 70)
    print()
    
    for test_name, passed in tests:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name}")
    
    print()
    
    return all(ok for _, ok in tests)

if __name__ == "__main__":
    success = test_e2e_smoke()
    sys.exit(0 if success else 1)
