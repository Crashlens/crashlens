#!/usr/bin/env python3
"""
Unit tests for guard report path and annotation hook functionality (Step 2).
"""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from crashlens.guard import guard


@pytest.fixture
def sample_rules_yaml(tmp_path):
    """Create sample rules.yaml for testing."""
    rules_file = tmp_path / "rules.yaml"
    rules_content = """
rules:
  - id: RL_TEST_001
    description: "Test rule for excessive retries"
    if:
      retry_count: ">= 3"
    action: fail_ci
    severity: error
"""
    rules_file.write_text(rules_content)
    return rules_file


@pytest.fixture
def sample_logs_jsonl(tmp_path):
    """Create sample JSONL logs for testing."""
    logs_file = tmp_path / "logs.jsonl"
    logs_content = """{"traceId": "trace1", "model": "gpt-4", "retry_count": 5, "prompt_tokens": 100, "completion_tokens": 50}
{"traceId": "trace2", "model": "gpt-3.5-turbo", "retry_count": 1, "prompt_tokens": 200, "completion_tokens": 75}
"""
    logs_file.write_text(logs_content)
    return logs_file


@pytest.fixture
def clean_logs_jsonl(tmp_path):
    """Create clean JSONL logs with no violations."""
    logs_file = tmp_path / "clean_logs.jsonl"
    logs_content = """{"traceId": "trace1", "model": "gpt-4", "retry_count": 1, "prompt_tokens": 100, "completion_tokens": 50}
{"traceId": "trace2", "model": "gpt-3.5-turbo", "retry_count": 0, "prompt_tokens": 200, "completion_tokens": 75}
"""
    logs_file.write_text(logs_content)
    return logs_file


