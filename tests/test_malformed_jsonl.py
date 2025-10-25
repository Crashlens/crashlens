"""
Tests for fail-safe JSONL parsing in guard command.

Verifies that:
1. Malformed JSON lines are skipped (not fatal)
2. Warnings are printed to stderr with line numbers
3. Valid lines are still processed
4. skipped_lines count is included in report
5. Parser continues after encountering bad lines
"""

import json
from pathlib import Path
from click.testing import CliRunner
import pytest

from crashlens.cli import cli


class TestMalformedJSONL:
    """Test guard's fail-safe JSONL parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        # Create minimal rules file
        self.rules_content = """
rules:
  - id: test_rule
    description: "Test rule"
    if:
      model: "gpt-4"
    action: warn
    severity: warn
"""

    def test_skip_malformed_line_and_continue(self):
        """Verify parser skips malformed line and processes valid lines."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with one malformed line
            log_file = Path("test.jsonl")
            log_content = """{"model": "gpt-4", "tokens": 100}
{this is not valid JSON}
{"model": "gpt-3.5-turbo", "tokens": 50}
"""
            log_file.write_text(log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            # Should succeed (doesn't abort on bad line)
            assert result.exit_code == 0, f"Guard failed: {result.output}"
            
            # Should have warning in stderr
            assert "⚠️" in result.output or "Warning" in result.output
            assert "Skipping malformed JSON" in result.output
            assert "line 2" in result.output  # Line number of bad line
            
            # Should have skipped lines summary
            assert "Skipped 1 malformed line" in result.output

    def test_report_contains_skipped_lines_count(self):
        """Verify JSON report includes skipped_lines count."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with multiple malformed lines
            log_file = Path("test.jsonl")
            log_content = """{"model": "gpt-4", "tokens": 100}
{bad line 1}
{"model": "gpt-3.5-turbo", "tokens": 50}
not valid json either
{"model": "gpt-4", "tokens": 200}
"""
            log_file.write_text(log_content)
            
            # Run guard with JSON output
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            assert result.exit_code == 0
            
            # Find and parse artifact
            artifact_files = list(Path(".").glob("guard-*.json"))
            assert len(artifact_files) == 1
            
            with open(artifact_files[0], "r") as f:
                report = json.load(f)
            
            # Verify skipped_lines in report
            assert "summary" in report
            assert "skipped_lines" in report["summary"]
            assert report["summary"]["skipped_lines"] == 2

    def test_all_valid_lines_no_skipped(self):
        """Verify skipped_lines is 0 when all lines are valid."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with all valid lines
            log_file = Path("test.jsonl")
            log_content = """{"model": "gpt-4", "tokens": 100}
{"model": "gpt-3.5-turbo", "tokens": 50}
{"model": "gpt-4", "tokens": 200}
"""
            log_file.write_text(log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            assert result.exit_code == 0
            
            # Should NOT have skipped lines summary (only shown if > 0)
            assert "Skipped" not in result.output or "Skipped 0" not in result.output
            
            # Check artifact
            artifact_files = list(Path(".").glob("guard-*.json"))
            with open(artifact_files[0], "r") as f:
                report = json.load(f)
            
            assert report["summary"]["skipped_lines"] == 0

    def test_valid_lines_processed_correctly_despite_bad_lines(self):
        """Verify valid lines are evaluated against rules despite malformed lines."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with malformed lines interspersed
            log_file = Path("test.jsonl")
            log_content = """{"model": "gpt-4", "tokens": 100}
{bad line}
{"model": "gpt-4", "tokens": 200}
"""
            log_file.write_text(log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            assert result.exit_code == 0
            
            # Check artifact to verify rule matched valid gpt-4 lines
            artifact_files = list(Path(".").glob("guard-*.json"))
            with open(artifact_files[0], "r") as f:
                report = json.load(f)
            
            # Should have 2 violations (2 gpt-4 lines, 1 bad line skipped)
            assert report["rules"]["test_rule"]["count"] == 2
            assert report["summary"]["skipped_lines"] == 1

    def test_malformed_line_warning_shows_content_snippet(self):
        """Verify warning includes content snippet of malformed line."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with identifiable malformed line
            log_file = Path("test.jsonl")
            log_content = """{"model": "gpt-4", "tokens": 100}
{this_is_the_bad_line: "test"}
{"model": "gpt-3.5-turbo", "tokens": 50}
"""
            log_file.write_text(log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ])
            
            assert result.exit_code == 0
            
            # Should show content snippet
            assert "Content:" in result.output
            assert "this_is_the_bad_line" in result.output

    def test_empty_lines_are_skipped_silently(self):
        """Verify empty lines don't trigger warnings or count as skipped."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with empty lines (should be ignored)
            log_file = Path("test.jsonl")
            log_content = """{"model": "gpt-4", "tokens": 100}

{"model": "gpt-3.5-turbo", "tokens": 50}

"""
            log_file.write_text(log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            assert result.exit_code == 0
            
            # Empty lines should NOT count as skipped
            artifact_files = list(Path(".").glob("guard-*.json"))
            with open(artifact_files[0], "r") as f:
                report = json.load(f)
            
            assert report["summary"]["skipped_lines"] == 0

    def test_long_malformed_line_truncated_in_warning(self):
        """Verify very long malformed lines are truncated in warning output."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with very long malformed line
            long_bad_line = "{" + "x" * 200 + "}"
            log_file = Path("test.jsonl")
            # Use regular string formatting to avoid f-string brace escaping issues
            log_content = '{"model": "gpt-4", "tokens": 100}\n' + long_bad_line + '\n{"model": "gpt-3.5-turbo", "tokens": 50}\n'
            log_file.write_text(log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ])
            
            assert result.exit_code == 0
            
            # Should truncate long line (show max 80 chars + "...")
            assert "..." in result.output
            # Should not print entire 200+ character line
            lines_in_output = result.output.split("\n")
            for line in lines_in_output:
                # No single line should be excessively long (>200 chars)
                assert len(line) < 200, f"Output line too long: {line[:100]}..."


