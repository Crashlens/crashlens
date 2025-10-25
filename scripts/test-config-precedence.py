#!/usr/bin/env python3
"""
Config Precedence Testing Script for CrashLens Phase 2

Tests the precedence order: CLI > ENV > YAML > Defaults
Validates error handling, schema validation, and graceful fallbacks.

Usage:
    python scripts/test-config-precedence.py
    python scripts/test-config-precedence.py --verbose
"""

import sys
import os
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class TestScenario:
    """Represents a single config precedence test scenario"""
    name: str
    description: str
    cli_flags: List[str] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)
    yaml_content: Optional[str] = None
    expected_winner: str = ""  # "CLI", "ENV", "YAML", "DEFAULT"
    expected_value: Optional[str] = None
    should_fail: bool = False
    expected_error: Optional[str] = None


def create_temp_yaml(content: str) -> Path:
    """Create temporary YAML file with content"""
    tmpfile = tempfile.NamedTemporaryFile(
        mode='w', suffix='.yaml', delete=False, encoding='utf-8'
    )
    tmpfile.write(content)
    tmpfile.close()
    return Path(tmpfile.name)


def create_temp_jsonl(num_traces: int = 10) -> Path:
    """Create temporary JSONL test file"""
    tmpfile = tempfile.NamedTemporaryFile(
        mode='w', suffix='.jsonl', delete=False, encoding='utf-8'
    )
    for i in range(num_traces):
        trace = {
            'traceId': f'test-{i}',
            'model': 'gpt-4',
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50}
        }
        tmpfile.write(json.dumps(trace) + '\n')
    tmpfile.close()
    return Path(tmpfile.name)


def run_crashlens_scan(
    log_file: Path,
    cli_flags: List[str],
    env_vars: Dict[str, str],
    config_file: Optional[Path] = None
) -> Tuple[int, str, str]:
    """
    Run crashlens scan command with specified config sources.
    
    Returns:
        Tuple of (exit_code, stdout, stderr)
    """
    # Build command
    cmd = ['crashlens', 'scan', str(log_file)]
    
    # Add config file if provided
    if config_file:
        cmd.extend(['--metrics-config', str(config_file)])
    
    # Add additional CLI flags
    cmd.extend(cli_flags)
    
    # Setup environment
    env = os.environ.copy()
    env.update(env_vars)
    
    # Run command
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=30
        )
        return (result.returncode, result.stdout, result.stderr)
    except subprocess.TimeoutExpired:
        return (124, "", "ERROR: Command timed out after 30 seconds")
    except Exception as e:
        return (1, "", f"ERROR: {e}")


