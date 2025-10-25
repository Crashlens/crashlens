"""
Tests for --dry-run and --summary-only CLI flags in guard command
"""

import json
from click.testing import CliRunner
from crashlens.guard import guard


class TestDryRunFlag:
    """Test --dry-run flag functionality"""
    
    def test_dry_run_prevents_exit_code_1(self):
        """Dry-run mode returns exit code 0 even when violations exist"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs with violations
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({
                    "model": "gpt-4o",
                    "tokens": 3000,
                    "cost_usd": 0.60,
                    "retry_count": 0,
                    "fallback_triggered": False
                }) + "\n")
            
            # Create rules that will trigger violations
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""")
            
            # Without dry-run, should fail
            result_normal = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--fail-on-violations"
            ])
            assert result_normal.exit_code == 1
            assert "❌ Guard: Failing due to policy violations" in result_normal.output
            
            # With dry-run, should succeed
            result_dry_run = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--fail-on-violations",
                "--dry-run"
            ])
            assert result_dry_run.exit_code == 0
            assert "🔍 Guard (dry-run): Violations found but not failing CI" in result_dry_run.output
    
    def test_dry_run_still_prints_report(self):
        """Dry-run mode still outputs full report"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs with violations
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({
                    "model": "gpt-4o",
                    "tokens": 3000,
                    "cost_usd": 0.10
                }) + "\n")
            
            # Create rules
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "High token usage"
    if:
      if_tokens_gt: 2000
    action: error
    severity: error
""")
            
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--dry-run"
            ])
            
            assert result.exit_code == 0
            assert "TEST001" in result.output
            assert "High token usage" in result.output
            assert "Violation Count: 1" in result.output
    
    def test_dry_run_without_violations_exit_0(self):
        """Dry-run with no violations exits 0 (same as normal)"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs WITHOUT violations
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({
                    "model": "gpt-3.5-turbo",
                    "tokens": 500,
                    "cost_usd": 0.01
                }) + "\n")
            
            # Create rules that won't trigger
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "High token usage"
    if:
      if_tokens_gt: 5000
    action: error
    severity: error
""")
            
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--dry-run"
            ])
            
            assert result.exit_code == 0
            assert "✅ Guard: No violations detected" in result.output


class TestSummaryOnlyFlag:
    """Test --summary-only flag functionality"""
    
    def test_summary_only_condensed_output(self):
        """Summary-only mode outputs condensed one-line-per-rule format"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs with multiple violations
            with open("test.jsonl", "w") as f:
                # Two violations for TEST001
                f.write(json.dumps({"model": "gpt-4o", "tokens": 3000}) + "\n")
                f.write(json.dumps({"model": "gpt-4o", "tokens": 4000}) + "\n")
                # One violation for TEST002
                f.write(json.dumps({"retry_count": 5}) + "\n")
                # No violation for TEST003
                f.write(json.dumps({"model": "gpt-3.5-turbo", "tokens": 500}) + "\n")
            
            # Create multiple rules
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "High tokens"
    if:
      if_tokens_gt: 2000
    action: error
    severity: error
  
  - id: TEST002
    description: "Excessive retries"
    if:
      if_retry_count_gt: 3
    action: warn
    severity: warn
  
  - id: TEST003
    description: "Expensive model"
    if:
      if_model: "claude-3"
    action: warn
    severity: warn
""")
            
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--summary-only"
            ])
            
            assert result.exit_code == 0
            
            # Check header
            assert "Rule ID | Violations | Severity" in result.output
            assert "-" * 40 in result.output
            
            # Check violations present
            assert "TEST001" in result.output
            assert "2" in result.output  # 2 violations
            assert "TEST002" in result.output
            assert "1" in result.output  # 1 violation
            
            # TEST003 should NOT appear (no violations)
            # Note: "TEST003" might appear in other output, so check full line format
            lines = result.output.split("\n")
            rule_lines = [l for l in lines if "TEST" in l and "|" in l]
            assert len(rule_lines) == 2  # Only TEST001 and TEST002
    
    def test_summary_only_with_no_violations(self):
        """Summary-only with no violations shows empty summary"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs without violations
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({"model": "gpt-3.5-turbo", "tokens": 500}) + "\n")
            
            # Create rule that won't trigger
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "High tokens"
    if:
      if_tokens_gt: 5000
    action: error
    severity: error
""")
            
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--summary-only"
            ])
            
            assert result.exit_code == 0
            assert "Rule ID | Violations | Severity" in result.output
            # TEST001 should not appear (no violations)
            lines = result.output.split("\n")
            rule_lines = [l for l in lines if "TEST001" in l and "|" in l]
            assert len(rule_lines) == 0
    
    def test_summary_only_overrides_output_format(self):
        """Summary-only takes precedence over other output formats"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs with violations
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({"model": "gpt-4o", "tokens": 3000}) + "\n")
            
            # Create rule
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "High tokens"
    if:
      if_tokens_gt: 2000
    action: error
    severity: error
""")
            
            # Try with --output json (summary-only should override)
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--output", "json",
                "--summary-only"
            ])
            
            assert result.exit_code == 0
            # Should be summary format, NOT JSON
            assert "Rule ID | Violations | Severity" in result.output
            assert "{" not in result.output  # No JSON braces


class TestCombinedFlags:
    """Test combinations of --dry-run and --summary-only"""
    
    def test_dry_run_and_summary_only_together(self):
        """Both flags work together correctly"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs with violations
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({"model": "gpt-4o", "tokens": 3000}) + "\n")
            
            # Create rule that should fail CI
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "High tokens"
    if:
      if_tokens_gt: 2000
    action: fail_ci
    severity: fatal
""")
            
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--fail-on-violations",
                "--dry-run",
                "--summary-only"
            ])
            
            # Should exit 0 (dry-run)
            assert result.exit_code == 0
            
            # Should show summary format
            assert "Rule ID | Violations | Severity" in result.output
            assert "TEST001" in result.output
            
            # Should show dry-run message
            assert "🔍 Guard (dry-run): Violations found but not failing CI" in result.output
    
    def test_dry_run_respects_severity_threshold(self):
        """Dry-run mode still respects --severity for reporting"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # Create logs with warn-level violation
            with open("test.jsonl", "w") as f:
                f.write(json.dumps({"model": "gpt-4o", "tokens": 1500}) + "\n")
            
            # Create warn-level rule
            with open("rules.yaml", "w") as f:
                f.write("""
rules:
  - id: TEST001
    description: "Medium tokens"
    if:
      if_tokens_gt: 1000
    action: warn
    severity: warn
""")
            
            # With --severity error, warn violations shouldn't block
            result = runner.invoke(guard, [
                "test.jsonl",
                "--rules", "rules.yaml",
                "--fail-on-violations",
                "--severity", "error",
                "--dry-run"
            ])
            
            assert result.exit_code == 0
            # Dry-run message should still appear if violations found
            assert "🔍 Guard (dry-run): Violations found but not failing CI" in result.output


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