class TestMalformedJSONLEdgeCases:
    """Edge case tests for malformed JSONL handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        
        self.rules_content = """
rules:
  - id: test_rule
    description: "Test"
    if:
      model: "gpt-4"
    action: warn
    severity: warn
"""

    def test_all_lines_malformed(self):
        """Verify guard handles file with all malformed lines gracefully."""
        with self.runner.isolated_filesystem():
            # Create rules file
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            # Create JSONL with all bad lines
            log_file = Path("test.jsonl")
            log_content = """{bad line 1}
not valid json
[wrong, format]
"""
            log_file.write_text(log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--output", "json"
            ])
            
            # Should still succeed (no valid lines to violate rules)
            assert result.exit_code == 0
            
            # Should report 3 skipped lines
            assert "Skipped 3 malformed line" in result.output
            
            # Check artifact
            artifact_files = list(Path(".").glob("guard-*.json"))
            with open(artifact_files[0], "r") as f:
                report = json.load(f)
            
            assert report["summary"]["skipped_lines"] == 3
            assert report["summary"]["violations"] == 0

    def test_malformed_line_doesnt_prevent_violations(self):
        """Verify malformed lines don't prevent detection of violations."""
        with self.runner.isolated_filesystem():
            # Create rules with fatal severity
            fatal_rules = """
rules:
  - id: fatal_rule
    description: "Fatal rule"
    if:
      model: "gpt-4"
    action: fail_ci
    severity: fatal
"""
            rules_file = Path("rules.yaml")
            rules_file.write_text(fatal_rules)
            
            # Create JSONL with malformed line and violation
            log_file = Path("test.jsonl")
            log_content = """{bad line}
{"model": "gpt-4", "tokens": 100}
"""
            log_file.write_text(log_content)
            
            # Run guard with fail-on-violations
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--fail-on-violations",
                "--severity", "fatal"
            ])
            
            # Should fail (fatal violation)
            assert result.exit_code == 1
            
            # But should still skip malformed line
            assert "Skipped 1 malformed line" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