def test_scenario(
    scenario: TestScenario,
    log_file: Path,
    verbose: bool = False
) -> Tuple[bool, str]:
    """
    Test a single config precedence scenario.
    
    Returns:
        Tuple of (passed, message)
    """
    print(f"\n{'='*80}")
    print(f"Test: {scenario.name}")
    print(f"Description: {scenario.description}")
    print(f"Expected Winner: {scenario.expected_winner}")
    print(f"{'='*80}")
    
    # Create YAML config if provided
    config_file = None
    if scenario.yaml_content:
        config_file = create_temp_yaml(scenario.yaml_content)
        if verbose:
            print(f"Created temp config: {config_file}")
    
    try:
        # Run command
        exit_code, stdout, stderr = run_crashlens_scan(
            log_file,
            scenario.cli_flags,
            scenario.env_vars,
            config_file
        )
        
        # Log output
        if verbose:
            print(f"\nExit code: {exit_code}")
            print(f"STDOUT:\n{stdout}")
            print(f"STDERR:\n{stderr}")
        
        # Check if command should have failed
        if scenario.should_fail:
            if exit_code != 0:
                # Check for expected error message
                if scenario.expected_error:
                    combined_output = stdout + stderr
                    if scenario.expected_error.lower() in combined_output.lower():
                        print(f"✓ PASS: Failed as expected with correct error message")
                        print(f"  Expected: '{scenario.expected_error}'")
                        print(f"  Found in output: YES")
                        return (True, "Failed gracefully with expected error")
                    else:
                        print(f"✗ FAIL: Failed but with wrong error message")
                        print(f"  Expected: '{scenario.expected_error}'")
                        print(f"  Got: {combined_output[:200]}")
                        return (False, f"Wrong error message")
                else:
                    print(f"✓ PASS: Failed as expected")
                    return (True, "Failed gracefully")
            else:
                print(f"✗ FAIL: Should have failed but succeeded")
                return (False, "Expected failure but command succeeded")
        
        # Check if command should have succeeded
        if exit_code != 0:
            print(f"✗ FAIL: Command failed unexpectedly")
            print(f"  Exit code: {exit_code}")
            print(f"  Error: {stderr[:200]}")
            return (False, f"Unexpected failure: {stderr[:100]}")
        
        # Validate expected value if provided
        if scenario.expected_value:
            combined_output = stdout + stderr
            if scenario.expected_value in combined_output:
                print(f"✓ PASS: Found expected value '{scenario.expected_value}'")
                print(f"  Winner: {scenario.expected_winner}")
                return (True, f"Config from {scenario.expected_winner}")
            else:
                print(f"✗ FAIL: Expected value not found")
                print(f"  Expected: '{scenario.expected_value}'")
                print(f"  Search in: {combined_output[:300]}")
                return (False, f"Expected value '{scenario.expected_value}' not found")
        
        # Generic success
        print(f"✓ PASS: Command succeeded")
        return (True, f"Config from {scenario.expected_winner}")
        
    finally:
        # Cleanup temp config
        if config_file and config_file.exists():
            config_file.unlink()


def define_test_scenarios() -> List[TestScenario]:
    """Define all config precedence test scenarios"""
    
    scenarios = []
    
    # Scenario A: CLI flag wins over defaults
    scenarios.append(TestScenario(
        name="A: CLI > Defaults",
        description="CLI flag should override default values",
        cli_flags=['--metrics-sample-rate', '0.25'],
        env_vars={},
        yaml_content=None,
        expected_winner="CLI",
        expected_value="0.25"
    ))
    
    # Scenario B: Env var wins over defaults
    scenarios.append(TestScenario(
        name="B: ENV > Defaults",
        description="Environment variable should override defaults",
        cli_flags=[],
        env_vars={'CRASHLENS_METRICS_SAMPLE_RATE': '0.35'},
        yaml_content=None,
        expected_winner="ENV",
        expected_value="0.35"
    ))
    
    # Scenario C: YAML wins over defaults
    scenarios.append(TestScenario(
        name="C: YAML > Defaults",
        description="YAML config should override defaults",
        cli_flags=[],
        env_vars={},
        yaml_content="""
metrics:
  enabled: true
  sampling:
    rate: 0.45
""",
        expected_winner="YAML",
        expected_value="0.45"
    ))
    
    # Scenario D: Defaults only
    scenarios.append(TestScenario(
        name="D: Defaults only",
        description="Use defaults when no config provided",
        cli_flags=[],
        env_vars={},
        yaml_content=None,
        expected_winner="DEFAULT",
        expected_value="1.0"  # Default sample rate
    ))
    
    # Scenario E: CLI wins over ENV
    scenarios.append(TestScenario(
        name="E: CLI > ENV",
        description="CLI flag should override environment variable",
        cli_flags=['--metrics-sample-rate', '0.55'],
        env_vars={'CRASHLENS_METRICS_SAMPLE_RATE': '0.65'},
        yaml_content=None,
        expected_winner="CLI",
        expected_value="0.55"
    ))
    
    # Scenario F: ENV wins over YAML
    scenarios.append(TestScenario(
        name="F: ENV > YAML",
        description="Environment variable should override YAML config",
        cli_flags=[],
        env_vars={'CRASHLENS_METRICS_SAMPLE_RATE': '0.75'},
        yaml_content="""
metrics:
  enabled: true
  sampling:
    rate: 0.85
""",
        expected_winner="ENV",
        expected_value="0.75"
    ))
    
    # Scenario G: CLI wins over YAML
    scenarios.append(TestScenario(
        name="G: CLI > YAML",
        description="CLI flag should override YAML config",
        cli_flags=['--metrics-sample-rate', '0.95'],
        env_vars={},
        yaml_content="""
metrics:
  enabled: true
  sampling:
    rate: 0.15
""",
        expected_winner="CLI",
        expected_value="0.95"
    ))
    
    # Scenario H: Malformed YAML (graceful failure)
    scenarios.append(TestScenario(
        name="H: Malformed YAML",
        description="Malformed YAML should fail gracefully with error log",
        cli_flags=[],
        env_vars={},
        yaml_content="""
metrics:
  enabled: true
  sampling:
    rate: [this is not a valid rate]
    indentation_error
""",
        expected_winner="N/A",
        should_fail=True,
        expected_error="YAML"
    ))
    
    # Additional scenarios for robustness
    
    # Scenario I: Invalid type (string instead of float)
    scenarios.append(TestScenario(
        name="I: Invalid Type",
        description="Invalid type should be caught by schema validation",
        cli_flags=[],
        env_vars={},
        yaml_content="""
metrics:
  enabled: true
  sampling:
    rate: "not_a_number"
""",
        expected_winner="N/A",
        should_fail=True,
        expected_error="validation"
    ))
    
    # Scenario J: Out of range value
    scenarios.append(TestScenario(
        name="J: Out of Range",
        description="Out of range value should be caught",
        cli_flags=[],
        env_vars={},
        yaml_content="""
metrics:
  enabled: true
  sampling:
    rate: 2.5
""",
        expected_winner="N/A",
        should_fail=True,
        expected_error="less than or equal to 1"
    ))
    
    # Scenario K: Missing required field (should use defaults)
    scenarios.append(TestScenario(
        name="K: Missing Optional Field",
        description="Missing optional fields should use defaults",
        cli_flags=[],
        env_vars={},
        yaml_content="""
metrics:
  enabled: true
""",
        expected_winner="YAML+DEFAULT",
        should_fail=False
    ))
    
    # Scenario L: Kill switch overrides everything
    scenarios.append(TestScenario(
        name="L: Kill Switch",
        description="CRASHLENS_DISABLE_METRICS should override all other config",
        cli_flags=['--push-metrics'],
        env_vars={'CRASHLENS_DISABLE_METRICS': 'true'},
        yaml_content="""
metrics:
  enabled: true
  sampling:
    rate: 1.0
""",
        expected_winner="KILL_SWITCH",
        should_fail=False  # Should succeed but not push metrics
    ))
    
    return scenarios


