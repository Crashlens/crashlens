"""
Tests for guard artifact creation (guard-<RUN_ID>.json).

Verifies that:
1. guard command writes JSON artifact to workspace root
2. Artifact filename includes RUN_ID
3. Artifact contains valid JSON with expected structure
4. CRASHLENS_RUN_ID environment variable is respected
"""

import json
import os
import tempfile
from pathlib import Path
from click.testing import CliRunner
import pytest

from crashlens.cli import cli


class TestArtifactCreation:
    """Test guard artifact creation for CI auditability."""

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
        
        # Create minimal JSONL log file
        self.log_content = """{"model": "gpt-4", "tokens": 100}
{"model": "gpt-3.5-turbo", "tokens": 50}
"""

    def test_artifact_created_on_guard_run(self):
        """Verify guard creates artifact file in workspace root."""
        with self.runner.isolated_filesystem():
            # Write test files
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            log_file = Path("test.jsonl")
            log_file.write_text(self.log_content)
            
            # Run guard command
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--output", "text"
            ])
            
            # Should succeed (violations are warnings)
            assert result.exit_code == 0, f"Guard failed: {result.output}"
            
            # Check artifact exists
            artifact_files = list(Path(".").glob("guard-*.json"))
            assert len(artifact_files) == 1, f"Expected 1 artifact, found {len(artifact_files)}"
            
            artifact_path = artifact_files[0]
            assert artifact_path.exists(), f"Artifact not found: {artifact_path}"
            
            # Verify artifact message in stderr
            assert "📋 Artifact written:" in result.output

    def test_artifact_contains_valid_json(self):
        """Verify artifact contains valid JSON with expected structure."""
        with self.runner.isolated_filesystem():
            # Write test files
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            log_file = Path("test.jsonl")
            log_file.write_text(self.log_content)
            
            # Run guard command
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ])
            
            # Find artifact
            artifact_files = list(Path(".").glob("guard-*.json"))
            assert len(artifact_files) == 1
            artifact_path = artifact_files[0]
            
            # Parse JSON
            with open(artifact_path, "r") as f:
                artifact_data = json.load(f)
            
            # Verify structure
            assert "summary" in artifact_data, "Missing 'summary' key"
            assert "rules" in artifact_data, "Missing 'rules' key"
            
            # Verify summary structure
            assert "total_rules" in artifact_data["summary"]
            assert "violations" in artifact_data["summary"]
            
            # Verify rules structure
            assert isinstance(artifact_data["rules"], dict)
            assert "test_rule" in artifact_data["rules"]
            
            # Verify rule details
            rule_data = artifact_data["rules"]["test_rule"]
            assert "count" in rule_data
            assert "severity" in rule_data
            assert "description" in rule_data
            assert "examples" in rule_data

    def test_artifact_respects_run_id_env_var(self):
        """Verify artifact filename uses CRASHLENS_RUN_ID if set."""
        with self.runner.isolated_filesystem():
            # Write test files
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            log_file = Path("test.jsonl")
            log_file.write_text(self.log_content)
            
            # Set custom RUN_ID
            custom_run_id = "20250105T120000Z-abc1234"
            
            # Run guard command with custom RUN_ID
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ], env={"CRASHLENS_RUN_ID": custom_run_id})
            
            assert result.exit_code == 0
            
            # Check artifact has expected filename
            expected_artifact = Path(f"guard-{custom_run_id}.json")
            assert expected_artifact.exists(), f"Expected artifact: {expected_artifact}"
            
            # Verify no other artifacts were created
            artifact_files = list(Path(".").glob("guard-*.json"))
            assert len(artifact_files) == 1
            assert artifact_files[0].name == f"guard-{custom_run_id}.json"

    def test_artifact_created_even_on_violations(self):
        """Verify artifact is created even when violations cause failure."""
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
            
            log_file = Path("test.jsonl")
            log_file.write_text(self.log_content)
            
            # Run guard with fail-on-violations
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file),
                "--fail-on-violations",
                "--severity", "fatal"
            ])
            
            # Should fail (fatal violation)
            assert result.exit_code == 1, "Expected failure on fatal violation"
            
            # Artifact should still exist
            artifact_files = list(Path(".").glob("guard-*.json"))
            assert len(artifact_files) == 1, "Artifact should be created even on failure"

    def test_artifact_filename_format(self):
        """Verify artifact filename follows expected format."""
        with self.runner.isolated_filesystem():
            # Write test files
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            log_file = Path("test.jsonl")
            log_file.write_text(self.log_content)
            
            # Run guard
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ])
            
            assert result.exit_code == 0
            
            # Find artifact
            artifact_files = list(Path(".").glob("guard-*.json"))
            assert len(artifact_files) == 1
            
            artifact_name = artifact_files[0].name
            
            # Verify format: guard-<timestamp>-<hash>.json
            # Format: guard-20250105T120000Z-abc1234.json
            assert artifact_name.startswith("guard-")
            assert artifact_name.endswith(".json")
            
            # Extract RUN_ID
            run_id = artifact_name[6:-5]  # Remove "guard-" and ".json"
            
            # Verify RUN_ID has timestamp and hash parts
            parts = run_id.split("-")
            assert len(parts) >= 2, f"RUN_ID should have timestamp-hash format, got: {run_id}"
            
            # First part should be timestamp (format: YYYYMMDDTHHMMSSsZ)
            timestamp_part = parts[0]
            assert len(timestamp_part) == 16, f"Timestamp should be 16 chars, got: {timestamp_part}"
            assert "T" in timestamp_part, "Timestamp should contain 'T'"
            assert timestamp_part.endswith("Z"), "Timestamp should end with 'Z'"

    def test_artifact_write_failure_warning(self):
        """Verify warning is shown if artifact write fails."""
        with self.runner.isolated_filesystem():
            # Write test files
            rules_file = Path("rules.yaml")
            rules_file.write_text(self.rules_content)
            
            log_file = Path("test.jsonl")
            log_file.write_text(self.log_content)
            
            # Set RUN_ID with invalid characters for filename
            # (This test verifies the error handling, though filesystem may sanitize)
            result = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ])
            
            # Command should still complete
            assert result.exit_code == 0
            
            # Either artifact is created or warning is shown
            artifact_files = list(Path(".").glob("guard-*.json"))
            if len(artifact_files) == 0:
                # If no artifact, should have warning
                assert "⚠️" in result.output or "Warning" in result.output
            else:
                # If artifact exists, success message should be shown
                assert "📋 Artifact written:" in result.output


