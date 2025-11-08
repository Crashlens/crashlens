"""
End-to-End Parity Tests for CrashLens Unified Engine

Validates that policy-check and guard --use-unified-engine produce
identical results on canonical datasets across all policy templates.

Pass Criteria:
- Parity within ±1% violation counts
- Identical severity buckets for all templates
- If parity fails, abort merge and provide diff diagnostics
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest


@dataclass
class PolicyResult:
    """Stores policy check results"""
    command: str
    violations_found: int
    rules_checked: int
    severity_buckets: Dict[str, int]
    rule_details: Dict[str, Dict]
    exit_code: int
    raw_output: str


class ParityTester:
    """End-to-end parity testing framework"""
    
    # Parity threshold: ±1% violation counts
    PARITY_THRESHOLD_PERCENT = 1.0
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.policies_dir = project_root / "policies"
        self.sample_logs = project_root / "sample-logs" / "demo-logs.jsonl"
        
    def run_policy_check(self, policy_file: Path) -> PolicyResult:
        """Run policy-check command and parse results"""
        cmd = [
            "poetry", "run", "crashlens", "policy-check",
            str(self.sample_logs),
            "--rules", str(policy_file),
            "--output", "json"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        # Parse JSON output
        try:
            output_json = json.loads(result.stdout)
            summary = output_json.get("summary", {})
            rules = output_json.get("rules", {})
            
            # Extract severity buckets
            severity_buckets = {}
            for rule_id, rule_data in rules.items():
                severity = rule_data.get("severity", "unknown")
                count = rule_data.get("count", 0)
                severity_buckets[severity] = severity_buckets.get(severity, 0) + count
            
            return PolicyResult(
                command=" ".join(cmd),
                violations_found=summary.get("violations", 0),
                rules_checked=summary.get("total_rules", 0),
                severity_buckets=severity_buckets,
                rule_details=rules,
                exit_code=result.returncode,
                raw_output=result.stdout
            )
        except json.JSONDecodeError:
            # Fallback: parse text output
            violations = 0
            if "Violations Found:" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "Violations Found:" in line:
                        violations = int(line.split(":")[-1].strip())
            
            return PolicyResult(
                command=" ".join(cmd),
                violations_found=violations,
                rules_checked=0,
                severity_buckets={},
                rule_details={},
                exit_code=result.returncode,
                raw_output=result.stdout
            )
    
    def run_guard_unified(self, policy_file: Path) -> PolicyResult:
        """Run guard --use-unified-engine command and parse results"""
        cmd = [
            "poetry", "run", "crashlens", "guard",
            str(self.sample_logs),
            "--rules", str(policy_file),
            "--output", "json"
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=self.project_root
        )
        
        # Parse JSON output (same as policy-check)
        try:
            output_json = json.loads(result.stdout)
            summary = output_json.get("summary", {})
            rules = output_json.get("rules", {})
            
            severity_buckets = {}
            for rule_id, rule_data in rules.items():
                severity = rule_data.get("severity", "unknown")
                count = rule_data.get("count", 0)
                severity_buckets[severity] = severity_buckets.get(severity, 0) + count
            
            return PolicyResult(
                command=" ".join(cmd),
                violations_found=summary.get("violations", 0),
                rules_checked=summary.get("total_rules", 0),
                severity_buckets=severity_buckets,
                rule_details=rules,
                exit_code=result.returncode,
                raw_output=result.stdout
            )
        except json.JSONDecodeError:
            violations = 0
            if "Violations Found:" in result.stdout:
                for line in result.stdout.split("\n"):
                    if "Violations Found:" in line:
                        violations = int(line.split(":")[-1].strip())
            
            return PolicyResult(
                command=" ".join(cmd),
                violations_found=violations,
                rules_checked=0,
                severity_buckets={},
                rule_details={},
                exit_code=result.returncode,
                raw_output=result.stdout
            )
    
    def compare_results(
        self, 
        policy_check_result: PolicyResult, 
        guard_result: PolicyResult,
        policy_name: str
    ) -> Tuple[bool, List[str]]:
        """Compare two results and check for parity"""
        issues = []
        
        # 1. Check violation counts (±1%)
        pc_violations = policy_check_result.violations_found
        guard_violations = guard_result.violations_found
        
        if pc_violations > 0:
            diff_percent = abs(pc_violations - guard_violations) / pc_violations * 100
        else:
            diff_percent = 0 if guard_violations == 0 else 100
        
        if diff_percent > self.PARITY_THRESHOLD_PERCENT:
            issues.append(
                f"Violation count mismatch: policy-check={pc_violations}, "
                f"guard={guard_violations} ({diff_percent:.1f}% difference, "
                f"threshold={self.PARITY_THRESHOLD_PERCENT}%)"
            )
        
        # 2. Check severity buckets (must be identical)
        if policy_check_result.severity_buckets != guard_result.severity_buckets:
            issues.append(
                f"Severity bucket mismatch:\n"
                f"  policy-check: {policy_check_result.severity_buckets}\n"
                f"  guard:        {guard_result.severity_buckets}"
            )
        
        # 3. Check exit codes
        if policy_check_result.exit_code != guard_result.exit_code:
            issues.append(
                f"Exit code mismatch: policy-check={policy_check_result.exit_code}, "
                f"guard={guard_result.exit_code}"
            )
        
        return len(issues) == 0, issues
    
    def generate_diff_diagnostics(
        self,
        policy_check_result: PolicyResult,
        guard_result: PolicyResult,
        policy_name: str
    ) -> str:
        """Generate detailed diff diagnostics for parity failures"""
        diagnostics = [
            "="*80,
            f"PARITY FAILURE DIAGNOSTICS: {policy_name}",
            "="*80,
            "",
            "Policy-Check Results:",
            f"  Command:        {policy_check_result.command}",
            f"  Exit Code:      {policy_check_result.exit_code}",
            f"  Violations:     {policy_check_result.violations_found}",
            f"  Rules Checked:  {policy_check_result.rules_checked}",
            f"  Severity Buckets: {policy_check_result.severity_buckets}",
            "",
            "Guard (Unified) Results:",
            f"  Command:        {guard_result.command}",
            f"  Exit Code:      {guard_result.exit_code}",
            f"  Violations:     {guard_result.violations_found}",
            f"  Rules Checked:  {guard_result.rules_checked}",
            f"  Severity Buckets: {guard_result.severity_buckets}",
            "",
            "Rule-by-Rule Comparison:",
        ]
        
        # Compare rule details
        all_rules = set(policy_check_result.rule_details.keys()) | set(guard_result.rule_details.keys())
        for rule_id in sorted(all_rules):
            pc_rule = policy_check_result.rule_details.get(rule_id, {})
            guard_rule = guard_result.rule_details.get(rule_id, {})
            
            pc_count = pc_rule.get("count", 0)
            guard_count = guard_rule.get("count", 0)
            
            if pc_count != guard_count:
                diagnostics.append(
                    f"  {rule_id}:"
                    f" policy-check={pc_count}, guard={guard_count}"
                    f" (diff={guard_count - pc_count})"
                )
        
        diagnostics.extend([
            "",
            "Raw Outputs:",
            "",
            "Policy-Check Output:",
            "-"*80,
            policy_check_result.raw_output[:500],
            "",
            "Guard Output:",
            "-"*80,
            guard_result.raw_output[:500],
            "",
            "="*80,
        ])
        
        return "\n".join(diagnostics)


class TestParityEndToEnd:
    """End-to-end parity test suite"""
    
    @pytest.fixture
    def tester(self):
        """Create parity tester instance"""
        project_root = Path(__file__).parent.parent.parent
        return ParityTester(project_root)
    
    @pytest.fixture
    def policy_templates(self, tester):
        """Get list of policy templates to test"""
        templates = []
        policies_dir = tester.policies_dir
        
        # Find all .yaml files in policies directory
        if policies_dir.exists():
            for policy_file in policies_dir.glob("*.yaml"):
                if policy_file.stem not in ["README", "langfuse"]:  # Skip non-policy files
                    templates.append(policy_file)
        
        # If no policies found, use default
        if not templates:
            default_policy = tester.project_root / ".crashlens" / "rules.yaml"
            if default_policy.exists():
                templates.append(default_policy)
        
        return templates
    
    def test_parity_for_all_templates(self, tester, policy_templates):
        """Test parity for all policy templates"""
        if not policy_templates:
            pytest.skip("No policy templates found")
        
        failures = []
        
        for policy_file in policy_templates:
            policy_name = policy_file.stem
            
            print(f"\n{'='*60}")
            print(f"Testing: {policy_name}")
            print(f"{'='*60}")
            
            # Run policy-check
            print("Running policy-check...")
            pc_result = tester.run_policy_check(policy_file)
            
            # Run guard with unified engine
            print("Running guard --use-unified-engine...")
            guard_result = tester.run_guard_unified(policy_file)
            
            # Compare results
            is_parity, issues = tester.compare_results(pc_result, guard_result, policy_name)
            
            if is_parity:
                print(f"✅ PASS: Parity achieved for {policy_name}")
            else:
                print(f"❌ FAIL: Parity check failed for {policy_name}")
                for issue in issues:
                    print(f"  - {issue}")
                
                # Generate diagnostics
                diagnostics = tester.generate_diff_diagnostics(pc_result, guard_result, policy_name)
                failures.append((policy_name, issues, diagnostics))
        
        # Report failures
        if failures:
            print("\n" + "="*80)
            print("PARITY TEST FAILURES")
            print("="*80)
            
            for policy_name, issues, diagnostics in failures:
                print(f"\n{policy_name}:")
                for issue in issues:
                    print(f"  - {issue}")
                print("\nDiagnostics:")
                print(diagnostics)
            
            pytest.fail(
                f"Parity tests failed for {len(failures)} template(s): "
                f"{', '.join(f[0] for f in failures)}"
            )
    
    def test_retry_loop_detector_parity(self, tester):
        """Specific test for retry-loop-detector policy"""
        policy_file = tester.policies_dir / "retry-loop-detector.yaml"
        
        if not policy_file.exists():
            pytest.skip("retry-loop-detector.yaml not found")
        
        pc_result = tester.run_policy_check(policy_file)
        guard_result = tester.run_guard_unified(policy_file)
        
        is_parity, issues = tester.compare_results(pc_result, guard_result, "retry-loop-detector")
        
        if not is_parity:
            diagnostics = tester.generate_diff_diagnostics(pc_result, guard_result, "retry-loop-detector")
            pytest.fail(f"Parity check failed:\n" + "\n".join(issues) + "\n\n" + diagnostics)
    
    def test_fallback_chain_detector_parity(self, tester):
        """Specific test for fallback-chain-detector policy"""
        policy_file = tester.policies_dir / "fallback-chain-detector.yaml"
        
        if not policy_file.exists():
            pytest.skip("fallback-chain-detector.yaml not found")
        
        pc_result = tester.run_policy_check(policy_file)
        guard_result = tester.run_guard_unified(policy_file)
        
        is_parity, issues = tester.compare_results(pc_result, guard_result, "fallback-chain-detector")
        
        if not is_parity:
            diagnostics = tester.generate_diff_diagnostics(pc_result, guard_result, "fallback-chain-detector")
            pytest.fail(f"Parity check failed:\n" + "\n".join(issues) + "\n\n" + diagnostics)
    
    def test_max_cost_per_trace_parity(self, tester):
        """Specific test for max-cost-per-trace policy"""
        policy_file = tester.policies_dir / "max-cost-per-trace.yaml"
        
        if not policy_file.exists():
            pytest.skip("max-cost-per-trace.yaml not found")
        
        pc_result = tester.run_policy_check(policy_file)
        guard_result = tester.run_guard_unified(policy_file)
        
        is_parity, issues = tester.compare_results(pc_result, guard_result, "max-cost-per-trace")
        
        if not is_parity:
            diagnostics = tester.generate_diff_diagnostics(pc_result, guard_result, "max-cost-per-trace")
            pytest.fail(f"Parity check failed:\n" + "\n".join(issues) + "\n\n" + diagnostics)


# Standalone test runner for CI
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent.parent
    tester = ParityTester(project_root)
    
    print("CrashLens End-to-End Parity Tests")
    print("="*80)
    
    # Find all policy templates
    templates = []
    if tester.policies_dir.exists():
        templates = list(tester.policies_dir.glob("*.yaml"))
    
    if not templates:
        print("No policy templates found")
        sys.exit(1)
    
    failures = []
    for policy_file in templates:
        if policy_file.stem in ["README", "langfuse"]:
            continue
        
        policy_name = policy_file.stem
        print(f"\nTesting: {policy_name}")
        
        pc_result = tester.run_policy_check(policy_file)
        guard_result = tester.run_guard_unified(policy_file)
        
        is_parity, issues = tester.compare_results(pc_result, guard_result, policy_name)
        
        if is_parity:
            print(f"✅ PASS")
        else:
            print(f"❌ FAIL")
            for issue in issues:
                print(f"  - {issue}")
            failures.append((policy_name, issues))
    
    if failures:
        print("\n" + "="*80)
        print("FAILURES")
        print("="*80)
        for policy_name, issues in failures:
            print(f"\n{policy_name}:")
            for issue in issues:
                print(f"  - {issue}")
        sys.exit(1)
    else:
        print("\n" + "="*80)
        print("✅ ALL PARITY TESTS PASSED")
        print("="*80)
        sys.exit(0)