def run_all_tests(verbose: bool = False) -> Tuple[int, int]:
    """
    Run all config precedence tests.
    
    Returns:
        Tuple of (passed_count, total_count)
    """
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                 CONFIG PRECEDENCE TEST SUITE                               ║
║                                                                            ║
║  Testing precedence order: CLI > ENV > YAML > Defaults                    ║
║  Validating error handling, schema validation, graceful fallbacks         ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Create test log file
    log_file = create_temp_jsonl(10)
    print(f"Created test log file: {log_file}")
    
    scenarios = define_test_scenarios()
    results = []
    
    try:
        for scenario in scenarios:
            passed, message = test_scenario(scenario, log_file, verbose)
            results.append((scenario.name, passed, message))
        
        # Print summary
        print(f"\n{'='*80}")
        print("TEST SUMMARY")
        print(f"{'='*80}\n")
        
        passed_count = sum(1 for _, passed, _ in results if passed)
        total_count = len(results)
        
        print(f"Results: {passed_count}/{total_count} tests passed")
        print(f"\nDetails:")
        for name, passed, message in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status}: {name}")
            if not passed or verbose:
                print(f"         {message}")
        
        print(f"\n{'='*80}")
        if passed_count == total_count:
            print("✓ ALL TESTS PASSED")
        else:
            print(f"✗ {total_count - passed_count} TEST(S) FAILED")
        print(f"{'='*80}\n")
        
        return (passed_count, total_count)
        
    finally:
        # Cleanup
        if log_file.exists():
            log_file.unlink()


def main():
    """Main entry point"""
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    passed, total = run_all_tests(verbose)
    
    # Exit with appropriate code
    if passed == total:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