class TestReportPath:
    """Test --report-path functionality."""
    
    def test_report_path_default(self, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Report written to default path (crashlens-report.json)."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml)
            ])
            
            # Check report file was created
            assert Path('crashlens-report.json').exists()
            
            # Verify report structure
            with open('crashlens-report.json', 'r') as f:
                report = json.load(f)
            
            assert 'summary' in report
            assert 'rules' in report
            assert report['summary']['violations'] == 1  # RL_TEST_001 triggered
    
    def test_report_path_custom(self, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Report written to custom path."""
        runner = CliRunner()
        custom_path = tmp_path / "custom-report.json"
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--report-path', str(custom_path)
            ])
            
            # Check custom report file was created
            assert custom_path.exists()
            
            # Verify content
            with open(custom_path, 'r') as f:
                report = json.load(f)
            
            assert report['summary']['violations'] == 1
    
    def test_report_path_subdirectory(self, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Report written to subdirectory (auto-created)."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            subdir = Path('reports')
            subdir.mkdir()
            report_path = subdir / 'guard-report.json'
            
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--report-path', str(report_path)
            ])
            
            assert report_path.exists()
    
    def test_report_path_write_error(self, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Handle write errors gracefully."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Use invalid path (directory as file)
            invalid_path = Path('invalid')
            invalid_path.mkdir()
            
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--report-path', str(invalid_path)  # Directory, not file
            ])
            
            # Should warn but not crash
            assert '⚠️  Warning: Could not write report' in result.output


class TestAnnotationHook:
    """Test --annotation-hook functionality."""
    
    @patch('crashlens.guard.subprocess.run')
    def test_annotation_hook_basic(self, mock_run, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Annotation hook is called with report path."""
        mock_run.return_value = MagicMock(returncode=0, stdout='Hook output', stderr='')
        
        runner = CliRunner()
        report_path = tmp_path / 'report.json'
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--report-path', str(report_path),
                '--annotation-hook', f'echo "Processing {report_path}"'
            ])
            
            # Verify subprocess.run was called
            assert mock_run.call_count == 1
            
            # Check command includes report path
            call_args = mock_run.call_args
            assert str(report_path) in call_args.args[0]
            
            # Verify output shows hook execution
            assert '🔗 Running annotation hook' in result.output
            assert '✅ Annotation hook completed successfully' in result.output
    
    @patch('crashlens.guard.subprocess.run')
    def test_annotation_hook_placeholder_substitution(self, mock_run, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Annotation hook substitutes {report_path} placeholder."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        
        runner = CliRunner()
        report_path = tmp_path / 'report.json'
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--report-path', str(report_path),
                '--annotation-hook', 'python script.py {report_path}'
            ])
            
            # Verify {report_path} was replaced
            call_args = mock_run.call_args
            assert '{report_path}' not in call_args.args[0]
            assert str(report_path) in call_args.args[0]
    
    @patch('crashlens.guard.subprocess.run')
    def test_annotation_hook_failure(self, mock_run, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Annotation hook failure is handled gracefully."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout='',
            stderr='Hook error message'
        )
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--annotation-hook', 'exit 1'
            ])
            
            # Should warn but not crash
            assert '⚠️  Annotation hook failed' in result.output
            # Guard should still complete normally
            assert result.exit_code in [0, 1]  # Depends on fail_on_violations
    
    @patch('crashlens.guard.subprocess.run')
    def test_annotation_hook_timeout(self, mock_run, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Annotation hook timeout is handled."""
        mock_run.side_effect = subprocess.TimeoutExpired('cmd', 60)
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--annotation-hook', 'sleep 120'
            ])
            
            # Should warn about timeout
            assert '⚠️  Annotation hook timed out' in result.output
    
    @patch('crashlens.guard.subprocess.run')
    def test_annotation_hook_without_violations(self, mock_run, tmp_path, sample_rules_yaml, clean_logs_jsonl):
        """Annotation hook runs even with no violations."""
        mock_run.return_value = MagicMock(returncode=0, stdout='', stderr='')
        
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(clean_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--annotation-hook', 'echo "Hook runs regardless"'
            ])
            
            # Hook should still be called
            assert mock_run.call_count == 1
            assert '🔗 Running annotation hook' in result.output


class TestDryRunEnhancements:
    """Test enhanced --dry-run behavior."""
    
    def test_dry_run_with_violations(self, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Dry-run mode prevents nonzero exit despite violations."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--fail-on-violations',
                '--dry-run'
            ])
            
            # Should not fail (exit code 0) despite violations
            assert result.exit_code == 0
            assert '🔍 Guard (dry-run): Issues found but not failing CI' in result.output
    
    def test_dry_run_with_cost_cap(self, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Dry-run mode prevents cost cap violations from failing."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--cost-cap', '0.0001',  # Very low cap, will exceed
                '--dry-run'
            ])
            
            # Should not fail despite cost cap
            assert result.exit_code == 0
            assert '🔍 Guard (dry-run)' in result.output
    
    def test_dry_run_without_violations(self, tmp_path, sample_rules_yaml, clean_logs_jsonl):
        """Dry-run mode with clean logs still exits 0."""
        runner = CliRunner()
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(clean_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--dry-run'
            ])
            
            assert result.exit_code == 0
            # Clean logs may still trigger rule, but dry-run ensures exit 0
            # Check for either success or dry-run message
            assert (
                '✅ Guard: No violations detected' in result.output or
                '🔍 Guard (dry-run)' in result.output
            )


class TestIntegration:
    """Integration tests combining report path, hook, and dry-run."""
    
    @patch('crashlens.guard.subprocess.run')
    def test_full_workflow(self, mock_run, tmp_path, sample_rules_yaml, sample_logs_jsonl):
        """Complete workflow: report + hook + violations."""
        mock_run.return_value = MagicMock(returncode=0, stdout='Hook success', stderr='')
        
        runner = CliRunner()
        report_path = tmp_path / 'final-report.json'
        
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(guard, [
                str(sample_logs_jsonl),
                '--rules', str(sample_rules_yaml),
                '--report-path', str(report_path),
                '--annotation-hook', 'python hook.py {report_path}',
                '--output', 'json'
            ])
            
            # Report created
            assert report_path.exists()
            
            # Hook called
            assert mock_run.call_count == 1
            
            # JSON output on stdout
            assert '"summary"' in result.output