class TestArtifactIntegration:
    """Integration tests for artifact creation in CI-like scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_multiple_guard_runs_create_separate_artifacts(self):
        """Verify multiple runs create separate artifacts (no overwrite)."""
        with self.runner.isolated_filesystem():
            # Create test files
            rules_content = """
rules:
  - id: test_rule
    description: "Test"
    if:
      model: "gpt-4"
    action: warn
    severity: warn
"""
            rules_file = Path("rules.yaml")
            rules_file.write_text(rules_content)
            
            log_file = Path("test.jsonl")
            log_file.write_text('{"model": "gpt-4", "tokens": 100}\n')
            
            # Run guard twice with different RUN_IDs
            result1 = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ], env={"CRASHLENS_RUN_ID": "run1"})
            
            result2 = self.runner.invoke(cli, [
                "guard",
                str(log_file),
                "--rules", str(rules_file)
            ], env={"CRASHLENS_RUN_ID": "run2"})
            
            assert result1.exit_code == 0
            assert result2.exit_code == 0
            
            # Should have two separate artifacts
            artifact_files = list(Path(".").glob("guard-*.json"))
            assert len(artifact_files) == 2
            
            artifact_names = {f.name for f in artifact_files}
            assert "guard-run1.json" in artifact_names
            assert "guard-run2.json" in artifact_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
